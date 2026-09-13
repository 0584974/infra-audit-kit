from __future__ import annotations
import argparse
import json
from pathlib import Path
import yaml
from .terraform import audit_plan
from .kubernetes import audit_documents
from .report import json_report, markdown_report


def main() -> int:
    parser = argparse.ArgumentParser(prog="infra-audit", description="Audit Terraform plan JSON and Kubernetes manifests.")
    sub = parser.add_subparsers(dest="command", required=True)

    tf = sub.add_parser("terraform", help="Audit Terraform plan JSON")
    tf.add_argument("input", type=Path)
    tf.add_argument("--format", choices=["markdown", "json"], default="markdown")
    tf.add_argument("--output", type=Path)

    k8s = sub.add_parser("kubernetes", help="Audit one or more Kubernetes YAML documents")
    k8s.add_argument("input", type=Path)
    k8s.add_argument("--format", choices=["markdown", "json"], default="markdown")
    k8s.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "terraform":
        findings = audit_plan(json.loads(args.input.read_text()))
    else:
        findings = audit_documents(list(yaml.safe_load_all(args.input.read_text())))

    report = markdown_report(findings) if args.format == "markdown" else json_report(findings)
    if args.output:
        args.output.write_text(report)
    else:
        print(report)
    return 2 if any(f.severity in {"critical", "high"} for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
