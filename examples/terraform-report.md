# Infrastructure Audit Report

## Summary

- **CRITICAL**: 2
- **HIGH**: 1

## Findings

### [CRITICAL] Database publicly accessible

- Rule: `TF-AWS-RDS-002`
- Source: `terraform`
- Resource: `aws_db_instance.app`
- Finding: The database is configured as publicly accessible.
- Remediation: Place the database in private subnets and access it through controlled application or administrative paths.

### [CRITICAL] Public ingress detected

- Rule: `TF-AWS-SG-001`
- Source: `terraform`
- Resource: `aws_security_group.public_admin`
- Finding: Ingress rule 0 allows traffic from the public Internet (0.0.0.0/0).
- Remediation: Restrict source CIDRs to approved networks, VPN ranges, or load balancers.

### [HIGH] Database storage encryption disabled

- Rule: `TF-AWS-RDS-001`
- Source: `terraform`
- Resource: `aws_db_instance.app`
- Finding: Database storage is planned without encryption at rest.
- Remediation: Enable storage encryption and use a managed KMS key where governance requires it.
