from __future__ import annotations
import json
from collections import Counter
from .models import Finding

ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def json_report(findings: list[Finding]) -> str:
    return json.dumps({"summary": dict(Counter(f.severity for f in findings)), "findings": [f.to_dict() for f in findings]}, indent=2)


def markdown_report(findings: list[Finding]) -> str:
    ordered = sorted(findings, key=lambda f: (ORDER.get(f.severity, 99), f.rule_id, f.resource))
    counts = Counter(f.severity for f in ordered)
    lines = ["# Infrastructure Audit Report", "", "## Summary", ""]
    if not ordered:
        lines += ["No findings.", ""]
    else:
        for severity in ("critical", "high", "medium", "low", "info"):
            if counts.get(severity):
                lines.append(f"- **{severity.upper()}**: {counts[severity]}")
        lines += ["", "## Findings", ""]
        for f in ordered:
            lines += [
                f"### [{f.severity.upper()}] {f.title}",
                "",
                f"- Rule: `{f.rule_id}`",
                f"- Source: `{f.source}`",
                f"- Resource: `{f.resource}`",
                f"- Finding: {f.message}",
                f"- Remediation: {f.remediation}",
                "",
            ]
    return "\n".join(lines)
