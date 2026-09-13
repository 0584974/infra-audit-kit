from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class Finding:
    source: str
    rule_id: str
    severity: str
    title: str
    resource: str
    message: str
    remediation: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
