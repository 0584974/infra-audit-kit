from __future__ import annotations
from typing import Any
from .models import Finding

WORKLOAD_KINDS = {"Pod", "Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"}


def _pod_spec(doc: dict[str, Any]) -> dict[str, Any] | None:
    kind = doc.get("kind")
    spec = doc.get("spec") or {}
    if kind == "Pod":
        return spec
    if kind in {"Deployment", "StatefulSet", "DaemonSet", "Job"}:
        return (spec.get("template") or {}).get("spec") or {}
    if kind == "CronJob":
        return (((spec.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec") or {}
    return None


def audit_documents(documents: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for doc in documents:
        if not isinstance(doc, dict) or doc.get("kind") not in WORKLOAD_KINDS:
            continue
        kind = doc.get("kind", "Unknown")
        meta = doc.get("metadata") or {}
        resource = f"{kind}/{meta.get('name', 'unnamed')}"
        spec = _pod_spec(doc) or {}

        if spec.get("hostNetwork") is True:
            findings.append(Finding(
                "kubernetes", "K8S-POD-001", "high",
                "hostNetwork enabled", resource,
                "Workload shares the node network namespace.",
                "Disable hostNetwork unless the workload explicitly requires node networking.",
                {"hostNetwork": True},
            ))

        containers = list(spec.get("containers") or []) + list(spec.get("initContainers") or [])
        for c in containers:
            cname = c.get("name", "unnamed")
            sc = c.get("securityContext") or {}
            if sc.get("privileged") is True:
                findings.append(Finding(
                    "kubernetes", "K8S-CTR-001", "critical",
                    "Privileged container", f"{resource}:{cname}",
                    "Container runs in privileged mode.",
                    "Remove privileged mode and grant only narrowly scoped Linux capabilities if required.",
                    {"privileged": True},
                ))
            if sc.get("runAsNonRoot") is not True:
                findings.append(Finding(
                    "kubernetes", "K8S-CTR-002", "medium",
                    "runAsNonRoot not enforced", f"{resource}:{cname}",
                    "The container does not explicitly enforce a non-root runtime user.",
                    "Set securityContext.runAsNonRoot=true and use an image with a non-root user.",
                    {"runAsNonRoot": sc.get("runAsNonRoot")},
                ))
            if sc.get("allowPrivilegeEscalation") is not False:
                findings.append(Finding(
                    "kubernetes", "K8S-CTR-003", "medium",
                    "Privilege escalation not disabled", f"{resource}:{cname}",
                    "allowPrivilegeEscalation is not explicitly false.",
                    "Set securityContext.allowPrivilegeEscalation=false unless a documented exception exists.",
                    {"allowPrivilegeEscalation": sc.get("allowPrivilegeEscalation")},
                ))
            resources = c.get("resources") or {}
            if not resources.get("requests") or not resources.get("limits"):
                findings.append(Finding(
                    "kubernetes", "K8S-CTR-004", "low",
                    "Resource requests/limits incomplete", f"{resource}:{cname}",
                    "Container does not define both resource requests and limits.",
                    "Set CPU and memory requests/limits based on measured workload behavior.",
                    {"resources": resources},
                ))
    return findings
