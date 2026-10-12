# Network Policy Process — Advisory

A recommended approach for operationalizing in-cluster network segmentation
on Kubernetes, from perimeter-only to developer-owned NetworkPolicies.

---

## What this document is

This is a recommended approach to building a network policy process
for an organization that:

- Runs perimeter and east-west controls through a firewall team on a
  traditional perimeter firewall appliance today.
- Wants to shift network segmentation left into the Kubernetes cluster using
  NetworkPolicy, ClusterNetworkPolicy, and egress rules.
- Has developers who are not security specialists — most have never written
  a firewall rule and do not inherently know what traffic their applications
  require.

**What this document is not:** a tool selection exercise or an ownership
assignment. It describes a process and a maturity path. Organizations apply
it with the teams and tools they already have. The tools named are upstream
open-source options: a CNI that enforces NetworkPolicy and ClusterNetworkPolicy
(Calico or Cilium), Kyverno or OPA Gatekeeper for admission policy, Trivy for
manifest scanning, Falco for runtime detection, and Argo CD for GitOps.

---

## 1. Where organizations typically start

Most organizations move through a four-phase maturity path. Trying to skip
phases — jumping straight to developer-authored micro-segmentation — is the
most common cause of stalled adoption.

The timeline for each phase depends on the organization's complexity, team
capacity, and risk tolerance. The four phases are sequential, each building
on the previous, but the pace is agreed upon by the organization.

### Phase 1 — Observe

Before writing any policy, understand what traffic flows today.

The CNI records the network flows between pods, namespaces, and external
destinations: Hubble with Cilium (`hubble observe`), or Calico's flow logs
(Goldmane, viewed in the Whisker console). Inspektor Gadget's
`advise_networkpolicy` gadget records the TCP and UDP traffic of chosen
namespaces. Together they give a **network baseline**, a map of every
connection the cluster has seen, which becomes the source of truth for what
traffic is expected.

At this stage, nothing is denied. The goal is visibility. The firewall team
and platform team review the observed flows together and identify:

