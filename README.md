# infra-audit-kit

A small, auditable Python CLI that checks Terraform plan JSON and Kubernetes manifests before handover or CI promotion.

It is designed for the awkward gap between “the configuration parsed successfully” and “this change is safe enough to promote.” The tool turns a focused set of high-risk infrastructure conditions into a repeatable pre-deployment gate and produces output suitable for review or CI artifacts.

## Why use it?

Infrastructure reviews often fail in predictable ways:

- a public security-group rule is hidden inside a large Terraform plan;
- an RDS instance is made public or left unencrypted;
- a Kubernetes workload gains privileged execution or host networking;
- resource requests and limits are omitted;
- a reviewer sees the change only after deployment.

`infra-audit-kit` is intentionally narrow and read-only. It does not modify infrastructure, contact cloud APIs, or attempt to replace policy engines. Its job is to give engineers a fast, explainable signal before promotion.

## Checks in v0.1

### Terraform plan JSON

- AWS security groups with public ingress
- severity escalation for public SSH and RDP
- publicly accessible AWS RDS instances
- unencrypted AWS RDS storage
- S3 buckets configured with `force_destroy`
- broad Azure NSG inbound rules

### Kubernetes manifests

- privileged containers
- missing or disabled `runAsNonRoot`
- privilege escalation
- missing resource requests or limits
- host networking

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

Audit a Terraform plan:

```bash
terraform show -json tfplan > terraform-plan.json
infra-audit terraform terraform-plan.json --format markdown --output report.md
```

Audit Kubernetes manifests:

```bash
infra-audit kubernetes deployment.yaml --format json
```

The process exits with code `2` when a high- or critical-severity finding exists, so a CI job can block promotion.

## CI gate example

```bash
set -euo pipefail
terraform show -json tfplan > terraform-plan.json
infra-audit terraform terraform-plan.json \
  --format markdown \
  --output infra-audit-report.md
```

Store `infra-audit-report.md` as a pipeline artifact so the result remains available for review even when the gate fails.

## Operating model

A practical promotion flow is:

1. Generate the Terraform plan or render the Kubernetes manifest.
2. Run `infra-audit-kit` without cloud credentials.
3. Publish the report as a CI artifact.
4. Stop the pipeline on high or critical findings.
5. Require a human to review the finding and the proposed remediation.

Because the tool reads local plan JSON and manifests, it can be placed before any production credential or deployment step.

## Scope and limitations

This project performs static checks on the supplied files. It does not prove that an infrastructure change is safe, evaluate the full effective cloud configuration, or replace tools such as OPA, cloud-native policy services, or a professional security review.

The deliberately small rule set makes every current check easy to understand and audit. Extend it only with rules whose failure condition, severity, and remediation can be explained clearly.

## Technical articles and implementation notes

- [A practical pre-deployment gate for Terraform plans and Kubernetes manifests](docs/pre-deployment-infrastructure-audit-ci.md)
- [Migrating Azure Landing Zones from CAF Enterprise Scale to AVM without losing control](docs/azure-caf-enterprise-scale-to-avm-migration.md)

## Development

```bash
pip install -e . pytest
pytest -q
```

Contributions should include a representative input fixture, the expected finding, severity, and tests for both positive and negative cases.

---

Built by Andre Jõgi — infrastructure, cloud, data-platform, and automation engineer.
