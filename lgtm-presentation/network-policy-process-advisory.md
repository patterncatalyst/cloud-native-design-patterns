# Network Policy Process — Red Hat Advisory

A recommended approach for operationalizing in-cluster network segmentation
on OpenShift, from perimeter-only to developer-owned NetworkPolicies.

---

## What this document is

This is Red Hat's recommended approach to building a network policy process
for an organization that:

- Runs perimeter and east-west controls through a firewall team on a
  traditional appliance (Palo Alto, Fortinet, etc.) today.
- Wants to shift network segmentation left into the OpenShift cluster using
  Kubernetes NetworkPolicy, AdminNetworkPolicy, and EgressFirewall.
- Has developers who are not security specialists — most have never written
  a firewall rule and do not inherently know what traffic their applications
  require.

**What this document is not:** a tool selection exercise or an ownership
assignment. It describes a process and a maturity path. Organizations apply
it with the teams and tools they already have.

---

## 1. Where customers typically start

Most organizations move through a four-phase maturity path. Trying to skip
phases — jumping straight to developer-authored micro-segmentation — is the
most common cause of stalled adoption.

### Phase 1 — Observe (weeks 1-4)

Before writing any policy, understand what traffic actually flows today.

Red Hat Advanced Cluster Security (ACS) automatically discovers network
flows between deployments, namespaces, and external destinations. It builds
a **network baseline** — a map of every connection the cluster has seen — and
renders it in the **Network Graph**. This baseline becomes the source of truth
for what traffic is expected.

At this stage, nothing is denied. The goal is visibility. The firewall team
and platform team review the ACS network graph together and identify:

- Which services talk to each other (and which shouldn't).
- Which services make outbound calls to external endpoints.
- Which connections cross namespace boundaries.
- Which traffic patterns were previously invisible behind the perimeter.

**What Red Hat typically sees:** customers are surprised by the volume of
east-west traffic they did not know existed — service-to-service connections
that were never documented because the perimeter firewall was the only
control plane.

### Phase 2 — Baseline (weeks 4-8)

Apply **default-deny** NetworkPolicy in every namespace. This is the single
highest-impact security measure — without it, any pod can reach any other
pod in the cluster.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: <namespace>
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

Simultaneously, use ACS to **auto-generate NetworkPolicy YAML** from the
observed baseline. ACS generates a single policy per deployment (named
`stackrox-generated-<deployment>`), with ingress rules based on observed
source pods and namespace selectors. These generated policies are a starting
point — they capture what traffic *did* flow, not what traffic *should* flow.

The platform team reviews the generated policies, removes any connections
that should not have existed (the audit value of this step is significant),
and applies the cleaned-up policies alongside the default-deny.

**What Red Hat typically sees:** the first default-deny rollout in a non-prod
namespace immediately reveals undocumented dependencies — a monitoring agent
that scrapes every pod, a legacy batch job that connects to an external
database, a sidecar that phones home to a SaaS endpoint. Discovering these
in dev or test is the point.

### Phase 3 — Guardrails (weeks 8-16)

With baseline policies in place, the platform team introduces cluster-scoped
guardrails using OpenShift's **AdminNetworkPolicy (ANP)** and
**BaselineAdminNetworkPolicy (BANP)**.

These are the policies the platform team owns — they cannot be overridden by
developers, and they establish the security boundaries that all applications
inherit.

### Phase 4 — Developer ownership (ongoing)

App teams begin authoring and owning their own namespace-scoped
NetworkPolicies. They do this via pull request, with CI validation and
platform team review. The process section later in this document describes
this workflow in detail.

---

## 2. The three-tier policy model

OpenShift's OVN-Kubernetes network plugin evaluates traffic against three
tiers of policy, in order. Understanding this model is critical — it
determines who controls what and where overrides are possible.

### Tier 1 — AdminNetworkPolicy (ANP)

- **Scope:** cluster-wide (not namespace-scoped)
- **Controlled by:** platform / infrastructure team
- **Priority:** 0 (highest) to 99 (lowest)
- **Actions:** Allow, Deny, or **Pass** (hand evaluation to the next tier)
- **Override:** cannot be overridden by NetworkPolicy or BANP

ANP is where the platform team enforces non-negotiable rules: deny traffic
to the control plane from application namespaces, allow monitoring agents
to scrape all pods, deny cross-environment traffic (dev → prod). A **Pass**
rule explicitly delegates the decision to the next tier (NetworkPolicy),
which is how the platform team says "app teams, this one is yours to decide."

**Critical caution:** an ANP with an empty namespace selector (`{}`) matches
*all* namespaces, including `openshift-*` and `kube-system`. Use workload-
specific label selectors. An overly broad ANP can lock the cluster.

### Tier 2 — NetworkPolicy (NP)

- **Scope:** namespace-scoped
- **Controlled by:** app teams (developers)
- **Override:** can be overridden by ANP (which takes precedence)

This is the standard Kubernetes NetworkPolicy API. App teams use it to
define which pods in their namespace accept traffic from which sources, on
which ports. Traffic that matches an ANP Allow or Deny rule never reaches
this tier — it is only evaluated if the ANP passed the traffic through.

### Tier 3 — BaselineAdminNetworkPolicy (BANP)

- **Scope:** cluster-wide (singleton — only one BANP exists per cluster)
- **Controlled by:** platform / infrastructure team
- **Actions:** Allow or Deny (no Pass)
- **Override:** *can* be overridden by NetworkPolicy

BANP is the safety net. It catches traffic that was passed by the ANP and
not matched by any NetworkPolicy. The recommended use is **default-deny at
the BANP tier** — if no ANP rule and no NetworkPolicy allows it, BANP denies
it. This means that a namespace with no NetworkPolicies at all still has a
default-deny posture, without requiring the app team to create the
default-deny policy themselves.

### How the tiers compose

```
Traffic arrives
  ├── ANP evaluates (tier 1)
  │     ├── Allow → traffic flows (skip NP and BANP)
  │     ├── Deny  → traffic blocked (skip NP and BANP)
  │     └── Pass  → hand to tier 2
  ├── NetworkPolicy evaluates (tier 2)
  │     ├── Match → apply NP rules (allow/deny per NP semantics)
  │     └── No NP in namespace → hand to tier 3
  └── BANP evaluates (tier 3)
        ├── Allow → traffic flows
        └── Deny  → traffic blocked
```

**The value proposition for the customer:** the platform team controls tiers
1 and 3 (the guardrails). Developers control tier 2 (their application's
policies). Even if a developer writes no NetworkPolicies at all, the BANP
default-deny ensures the namespace is not wide open. This directly addresses
the developer skill gap — the platform provides safety by default.

---

## 3. Handling the developer skill gap

Developers are not firewall engineers. Expecting them to author network
policies from scratch — knowing which ports their services listen on, which
upstream services call them, and which external endpoints they need — is
unrealistic at the start. Red Hat recommends four complementary approaches:

### a) ACS-generated baselines — developers review, not author

ACS observes actual traffic for a configurable window, then generates
NetworkPolicy YAML that matches the observed flows. The developer's job is
to *review* the generated policy — "does this look right? should this
connection exist?" — not to author it from scratch. This inverts the skill
requirement: reviewing a concrete policy is dramatically easier than writing
one from zero.

Over time, as developers become familiar with the policy format, they begin
modifying and authoring policies directly. But the starting point is always
a generated baseline, not a blank file.

### b) Platform-authored starter templates

The platform team maintains a library of NetworkPolicy templates for common
workload archetypes:

- **Web-facing service** — accepts ingress from the ingress controller on
  port 8080/8443, allows egress to backend services and the database.
- **Internal API** — accepts ingress from specific consumer services, allows
  egress to the database and Kafka.
- **Batch job** — no ingress, allows egress to the database and specific
  external endpoints.
- **Database** — accepts ingress from application services on port 5432,
  no egress.

Developers pick the template that matches their workload, customize the
namespace and label selectors, and submit a PR. The template handles the
hard parts (deny-all baseline, correct policyTypes, CIDR ranges for external
services).

### c) BANP as a safety net

With a BANP configured to deny traffic that no other policy allows, a
developer who deploys a new service without any NetworkPolicy gets
default-deny behavior automatically. Their service cannot send or receive
traffic until they (or the platform) create a policy. This is strict but
safe — it converts "I forgot to write a policy" from a security gap into a
connectivity issue that surfaces immediately in testing.

### d) Golden-path namespace provisioning

When a new namespace is provisioned (via GitOps, a self-service portal, or
an operator), the provisioning process automatically includes:

- A default-deny NetworkPolicy
- An EgressFirewall allowing only approved external destinations
- Starter NetworkPolicy templates in a `policies/` directory
- RBAC bindings giving the app team edit access to NetworkPolicy resources

The developer starts with a working, secured namespace. They never see the
"everything is open, now lock it down" starting point that leads to
procrastination.

---

## 4. CI/CD flow end-to-end

Network policy changes follow the same CI/CD pipeline as application code.
The principle is the same: **the CI pipeline is the only path to production.**

### The flow

```
Developer authors/modifies NetworkPolicy YAML
  │
  ├── Opens PR against the policy repo
  │
  ├── CI validates automatically:
  │     ├── Schema check    — oc apply --dry-run=client (valid YAML, correct API version)
  │     ├── Policy lint     — conftest / kyverno CLI (organizational rules: no allow-all,
  │     │                     required labels, port range limits)
  │     ├── ACS build-time  — ACS build-time policy tools validate against known baselines
  │     │                     and flag policies that would allow traffic outside the baseline
  │     └── Dry-run apply   — oc apply --dry-run=server against a staging cluster
  │                           (catches admission denials, quota issues)
  │
  ├── Platform / security team reviews the PR
  │     ├── For NetworkPolicies: app team authors, platform reviews
  │     ├── For ANP/BANP/EgressFirewall: platform authors, security/firewall reviews
  │     └── CODEOWNERS enforces review requirements by path
  │
  ├── Merge triggers GitOps sync
  │     ├── OpenShift GitOps (ArgoCD) syncs to staging cluster
  │     ├── Smoke tests validate connectivity (expected paths open, expected paths denied)
  │     └── If staging passes → sync to production
  │
  └── Post-deploy validation
        ├── ACS network graph confirms no anomalous flows
        └── OVN-Kubernetes flow logs confirm deny counts are expected
```

### What ACS build-time tools add

Starting with ACS 4.4, build-time network policy tools can generate and
validate policies locally or in a CI pipeline. This closes the loop between
"what traffic does my app need" (observed in ACS) and "what policy should I
write" (generated and validated in CI). The developer never needs to author
a policy from scratch — they generate one from the baseline, review it, and
submit the PR.

---

## 5. Repo structure

Red Hat recommends a three-layer repository model that separates platform-
owned policies from application-owned policies, with clear ownership and
review boundaries.

```
cluster-policies/
│
├── platform-baselines/                    # Platform team owns
│   ├── anp/
│   │   ├── deny-cross-env.yaml           # Block dev ↔ prod traffic
│   │   ├── allow-monitoring.yaml         # Prometheus/OTel can scrape all pods
│   │   ├── deny-control-plane.yaml       # Apps cannot reach API server directly
│   │   └── pass-app-traffic.yaml         # Delegate app-to-app decisions to NP tier
│   ├── banp/
│   │   └── default-deny-baseline.yaml    # Safety net: deny anything not explicitly allowed
│   ├── egressfirewall/
│   │   ├── prod-egress.yaml              # Production: allow only approved external CIDRs/DNS
│   │   ├── test-egress.yaml              # Test: same as prod (mirrors topology)
│   │   └── dev-egress.yaml               # Dev: broader access, still no direct internet
│   └── kustomization.yaml
│
├── onboarding/                            # Platform team maintains, app teams consume
│   ├── web-service/
│   │   ├── default-deny.yaml
│   │   ├── allow-ingress-controller.yaml
│   │   ├── allow-egress-db.yaml
│   │   └── kustomization.yaml
│   ├── internal-api/
│   │   ├── default-deny.yaml
│   │   ├── allow-from-consumers.yaml
│   │   ├── allow-egress-kafka.yaml
│   │   └── kustomization.yaml
│   └── batch-job/
│       ├── default-deny.yaml
│       ├── allow-egress-db.yaml
│       └── kustomization.yaml
│
├── app-policies/                          # App teams own, platform reviews
│   ├── orders/
│   │   ├── base/
│   │   │   ├── order-service-np.yaml
│   │   │   ├── inventory-service-np.yaml
│   │   │   └── kustomization.yaml
│   │   └── overlays/
│   │       ├── dev/
│   │       ├── test/
│   │       └── prod/
│   ├── payments/
│   │   └── ...
│   └── notifications/
│       └── ...
│
├── CODEOWNERS                             # Enforces review rules
│   # /platform-baselines/  @platform-team @firewall-team
│   # /onboarding/          @platform-team
│   # /app-policies/orders/ @orders-team   @platform-team
│
└── .tekton/ or .github/                   # CI pipeline definitions
    └── policy-validation.yaml
```

### Ownership model

| Layer | Authors | Reviewers | Scope |
|-------|---------|-----------|-------|
| `platform-baselines/` (ANP, BANP, EgressFirewall) | Platform team | Firewall / security team | Cluster-wide |
| `onboarding/` (templates) | Platform team | Platform team | Reusable templates |
| `app-policies/` (NetworkPolicy) | App teams | Platform team | Per-namespace |

### Environment promotion

Kustomize overlays handle environment differences. The `base/` directory
contains the policy shape; overlays adjust namespace names, label selectors,
and external CIDR ranges per environment. The same PR that modifies a
policy flows through the same CI pipeline regardless of target environment.

---

## 6. Day-2 operations

### Denied-flow triage

When a developer reports "my service can't reach X," the triage path is:

1. **ACS anomalous flow alerts** — check the ACS network graph for the
   deployment. If the connection appears as an anomalous flow (outside the
   baseline), it was likely never policy-allowed. Decide whether to add
   a policy or investigate why the new connection exists.

2. **OVN-Kubernetes flow logs** — OVN-K logs denied packets with source pod,
   destination, port, and the ACL rule that denied them. These logs
   identify *which tier* denied the traffic (ANP, NP, or BANP), which
   tells you who needs to update the policy.

3. **`oc adm must-gather`** — collects network policy state, OVN-K
   configuration, and flow logs for offline analysis. Use this for
   escalation to Red Hat support.

**Target:** denied-flow triage should take under 30 minutes. If it
regularly takes longer, the observability tooling (ACS, flow logs) is not
configured correctly.

### Break-glass process

When a denied flow is blocking a production incident and the normal PR
process is too slow:

1. A platform team member creates a **temporary ANP with a Pass rule** at a
   high priority (low number), handing the traffic decision to the
   NetworkPolicy tier. If no NetworkPolicy exists for the target, the BANP
   (if configured as default-deny) will still deny — so the break-glass
   may need a temporary NetworkPolicy as well.

2. The temporary rule is **time-boxed** (label it with an expiration date
   annotation) and **logged** (create an incident ticket referencing the
   change).

3. Within 24 hours, the proper policy change goes through the normal PR
   and CI pipeline. The temporary rule is removed.

4. All break-glass events are reviewed in the quarterly policy review.

### Drift detection

- **OpenShift GitOps (ArgoCD)** reports sync status for every policy
  manifest. If someone manually applies a policy via `oc apply` instead
  of the PR pipeline, ArgoCD detects the drift and either alerts or
  auto-reverts (depending on configuration).

- **ACS baseline drift** — if new traffic flows appear that are not in
  the ACS network baseline, ACS flags them as anomalous. This catches
  both policy drift (someone added a rule manually) and application
  drift (a new service started making unexpected connections).

### Policy coverage reporting

Maintain a dashboard or periodic report showing:

- Namespaces with default-deny in place vs. those without.
- Namespaces with ACS baselines active vs. those still in observation.
- ANP/BANP rules in effect and their last-modified dates.
- Break-glass events in the current quarter.
- Denied-flow triage times (mean, p95).

---

## 7. The firewall team's evolving role

The shift to in-cluster network policy does not eliminate the firewall team.
It changes their scope and elevates their role from gatekeeper to architect.

### What stays with the firewall team

- **North-south edge controls** — the perimeter firewall (Palo Alto)
  continues to manage traffic entering and leaving the data center or
  cloud VPC. This is where TLS inspection, DDoS mitigation, and
  compliance logging (PCI, HIPAA) remain.

- **EgressFirewall authorship** — the firewall team authors and reviews
  EgressFirewall CRDs that control which external destinations cluster
  workloads can reach. This is their domain expertise (approved CIDRs,
  DNS-based rules, compliance-required blocks).

- **ANP / BANP review** — the firewall team reviews all cluster-scoped
  network policies (ANP, BANP) because these have cluster-wide blast
  radius. The platform team authors them; the firewall team approves.

### What shifts to the platform and app teams

- **East-west traffic segmentation** — service-to-service traffic within
  the cluster is segmented by NetworkPolicy, authored by app teams and
  reviewed by the platform team. The firewall team does not need to
  approve every pod-to-pod rule — that does not scale.

- **NetworkPolicy authorship** — app teams own their namespace-scoped
  policies. They know which services call which endpoints. The platform
  team reviews for correctness and compliance; the firewall team is
  consulted for cross-namespace or unusual egress patterns.

### The new relationship

```
                  ┌─────────────┐
                  │ Firewall    │  Authors: EgressFirewall
                  │ Team        │  Reviews: ANP, BANP
                  │             │  Owns: perimeter (Palo Alto)
                  └──────┬──────┘
                         │ reviews cluster-scoped policies
                  ┌──────▼──────┐
                  │ Platform    │  Authors: ANP, BANP, templates
                  │ Team        │  Reviews: app NetworkPolicies
                  │             │  Owns: cluster security posture
                  └──────┬──────┘
                         │ reviews namespace-scoped policies
                  ┌──────▼──────┐
                  │ App Teams   │  Authors: NetworkPolicy (per-namespace)
                  │             │  Consumes: templates, ACS baselines
                  │             │  Owns: application connectivity
                  └─────────────┘
```

The firewall team moves from "approve every rule" to "set the boundaries
and review the exceptions." This is faster for developers, safer for the
organization, and a better use of the firewall team's expertise.

---

## 8. What "good" looks like at 12 months

### Maturity checklist

After 12 months of sustained effort, a mature network policy practice looks
like this:

- [ ] **Default-deny in every namespace** — no namespace exists without a
      default-deny NetworkPolicy or BANP coverage.
- [ ] **ACS baselines active** — every production namespace has a locked
      baseline. New flows trigger anomalous-flow alerts.
- [ ] **ANP guardrails enforced** — cross-environment traffic blocked,
      monitoring access allowed, control-plane access restricted.
- [ ] **BANP default-deny** — the cluster-wide safety net catches any
      traffic not explicitly allowed by ANP or NetworkPolicy.
- [ ] **App teams authoring policies via PR** — developers submit
      NetworkPolicy changes through the CI/CD pipeline, not `oc apply`.
- [ ] **CI validates before merge** — schema checks, policy linting, ACS
      build-time validation, and dry-run apply run on every PR.
- [ ] **EgressFirewall per project** — outbound traffic is restricted to
      approved external destinations in every namespace.
- [ ] **Firewall team reviews, does not block** — turnaround on ANP/BANP
      reviews is under 48 hours.
- [ ] **Denied-flow triage under 30 minutes** — ACS alerts and OVN-K flow
      logs provide immediate root-cause.
- [ ] **Quarterly policy review** — all break-glass events reviewed,
      stale policies removed, ACS baselines refreshed, RBAC bindings
      audited.

### What customers wish they'd done differently

These are the top five lessons Red Hat hears from customers who have been
through this journey:

1. **"We should have started with observation, not enforcement."** Customers
   who jumped to default-deny without first running ACS in observation mode
   caused outages from denied traffic they did not know existed. The observe
   phase pays for itself.

2. **"We over-engineered the templates."** The first set of starter templates
   should be simple — three to five archetypes, not twenty. Start broad
   and refine based on actual PR volume and developer feedback.

3. **"We underestimated the EgressFirewall work."** Cataloging every
   external endpoint every service needs to reach is the most
   time-consuming part of the shift. Start this inventory in Phase 1
   alongside the ACS observation.

4. **"We should have involved the firewall team earlier."** Customers who
   presented in-cluster policy as a replacement for the firewall team met
   resistance. Customers who positioned it as "the firewall team's
   expertise applied at a new layer" got buy-in.

5. **"We needed a break-glass process on day one."** The first denied-flow
   incident in production without a break-glass process caused panic and
   a rollback of all policies. Define the break-glass process before you
   enforce anything in production.

---

## 9. Alignment with environment governance

This network policy process fits within a broader environment governance
framework covering RBAC, admission control, GitOps, and audit. The
companion document — *Kubernetes Environment Access Policies* — covers the
full stack:

| Governance layer | This document | Companion document |
|-----------------|---------------|-------------------|
| Network segmentation | NetworkPolicy, ANP, BANP, EgressFirewall — the focus here | Default-deny baseline, environment-specific allow rules |
| RBAC | Who can create/modify network policies | Full RBAC matrix by environment (dev/test/prod) |
| Admission control | Policy linting in CI (conftest, kyverno) | OPA Gatekeeper ConstraintTemplates |
| GitOps | ArgoCD sync and drift detection for policies | Full GitOps-gated production change pipeline |
| Audit | ACS baselines, OVN-K flow logs, break-glass tracking | API server audit logs, OPA decision logs, Git history |
| Namespace isolation | NetworkPolicy as one of four controls | RBAC + NetworkPolicy + ResourceQuota + LimitRange |

The network policy process described here is one vertical slice of that
broader model. Organizations should implement both together — network
segmentation without RBAC governance is incomplete, and RBAC without
network segmentation leaves east-west traffic uncontrolled.

---

## References

- [OpenShift AdminNetworkPolicy documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/network_security/admin-network-policy)
- [BaselineAdminNetworkPolicy documentation](https://docs.openshift.com/container-platform/4.16/networking/network_security/AdminNetworkPolicy/ovn-k-banp.html)
- [Using AdminNetworkPolicy API to secure OpenShift cluster networking](https://www.redhat.com/en/blog/using-adminnetworkpolicy-api-to-secure-openshift-cluster-networking)
- [OpenShift EgressFirewall documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/network_security/egress-firewall)
- [ACS — Managing network policies](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_security_for_kubernetes/3.69/html/operating/manage-network-policies)
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNCF Cloud Native Security Whitepaper](https://github.com/cncf/tag-security/tree/main/security-whitepaper)
- [Kubernetes RBAC Good Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)
- Companion: [Kubernetes Environment Access Policies](k8s-environment-policies.md)
