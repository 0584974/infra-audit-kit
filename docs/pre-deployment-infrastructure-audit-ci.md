# A Practical Pre-Deployment Gate for Terraform Plans and Kubernetes Manifests

Infrastructure review often happens at the least useful moment: after a deployment has failed, after a security scanner has produced hundreds of context-free alerts, or during a handover when the original author is no longer available. A smaller and earlier control is usually more effective. Before promotion, turn the exact deployment input into a machine-readable artifact, run a bounded set of high-signal checks, and fail only on findings that the team has explicitly decided must block delivery.

This guide uses the small, read-only `infra-audit-kit` CLI in this repository. The point is not to replace a full policy engine. It is to show how to build an understandable gate whose inputs, rules, output, and failure behavior can all be inspected.

## 1. Define the contract before adding a scanner

A useful gate needs a narrow contract:

- It examines generated Terraform plan JSON or rendered Kubernetes YAML.
- It never changes infrastructure.
- Every finding identifies a rule, severity, resource, evidence, and remediation.
- High or critical findings return exit code `2`.
- No finding, or only lower-severity findings, returns `0`.
- Parsing or execution failures are different from policy findings and must remain visible as job failures.

That distinction matters. A policy rejection says, “the input was understood and violates a declared rule.” A parser crash says, “the input was not evaluated.” Treating both as the same generic red job makes troubleshooting and audit evidence weaker.

The current rule set intentionally concentrates on common, consequential mistakes: public administrative ingress, public or unencrypted RDS instances, destructive S3 settings, broad Azure NSG ingress, privileged Kubernetes containers, host networking, privilege escalation, missing non-root execution, and missing resource requests or limits.

## 2. Generate the artifact that will actually be applied

For Terraform, do not scan only HCL source. Modules, expressions, variables, and provider behavior make the plan a better representation of intended change.

```bash
terraform init
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
```

HashiCorp documents `terraform show -json` as the machine-readable representation of a plan or state file. The JSON can contain sensitive values in plain text, so it should be handled like a deployment secret: do not upload it to public artifacts or retain it longer than necessary. See the official [Terraform show documentation](https://developer.hashicorp.com/terraform/cli/commands/show).

For Kubernetes, scan the manifest that will be submitted, not merely a Helm template before values and overlays are resolved. Depending on the delivery tool, that may mean:

```bash
helm template my-app ./chart -f values-prod.yaml > rendered.yaml
# or
kubectl kustomize overlays/prod > rendered.yaml
```

This keeps the gate aligned with the object shape the API server is expected to receive.

## 3. Install and run the audit locally

The project requires Python 3.10 or later.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Audit Terraform and write a Markdown report:

```bash
infra-audit terraform tfplan.json \
  --format markdown \
  --output terraform-audit.md
```

Audit one or more YAML documents:

```bash
infra-audit kubernetes rendered.yaml \
  --format json \
  --output kubernetes-audit.json
```

The repository includes deliberately unsafe examples for a smoke test:

```bash
infra-audit terraform examples/terraform-plan.json
echo "$?"  # expected: 2

infra-audit kubernetes examples/kubernetes.yaml
echo "$?"  # expected: 2
```

The Terraform example contains public SSH ingress and a public, unencrypted database. The Kubernetes example runs a privileged container. Those are intentional fixtures, not deployable reference configurations.

## 4. Make the CI step preserve evidence

A gate is much more useful when it both blocks and leaves a readable report. A shell step can capture the policy exit code without losing the generated output:

```bash
set +e
infra-audit terraform tfplan.json \
  --format markdown \
  --output terraform-audit.md
audit_rc=$?
set -e

if [ "$audit_rc" -eq 2 ]; then
  echo "Infrastructure policy gate rejected the plan."
  sed -n '1,200p' terraform-audit.md
  exit 2
fi

if [ "$audit_rc" -ne 0 ]; then
  echo "Audit execution failed with exit code $audit_rc."
  exit "$audit_rc"
fi
```

A GitHub Actions job can then upload the report even when the gate fails:

```yaml
name: infrastructure-policy

on:
  pull_request:

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: python -m pip install -e .

      - name: Create Terraform plan JSON
        run: |
          terraform -chdir=infra init -input=false
          terraform -chdir=infra plan -input=false -out=tfplan
          terraform -chdir=infra show -json tfplan > tfplan.json

      - name: Audit plan
        id: audit
        continue-on-error: true
        run: |
          infra-audit terraform infra/tfplan.json \
            --format markdown \
            --output terraform-audit.md

      - name: Publish report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: terraform-audit
          path: terraform-audit.md

      - name: Enforce gate
        if: steps.audit.outcome == 'failure'
        run: exit 2
```

In a real repository, pin third-party actions to reviewed commit SHAs and make Terraform credentials available only to the plan step. GitHub's official guidance explains the security consequences of untrusted input and credential scope in [secure use of GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions).

## 5. Decide what blocks, what warns, and who owns exceptions

The CLI currently blocks on high and critical findings. That is a sensible default only if severity is stable and understood. Before making the check mandatory, run it against representative plans and manifests, then record:

1. which rules block all environments;
2. which rules may be warnings in development;
3. who can approve an exception;
4. where the exception rationale and expiry date live;
5. how a false positive becomes a test and a rule change.

Avoid permanent path-based exclusions such as “ignore the entire legacy folder.” A bounded exception should identify the rule and resource, state why the risk is temporarily accepted, name an owner, and expire. The scanner in this repository does not yet implement an exception format; until it does, exceptions should be handled outside the tool as an explicit, reviewed pipeline decision rather than hidden in source code.

## 6. Test both detection and absence

A security check is not complete when the unsafe fixture fails. It also needs a safe fixture that passes, and nested or multi-document inputs that prove traversal works as expected.

For each rule, maintain at least:

- one positive fixture that must generate the finding;
- one negative fixture that must not generate it;
- one boundary case, such as IPv6 public ingress, an empty list, a missing optional field, or a nested child module;
- an assertion over rule ID, resource identity, severity, and critical evidence.

Also test CLI behavior:

- Markdown and JSON output are valid.
- `--output` writes a file and stdout mode remains readable.
- a high finding returns `2`;
- no blocking finding returns `0`;
- malformed JSON or YAML fails visibly rather than silently passing.

## 7. Know the limits of a plan-time gate

A pre-deployment check can catch declared configuration risk. It cannot prove the running system is secure. It does not see every provider default, organization policy, admission-controller mutation, manual change, runtime identity path, or network control outside the artifact.

Use it as one layer:

```text
source review
  -> rendered plan/manifest audit
  -> protected approval
  -> deployment
  -> cloud/Kubernetes policy enforcement
  -> runtime configuration and drift monitoring
```

Terraform also warns that its JSON output format has compatibility considerations; consumers should be tested against supported Terraform versions. Kubernetes security should additionally be enforced with admission controls such as the built-in [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/) or an organization-approved policy engine.

## 8. A practical adoption sequence

A low-friction rollout is:

1. Run the tool in report-only mode for one or two delivery cycles.
2. Review every finding with platform and application owners.
3. Fix clear defects and add regression fixtures.
4. Turn on blocking only for high-confidence rules.
5. Track false positives, exceptions, and mean time to remediation.
6. Expand the rule set only when each new rule has an owner and a testable remediation path.

The goal is not the largest rule catalogue. The goal is a small control that developers understand, operators trust, and auditors can reconstruct from the exact input and report.