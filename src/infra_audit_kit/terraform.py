from __future__ import annotations
from typing import Any
from .models import Finding

PUBLIC_CIDRS = {"0.0.0.0/0", "::/0"}


def _walk_resources(module: dict[str, Any]):
    for resource in module.get("resources", []):
        yield resource
    for child in module.get("child_modules", []):
        yield from _walk_resources(child)


def audit_plan(plan: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    root = plan.get("planned_values", {}).get("root_module", {})
    for r in _walk_resources(root):
        rtype = r.get("type", "unknown")
        name = r.get("address", r.get("name", "unknown"))
        values = r.get("values") or {}

        if rtype == "aws_security_group":
            for direction in ("ingress", "egress"):
                for idx, rule in enumerate(values.get(direction) or []):
                    cidrs = set(rule.get("cidr_blocks") or []) | set(rule.get("ipv6_cidr_blocks") or [])
                    if cidrs & PUBLIC_CIDRS and direction == "ingress":
                        from_port = rule.get("from_port")
                        to_port = rule.get("to_port")
                        severity = "critical" if from_port in (22, 3389) or to_port in (22, 3389) else "high"
                        findings.append(Finding(
                            "terraform", "TF-AWS-SG-001", severity,
                            "Public ingress detected", name,
                            f"Ingress rule {idx} allows traffic from the public Internet ({', '.join(sorted(cidrs & PUBLIC_CIDRS))}).",
                            "Restrict source CIDRs to approved networks, VPN ranges, or load balancers.",
                            {"direction": direction, "from_port": from_port, "to_port": to_port, "cidrs": sorted(cidrs)},
                        ))

        if rtype == "aws_s3_bucket":
            if values.get("force_destroy") is True:
                findings.append(Finding(
                    "terraform", "TF-AWS-S3-001", "medium",
                    "S3 force_destroy enabled", name,
                    "The bucket can be destroyed together with all contained objects.",
                    "Disable force_destroy for production data or require an explicit break-glass workflow.",
                    {"force_destroy": True},
                ))

        if rtype in {"aws_db_instance", "aws_rds_cluster"}:
            if values.get("storage_encrypted") is False:
                findings.append(Finding(
                    "terraform", "TF-AWS-RDS-001", "high",
                    "Database storage encryption disabled", name,
                    "Database storage is planned without encryption at rest.",
                    "Enable storage encryption and use a managed KMS key where governance requires it.",
                    {"storage_encrypted": False},
                ))
            if values.get("publicly_accessible") is True:
                findings.append(Finding(
                    "terraform", "TF-AWS-RDS-002", "critical",
                    "Database publicly accessible", name,
                    "The database is configured as publicly accessible.",
                    "Place the database in private subnets and access it through controlled application or administrative paths.",
                    {"publicly_accessible": True},
                ))

        if rtype == "azurerm_network_security_rule":
            src = values.get("source_address_prefix")
            dest_port = str(values.get("destination_port_range", ""))
            access = str(values.get("access", "")).lower()
            direction = str(values.get("direction", "")).lower()
            if src in {"*", "Internet", "0.0.0.0/0"} and access == "allow" and direction == "inbound":
                severity = "critical" if dest_port in {"22", "3389", "*"} else "high"
                findings.append(Finding(
                    "terraform", "TF-AZ-NSG-001", severity,
                    "Broad Azure NSG inbound rule", name,
                    f"Inbound rule allows source {src} to destination port {dest_port}.",
                    "Restrict the source prefix and expose only explicitly required service ports.",
                    {"source": src, "destination_port": dest_port},
                ))

    return findings
