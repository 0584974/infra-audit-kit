from infra_audit_kit.terraform import audit_plan
from infra_audit_kit.kubernetes import audit_documents


def test_terraform_public_ssh_is_critical():
    plan = {"planned_values": {"root_module": {"resources": [{
        "type": "aws_security_group", "address": "aws_security_group.bad",
        "values": {"ingress": [{"from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"]}]}
    }]}}}
    findings = audit_plan(plan)
    assert any(f.rule_id == "TF-AWS-SG-001" and f.severity == "critical" for f in findings)


def test_k8s_privileged_is_critical():
    docs = [{"kind": "Deployment", "metadata": {"name": "bad"}, "spec": {"template": {"spec": {"containers": [{"name": "app", "securityContext": {"privileged": True}}]}}}}]
    findings = audit_documents(docs)
    assert any(f.rule_id == "K8S-CTR-001" and f.severity == "critical" for f in findings)
