# Migrating Azure Landing Zones from CAF Enterprise Scale to AVM Without Losing Control

The move from the Terraform module commonly known as **CAF Enterprise Scale** to the Azure Verified Modules (AVM) ecosystem is not a routine dependency upgrade. It is a platform migration: module boundaries change, inputs and outputs change, and the relationship between Terraform configuration and existing Azure resources may change with them.

That distinction matters. A team can produce a clean Terraform plan and still create operational damage if it accidentally changes management-group placement, policy assignments, role assignments, hub networking, or resource addresses in state. The safe objective is therefore not “make the new module apply.” It is:

> Reproduce the intended landing-zone behavior under the new implementation, with controlled state transition, explicit validation, and a tested rollback path.

This article presents a practical way to do that.

## Why migrate now?

Microsoft’s Azure Landing Zones guidance continues to evolve, while Azure Verified Modules provide Microsoft-aligned, reusable Terraform building blocks with published specifications and contribution standards. The relevant starting points are:

- [Azure Landing Zones documentation](https://learn.microsoft.com/azure/cloud-adoption-framework/ready/landing-zone/)
- [Azure Landing Zones Accelerator](https://azure.github.io/Azure-Landing-Zones/accelerator/)
- [Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/)
- [AVM pattern module for Azure Landing Zones](https://github.com/Azure/terraform-azurerm-avm-ptn-alz)
- [CAF Enterprise Scale Terraform module](https://github.com/Azure/terraform-azurerm-caf-enterprise-scale)

The business case is maintainability, not novelty. A platform module sits underneath governance, connectivity, identity, and workload subscriptions. Staying aligned with the supported landing-zone ecosystem reduces the long-term cost of absorbing Azure platform changes. But the migration must be treated like a production change to a control plane.

## Start with a behavioral inventory

Do not begin by translating variables. Begin by documenting what the current platform actually does.

For each deployed environment, record:

1. Management-group hierarchy and subscription placement.
2. Policy definitions, initiatives, assignments, exemptions, parameters, and managed identities.
3. Role assignments, including principal IDs and scopes.
4. Connectivity topology: hub resources, peering, DNS, routing, firewalls, gateways, and private DNS.
5. Diagnostic settings, log destinations, Defender settings, and monitoring integrations.
6. Terraform workspaces, state backends, provider versions, module versions, and resource addresses.
7. Resources intentionally managed outside the landing-zone code.
8. Known exceptions that are business requirements rather than technical debt.

This inventory becomes the acceptance baseline. Without it, “no errors during apply” can be mistaken for success.

A useful output is a matrix with four columns: current resource or behavior, intended owner after migration, migration action, and validation method. That forces ambiguous ownership into the open before Terraform makes the decision for you.

## Separate three kinds of change

The safest migration separates changes that are often bundled together:

- **Implementation change:** replacing the old module with AVM-based configuration.
- **Platform redesign:** changing hierarchy, policies, networking, or operating model.
- **Remediation:** fixing drift and historical inconsistencies.

Only the first belongs in the initial migration. Combining all three makes the plan difficult to review and rollback nearly impossible to reason about.

Freeze unrelated platform changes during the migration window. If the target design must change, first reproduce the present intended behavior under the new implementation, then perform the redesign as a separate, reviewable change.

## Build the target beside production

Create the AVM-based target configuration in an isolated branch and state environment. Pin Terraform, provider, and module versions. Do not point the new configuration at production state on day one.

Use representative non-production subscriptions to prove:

- hierarchy construction;
- policy assignment and parameter behavior;
- role assignment ownership;
- connectivity integration;
- diagnostics and monitoring;
- naming and tagging;
- module outputs consumed by downstream automation.

This is also where teams discover hidden contracts. A pipeline may depend on an output name. A subscription vending process may assume a management-group ID. A policy remediation job may expect a specific managed identity. Those contracts are part of the platform even if they never appeared in an architecture diagram.

## Treat Terraform state as production data

Most migration risk is concentrated in state.

Before any state operation:

- back up the remote state and record its version or object identifier;
- capture the exact source commit, lock file, provider versions, and module version;
- run a refresh-only plan and resolve unexplained drift;
- export a list of resource addresses and Azure resource IDs;
- verify backend locking and access;
- rehearse every state command against a copied state in a disposable environment.

Prefer declarative Terraform mechanisms such as `moved` blocks where they are supported and unambiguous. Use imports when the new configuration must adopt an existing Azure resource. Use direct state commands only when the mapping is understood, peer-reviewed, rehearsed, and logged.

The rule is simple: a state move changes Terraform’s ownership record; it does not change Azure. An incorrect move can cause the next plan to propose destructive Azure changes. Therefore every group of moves must be followed by a plan whose result is explained resource by resource.

## Migrate in bounded waves

A landing zone is easier to control when migrated by concern rather than in one large apply. A typical order is:

1. Management-group hierarchy.
2. Custom policy definitions and initiatives.
3. Policy assignments, exemptions, and remediations.
4. Role assignments.
5. Logging, diagnostics, and security configuration.
6. Connectivity resources and integrations.
7. Subscription placement or vending integrations.
8. Downstream outputs and automation consumers.

The exact order depends on the estate. Connectivity may remain in a separate state and module, which is often a good design. The important point is that each wave has its own entry criteria, expected plan, validation, and rollback decision.

Limit the blast radius further by piloting one non-production branch of the management-group tree before shared production scopes.

## Define hard validation gates

A migration needs machine-checkable gates, not “looks reasonable.”

Before apply:

- `terraform fmt -check`, validation, linting, and security scanning pass;
- providers and modules are pinned;
- the plan contains no unexplained deletes or replacements;
- policy and role changes match the approved inventory;
- state backup and rollback steps are verified;
- a second reviewer approves the plan.

After each wave:

- management-group and subscription placement match the baseline;
- policy assignment counts, scopes, parameters, and identities match expectations;
- exemptions remain present and valid;
- role assignments have the correct principals and scopes;
- connectivity tests confirm DNS, routes, peering, and required endpoints;
- diagnostic settings deliver data to the intended destinations;
- a second Terraform plan is empty or contains only explicitly accepted differences;
- representative workload deployment and subscription-vending tests pass.

A zero-change second plan is one of the strongest signals that the new implementation has converged. It is not sufficient by itself, but a non-empty unexplained plan is a clear stop condition.

## Design rollback before the first apply

Rollback is not “put the old code back.” If state addresses or ownership changed, old code plus new state may be unsafe.

A credible rollback package contains:

- the source state snapshot;
- exact source commit and dependency lock file;
- target state snapshots after each successful wave;
- a reversible mapping of old and new resource addresses;
- the commands and permissions required to restore state;
- criteria for rolling forward versus restoring;
- a communications and decision owner.

Some changes are easier to correct forward than to reverse, especially policy assignments that have already triggered remediation. Decide this in advance. The rollback decision should consider Azure-side effects, not only Terraform state.

## Common failure modes

### “The plan is mostly renames”

Resource address changes are not harmless unless Terraform is explicitly told that the old and new addresses represent the same Azure objects. Review every create/delete pair as a potential missing move or import.

### Policy equality is checked by display name

Policy behavior depends on definition IDs, versions, parameters, scope, enforcement mode, identity, exemptions, and remediation. Compare those properties, not just names.

### Existing drift is absorbed into the migration

If a refresh-only plan already shows changes, migration results become ambiguous. Reconcile or formally accept drift before changing the implementation.

### Connectivity is included because it is convenient

Hub networks and routing often have a larger blast radius and different maintenance requirements than hierarchy and policy. Keep connectivity separate unless the dependency is understood and the rollback is proven.

### State commands are written directly against production

Rehearse against a state copy and non-production resources. Record before-and-after address-to-resource-ID mappings.

### The migration becomes a redesign

A new management-group hierarchy or policy model may be valuable, but coupling it to the module transition multiplies risk. Stabilize first; redesign second.

## A practical cutover checklist

A production cutover is ready when all of the following are true:

- the behavioral inventory is approved;
- target configuration has passed non-production tests;
- drift is understood;
- state mapping has been rehearsed;
- the production plan has no unexplained destructive action;
- policy, RBAC, logging, and connectivity checks are automated where possible;
- rollback artifacts have been tested;
- downstream consumers have been identified;
- change ownership and go/no-go authority are explicit;
- the next plan after each wave is reviewed before continuing.

The cutover should stop immediately if Azure resource IDs unexpectedly change, subscription placement differs from the approved target, policy assignments disappear, privileged role assignments change unexpectedly, or shared networking shows unexplained replacement.

## The architectural outcome

The best result is not a one-for-one rewrite that preserves every historical coupling. It is a controlled transition to a platform structure in which responsibilities are visible:

- landing-zone hierarchy and governance are versioned;
- connectivity can evolve with an appropriate blast radius;
- subscription vending consumes stable contracts;
- policy and RBAC changes are testable;
- Terraform state ownership is deliberate;
- module upgrades are routine rather than existential.

AVM gives teams a stronger standardized foundation, but it does not remove the need for platform engineering discipline. The migration succeeds when the organization can prove that governance and operations remain correct—not merely when Terraform returns exit code zero.

---

*Author: Andre Jõgi — infrastructure, cloud, data-platform, and automation engineer.*
