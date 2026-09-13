# infra-audit-kit

Small, auditable Python CLI for checking Terraform plan JSON and Kubernetes manifests before handover or CI promotion.

## What it checks in v0.1

- AWS security groups with public ingress, including SSH/RDP severity escalation
- AWS RDS public accessibility and storage encryption
- S3 `force_destroy`
- Broad Azure NSG inbound rules
- Kubernetes privileged containers
- `runAsNonRoot`
- privilege escalation
- resource requests/limits
- host networking

The tool is read-only: it never changes infrastructure.

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Usage

```bash
infra-audit terraform examples/terraform-plan.json --format markdown --output report.md
infra-audit kubernetes examples/kubernetes.yaml --format json
```

Exit code is `2` when a high/critical finding exists, allowing CI to block promotion.

## Development

```bash
pip install -e . pytest
pytest -q
```