- Which services talk to each other (and which shouldn't).
- Which services make outbound calls to external endpoints.
- Which connections cross namespace boundaries.
- Which traffic patterns were previously invisible behind the perimeter.

**What field teams typically see:** organizations are surprised by the volume of
east-west traffic they did not know existed — service-to-service connections
that were never documented because the perimeter firewall was the only
control plane.

### Phase 2 — Baseline

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

Simultaneously, **generate NetworkPolicy YAML** from the observed baseline.
Inspektor Gadget's `advise_networkpolicy` writes one policy per workload, with
ingress and egress rules based on the observed peers (Kubernetes NetworkPolicy,
or CiliumNetworkPolicy on Cilium). These generated policies are a starting
point — they capture what traffic *did* flow, not what traffic *should* flow.
On Calico, a StagedNetworkPolicy shows in the flow logs what a policy would
deny before it is enforced.

The platform team reviews the generated policies, removes any connections
that should not have existed (the audit value of this step is significant),
and applies the cleaned-up policies alongside the default-deny.

**What field teams typically see:** the first default-deny rollout in a non-prod
namespace immediately reveals undocumented dependencies — a monitoring agent
that scrapes every pod, a legacy batch job that connects to an external
database, a sidecar that phones home to a SaaS endpoint. Discovering these
in dev or test is the point.

### Phase 3 — Guardrails

With baseline policies in place, the platform team introduces cluster-scoped
guardrails using the upstream **ClusterNetworkPolicy (CNP)** API, in its
**Admin** and **Baseline** tiers.

These are the policies the platform team owns — they cannot be overridden by
developers, and they establish the security boundaries that all applications
inherit.

### Phase 4 — Developer ownership (ongoing)

App teams begin authoring and owning their own namespace-scoped
NetworkPolicies. They do this via pull request, with CI validation and
platform team review. The CI/CD flow section describes
this workflow in detail.

---

## 2. The three-tier policy model

A CNI that implements ClusterNetworkPolicy evaluates traffic against three
tiers of policy, in order. Understanding this model is critical — it
determines who controls what and where overrides are possible.

### Tier 1 — ClusterNetworkPolicy, Admin tier

- **Scope:** cluster-wide (not namespace-scoped)
- **Controlled by:** platform / infrastructure team
- **Priority:** 0 (highest) to 1000 (lowest)
- **Actions:** Accept, Deny, or **Pass** (hand evaluation to the next tier)
- **Override:** cannot be overridden by NetworkPolicy or the Baseline tier
- **Status:** `policy.networking.k8s.io/v1alpha2` (alpha, network-policy-api v0.2.0); enforced by Calico 3.32 and later, and by Cilium 1.20 when enabled

The Admin tier is where the platform team enforces non-negotiable rules: deny
traffic to the control plane from application namespaces, accept monitoring
agents scraping all pods, deny cross-environment traffic (dev → prod). A **Pass**
rule explicitly delegates the decision to the next tier (NetworkPolicy),
which is how the platform team says "app teams, this one is yours to decide."

**Critical caution:** an Admin-tier policy with an empty namespace selector
(`{}`) matches *all* namespaces, including `kube-system` and the CNI's own
namespaces. Use workload-specific label selectors. An overly broad Admin-tier
policy can lock the cluster.

### Tier 2 — NetworkPolicy (NP)

- **Scope:** namespace-scoped
- **Controlled by:** app teams (developers)
- **Override:** can be overridden by the Admin tier (which takes precedence)

This is the standard Kubernetes NetworkPolicy API. App teams use it to
define which pods in their namespace accept traffic from which sources, on
which ports. Traffic that matches an Admin-tier Accept or Deny rule never reaches
this tier; it is evaluated unless an Admin-tier rule accepted or denied the traffic.

### Tier 3 — ClusterNetworkPolicy, Baseline tier

- **Scope:** cluster-wide (one default-deny policy is the recommended shape)
- **Controlled by:** platform / infrastructure team
- **Actions:** Deny for the safety net, Accept for cluster-wide defaults such as DNS
- **Override:** *can* be overridden by NetworkPolicy

The Baseline tier is the safety net. It decides traffic that no Admin-tier rule
accepted or denied and no NetworkPolicy covers. The recommended use is **default-deny at
the Baseline tier**: if no Admin-tier rule and no NetworkPolicy allows it, the
Baseline tier denies it. This means that a namespace with no NetworkPolicies at all still has a
default-deny posture, without requiring the app team to create the
default-deny policy themselves.

The earlier releases of the API split these two tiers into
AdminNetworkPolicy and BaselineAdminNetworkPolicy (`v1alpha1`). Upstream now
lists them as previous APIs, and Calico 3.32 no longer enforces them, so new
policies use ClusterNetworkPolicy.

### How the tiers compose

*Diagram: advisory-tier-evaluation — ClusterNetworkPolicy three-tier evaluation*

![Three-tier policy evaluation](../assets/diagrams/advisory-tier-evaluation.svg)

**The value proposition for the organization:** the platform team controls tiers
1 and 3 (the guardrails). Developers control tier 2 (their application's
policies). Even if a developer writes no NetworkPolicies at all, the Baseline
default-deny ensures the namespace is not wide open. This directly addresses
the developer skill gap — the platform provides safety by default.

---

## 3. Handling the developer skill gap

Developers are not firewall engineers. Expecting them to author network
policies from scratch — knowing which ports their services listen on, which
upstream services call them, and which external endpoints they need — is
unrealistic at the start. Four complementary approaches close the gap:

### a) Generated baselines — developers review, not author

Inspektor Gadget's `advise_networkpolicy` observes traffic for a chosen window,
then generates
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

### c) The Baseline tier as a safety net

With a Baseline-tier policy that denies traffic no other policy allows, a
developer who deploys a new service without any NetworkPolicy gets
default-deny behavior automatically. Their service cannot send or receive
traffic until they (or the platform) create a policy. This is strict but
safe — it converts "I forgot to write a policy" from a security gap into a
connectivity issue that surfaces immediately in testing.

### d) Golden-path namespace provisioning

When a new namespace is provisioned (via GitOps, a self-service portal, or
an operator), the provisioning process automatically includes:

- A default-deny NetworkPolicy (a Kyverno generate rule can create it for every new namespace)
- Egress rules allowing only approved external destinations
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

*Diagram: advisory-ci-pipeline — network policy CI/CD pipeline*

![Policy CI/CD pipeline](../assets/diagrams/advisory-ci-pipeline.svg)

The pipeline stages:

1. **Developer** authors or modifies NetworkPolicy YAML and opens a PR
   against the policy repo.
2. **CI validates automatically:**
   - Schema check — `kubeconform` and `kubectl apply --dry-run=client` (valid YAML, correct API version)
   - Policy lint — conftest / `kyverno test` / `gator verify` (organizational rules: no allow-all,
     required labels, port range limits); `trivy config` scans the manifests
   - Baseline diff — compare the change with the policy generated from observed flows
     and flag rules that would allow traffic outside the baseline
   - Dry-run apply — `kubectl apply --dry-run=server` against a staging cluster
     (catches admission denials, quota issues)
3. **Platform / security team reviews the PR** — CODEOWNERS enforces: app
   team authors NetworkPolicies (platform reviews), platform authors
   ClusterNetworkPolicies and egress rules (firewall/security reviews).
4. **Merge triggers GitOps sync** — Argo CD syncs to the
   staging cluster, smoke tests validate connectivity, then syncs to
   production.
5. **Post-deploy validation** — Hubble or Calico flow logs confirm no unexpected
   flows and the expected deny counts; Falco alerts on unexpected egress at runtime.

### What generated baselines add

Inspektor Gadget's `advise_networkpolicy` gadget records the traffic of the
selected namespaces and writes the NetworkPolicy that matches it. This closes the loop between
"what traffic does my app need" (observed by the CNI) and "what policy should I
write" (generated, then validated in CI). The developer never needs to author
a policy from scratch — they generate one from the baseline, review it, and
submit the PR.

---

## 5. Repo structure

A three-layer repository model separates platform-
owned policies from application-owned policies, with clear ownership and
review boundaries.

```
cluster-policies/
│
├── platform-baselines/                    # Platform team owns
│   ├── admin-tier/
│   │   ├── deny-cross-env.yaml           # Block dev ↔ prod traffic
│   │   ├── accept-monitoring.yaml        # Prometheus/OTel can scrape all pods
│   │   ├── deny-control-plane.yaml       # Apps cannot reach API server directly
│   │   └── pass-app-traffic.yaml         # Delegate app-to-app decisions to NP tier
│   ├── baseline-tier/
│   │   └── default-deny-baseline.yaml    # Safety net: deny anything not explicitly allowed
│   ├── egress/
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
| `platform-baselines/` (Admin tier, Baseline tier, egress rules) | Platform team | Firewall / security team | Cluster-wide |
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

1. **Compare with the baseline** — check whether the connection is in the
   observed baseline (the generated policies in Git). If it is not, it was
   likely never policy-allowed. Decide whether to add
   a policy or investigate why the new connection exists.

2. **Flow logs** — `hubble observe --verdict DROPPED` (Cilium) or the Calico
   flow logs show the dropped flow with source pod, destination and port.
   Match it with the policies that select the pod to find *which tier*
   denied the traffic (Admin, NP, or Baseline), which
   tells you who needs to update the policy.

3. **Diagnostics bundle** — `cilium sysdump` or `calicoctl cluster diags`
   collects network policy state, CNI configuration, and logs for offline
   analysis. Use it for an upstream issue or for escalation to your support
   provider.

**Target:** denied-flow triage should take under 30 minutes. If it
regularly takes longer, the observability tooling (flow logs, baselines) is not
configured correctly.

### Break-glass process

When a denied flow is blocking a production incident and the normal PR
process is too slow:

1. A platform team member creates a **temporary Admin-tier policy with a Pass rule** at a
   high priority (low number), handing the traffic decision to the
   NetworkPolicy tier. If no NetworkPolicy exists for the target, the Baseline tier
   (if configured as default-deny) will still deny, so the break-glass
   may need a temporary NetworkPolicy as well.

2. The temporary rule is **time-boxed** (label it with an expiration date
   annotation) and **logged** (create an incident ticket referencing the
   change).

3. Within 24 hours, the proper policy change goes through the normal PR
   and CI pipeline. The temporary rule is removed.

4. All break-glass events are reviewed in the quarterly policy review.

### Drift detection

- **Argo CD** reports sync status for every policy
  manifest. If someone manually applies a policy via `kubectl apply` instead
  of the PR pipeline, Argo CD detects the drift and either alerts or
  auto-reverts (self-heal, depending on configuration).

- **Baseline drift** — if new traffic flows appear that are not in
  the observed baseline, the flow logs and Falco flag them. This catches
  both policy drift (someone added a rule manually) and application
  drift (a new service started making unexpected connections).

### Policy coverage reporting

Maintain a dashboard or periodic report showing:

- Namespaces with default-deny in place vs. those without.
- Namespaces with reviewed baselines vs. those still in observation.
- Admin-tier and Baseline-tier rules in effect and their last-modified dates.
- Break-glass events in the current quarter.
- Denied-flow triage times (mean, p95).

---

## 7. The firewall team's evolving role

The shift to in-cluster network policy does not eliminate the firewall team.
It changes their scope and moves their role from gatekeeper to architect.

### What stays with the firewall team

- **North-south edge controls** — the perimeter firewall
  continues to manage traffic entering and leaving the data center or
  cloud VPC. This is where TLS inspection, DDoS mitigation, and
  compliance logging (PCI, HIPAA) remain.

- **Egress rule authorship** — the firewall team authors and reviews
  the egress rules that control which external destinations cluster
  workloads can reach. This is their domain expertise (approved CIDRs,
  DNS-based rules, compliance-required blocks).

- **Admin and Baseline tier review** — the firewall team reviews all cluster-scoped
  network policies (the Admin and Baseline tiers) because these have cluster-wide blast
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

*Diagram: advisory-team-ownership — policy ownership model*

![Policy ownership model](../assets/diagrams/advisory-team-ownership.svg)

The firewall team moves from "approve every rule" to "set the boundaries
and review the exceptions." This is faster for developers, safer for the
organization, and a better use of the firewall team's expertise.

---

## 8. What "good" looks like at maturity

### Maturity checklist

After sustained effort over a maturity period agreed upon by the
organization, a mature network policy practice looks like this:

- [ ] **Default-deny in every namespace** — no namespace exists without a
      default-deny NetworkPolicy or Baseline-tier coverage.
- [ ] **Baselines reviewed** — every production namespace has a reviewed
      baseline in Git. New flows outside it raise alerts.
- [ ] **Admin-tier guardrails enforced** — cross-environment traffic blocked,
      monitoring access allowed, control-plane access restricted.
- [ ] **Baseline-tier default-deny** — the cluster-wide safety net catches any
      traffic not explicitly allowed by the Admin tier or NetworkPolicy.
- [ ] **App teams authoring policies via PR** — developers submit
      NetworkPolicy changes through the CI/CD pipeline, not `kubectl apply`.
- [ ] **CI validates before merge** — schema checks, policy linting, baseline
      diff, and dry-run apply run on every PR.
- [ ] **Egress rules per namespace** — outbound traffic is restricted to
      approved external destinations in every namespace.
- [ ] **Firewall team reviews, does not block** — turnaround on Admin and Baseline tier
      reviews is under 48 hours.
- [ ] **Denied-flow triage under 30 minutes** — flow logs and Falco alerts
      provide immediate root-cause.
- [ ] **Quarterly policy review** — all break-glass events reviewed,
      stale policies removed, baselines refreshed, RBAC bindings
      audited.

### What organizations wish they'd done differently

These are the five lessons heard most often from organizations that have
completed this transition:

1. **"We should have started with observation, not enforcement."** Teams
   that jumped to default-deny without first observing the flows
   caused outages from denied traffic they did not know existed. The observe
   phase pays for itself.

2. **"We over-engineered the templates."** The first set of starter templates
   should be simple — three to five archetypes, not twenty. Start broad
   and refine based on actual PR volume and developer feedback.

3. **"We underestimated the egress work."** Cataloging every
   external endpoint every service needs to reach is the most
   time-consuming part of the shift. Start this inventory in Phase 1
   alongside the flow observation.

4. **"We should have involved the firewall team earlier."** Teams that
   presented in-cluster policy as a replacement for the firewall team met
   resistance. Teams that positioned it as "the firewall team's
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
| Network segmentation | NetworkPolicy, ClusterNetworkPolicy (Admin and Baseline tiers), egress rules: the focus here | Default-deny baseline, environment-specific allow rules |
| RBAC | Who can create/modify network policies | Full RBAC matrix by environment (dev/test/prod) |
| Admission control | Policy linting in CI (conftest, kyverno) | OPA Gatekeeper ConstraintTemplates |
| GitOps | Argo CD sync and drift detection for policies | Full GitOps-gated production change pipeline |
| Audit | Flow logs, Falco alerts, break-glass tracking | API server audit logs, OPA decision logs, Git history |
| Namespace isolation | NetworkPolicy as one of four controls | RBAC + NetworkPolicy + ResourceQuota + LimitRange |

The network policy process described here is one vertical slice of that
broader model. Organizations should implement both together — network
segmentation without RBAC governance is incomplete, and RBAC without
network segmentation leaves east-west traffic uncontrolled.

---

## References

- [Kubernetes Network Policy API: ClusterNetworkPolicy](https://network-policy-api.sigs.k8s.io/)
- [network-policy-api v0.2.0 release notes](https://github.com/kubernetes-sigs/network-policy-api/releases/tag/v0.2.0)
- [Network Policy API implementations](https://network-policy-api.sigs.k8s.io/implementations/)
- [Calico v3.32 release notes: ClusterNetworkPolicy](https://github.com/projectcalico/calico/blob/release-v3.32/release-notes/v3.32.0-release-notes.md)
- [Cilium: Kubernetes network policy](https://docs.cilium.io/en/stable/network/kubernetes/policy/)
- [Inspektor Gadget: advise_networkpolicy](https://inspektor-gadget.io/docs/latest/gadgets/advise_networkpolicy)
- [Kyverno policy: add-network-policy](https://kyverno.io/policies/best-practices/add-network-policy/add-network-policy/)
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNCF Cloud Native Security Whitepaper](https://github.com/cncf/tag-security/tree/main/security-whitepaper)
- [Kubernetes RBAC Good Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)
- Companion: [Kubernetes Environment Access Policies](k8s-environment-policies.md)
