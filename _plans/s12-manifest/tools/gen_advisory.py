#!/usr/bin/env python3
"""Decision 7: the Network-Policy-Process-Advisory deck reworked to upstream Kubernetes and open source.

Same process and phases; ACS, OpenShift (OVN-Kubernetes, EgressFirewall, oc, OpenShift GitOps) and the
Red Hat attribution of the recommendations are replaced by upstream APIs and open-source tools. Facts and
citations: _plans/s12-manifest/Network-Policy-Process-Advisory.md. Writes the whole edit file (the earlier
voice and link ops are superseded: every slide's text and notes are set here).
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "lgtm-presentation" / "edits" / "Network-Policy-Process-Advisory.json"
P = "lgtm-presentation/edits/png/"

# sldId: (eyebrow or None, title or None, body paragraphs or None, caption or None, caption shape, notes)
S = {}
S[256] = dict(title=["Network Policy Process",
                     "Advisory — Shifting from perimeter to in-cluster segmentation."], notes=[
    "Welcome the audience and set context. This deck presents a recommended approach for operationalizing "
    "in-cluster network segmentation on Kubernetes, with upstream APIs and open-source tools. The starting point "
    "is common: perimeter and east-west controls run through the firewall team on a traditional appliance, there "
    "is no in-cluster network policy, and developers have never written a firewall rule. The goal is not to pick "
    "tools or assign owners; it is to describe a process and a maturity path that the organization can adopt at "
    "its own pace. We will walk through where organizations typically start, how to handle the developer skill "
    "gap, the CI/CD flow for policy changes, repo structure, day-two operations, the firewall team's evolving "
    "role, and what maturity looks like. Ask the audience: do you have a documented process for who authors, "
    "reviews, and approves network policies in your clusters today? The answer usually reveals the gap this deck "
    "fills."])
S[257] = dict(body=[
    "Perimeter and east-west controls run through the firewall team on a traditional appliance today.",
    "The organization wants to shift network segmentation left into the cluster (NetworkPolicy, "
    "ClusterNetworkPolicy, egress rules) but has not defined the workflow.",
    "Developers are not security specialists. Most have never written a firewall rule and don't inherently know "
    "what traffic their applications require.",
    "The goal: a recommended process for operationalizing in-cluster network segmentation, not a tool selection "
    "exercise or an ownership assignment.",
], caption="A recommended approach, built on upstream Kubernetes and open-source tools.", notes=[
    "Frame the current state without judgment. The perimeter firewall handles everything: north-south and "
    "east-west traffic controls run through the firewall team on the perimeter appliance. There is no Kubernetes "
    "NetworkPolicy in the cluster. Developers are not security specialists; most have never written a firewall "
    "rule and do not inherently know what traffic their applications require. This is not unusual. Most "
    "organizations start in exactly this position. The shift to in-cluster segmentation is not about replacing "
    "the firewall team or the perimeter; it is about extending the organization's security posture into a layer "
    "the perimeter cannot see. The perimeter firewall has no visibility into pod-to-pod traffic inside the "
    "cluster. A compromised pod behind the perimeter can reach every other pod unless the cluster itself "
    "enforces segmentation. That is the gap this process fills."])
S[258] = dict(title="The four-phase maturity path", body=[
    "Phase 1 — Observe: understand what traffic flows today from the CNI's flow logs (Hubble or Calico). No "
    "enforcement yet.",
    "Phase 2 — Baseline: apply default-deny in every namespace, generate policies from the observed flows, clean "
    "them up.",
    "Phase 3 — Guardrails: introduce cluster-scoped ClusterNetworkPolicy (Admin and Baseline tiers) owned by the "
    "platform team.",
    "Phase 4 — Developer ownership: app teams author and own their namespace-scoped NetworkPolicies via PR.",
    "The timeline for each phase depends on the organization's complexity, team capacity, and risk tolerance. "
    "Each phase builds on the previous.",
], notes=[
    "Walk through the four phases. The most important point is that these are sequential and the timeline "
    "depends on the organization's complexity and risk tolerance. Phase 1 is observation: reading the CNI's flow "
    "logs to discover what traffic flows before writing any policy. Phase 2 is baseline: applying default-deny "
    "and cleaning up policies generated from the observed flows. Phase 3 is guardrails: the platform team "
    "introduces cluster-scoped ClusterNetworkPolicy rules in the Admin and Baseline tiers that developers cannot "
    "override. Phase 4 is developer ownership: app teams author their own namespace-scoped NetworkPolicies via "
    "pull request. The most common failure is skipping Phase 1 and jumping straight to enforcement; teams that "
    "did this caused outages from denied traffic they did not know existed. The observation phase pays for "
    "itself by revealing undocumented dependencies and unauthorized connections. Stress that each phase builds "
    "on the previous: you cannot do Phase 3 well without Phase 2's baseline, and Phase 2 is reckless without "
    "Phase 1's visibility."])
S[259] = dict(title="Observe the flows", body=[
    "The CNI records flows between pods, namespaces, and external destinations: Hubble with Cilium, flow logs "
    "(Goldmane, Whisker) with Calico.",
    "Inspektor Gadget's advise_networkpolicy gadget records the TCP and UDP traffic of chosen namespaces. "
    "Together they give the network baseline, the source of truth for what traffic is expected.",
    "The firewall team and platform team review the flows together and identify which services talk to each "
    "other, which make outbound calls, and which cross namespace boundaries.",
    "What field teams typically see: organizations are surprised by the volume of east-west traffic that was "
    "invisible behind the perimeter.",
], notes=[
    "Explain what observation means without a commercial console. The CNI already sees every flow. With "
    "Cilium, Hubble shows them (hubble observe, or the Hubble UI); with Calico 3.30 and later, Felix sends flow "
    "logs to Goldmane and the Whisker console shows them. Inspektor Gadget, a CNCF Sandbox project, adds the "
    "advise_networkpolicy gadget: it records the TCP and UDP traffic of the namespaces you choose and later "
    "turns it into NetworkPolicy YAML. At this stage, nothing is denied. The goal is pure visibility. The "
    "firewall team and platform team review the observed flows together. They identify which services talk to "
    "each other and which should not, which services make outbound calls to external endpoints, which "
    "connections cross namespace boundaries, and which traffic patterns were previously invisible behind the "
    "perimeter. What field teams typically see: organizations are surprised by the volume of east-west traffic "
    "they did not know existed. A frontend directly querying a database it should go through an API for. A "
    "monitoring agent making outbound calls to a SaaS endpoint. Discovery is the highest-value step."])
S[260] = dict(title="Baseline: default-deny + generated policies", body=[
    "Apply default-deny NetworkPolicy in every namespace — the single highest-impact security measure.",
    "Generate NetworkPolicy YAML from the observed flows: advise_networkpolicy writes one policy per workload, "
    "with rules from the observed peers.",
    "Generated policies capture what traffic did flow, not what should flow. The platform team reviews, removes "
    "unauthorized connections, and applies cleaned-up policies alongside default-deny.",
    "The first default-deny rollout reveals undocumented dependencies — monitoring agents, legacy batch jobs, "
    "SaaS sidecars. Discovering these in dev/test is the point.",
], caption="Generated policies are a starting point, not the final state.", notes=[
    "Walk through the baseline phase. The first action is applying default-deny NetworkPolicy in every "
    "namespace: podSelector empty, policyTypes Ingress and Egress. This is the single highest-impact security "
    "measure. Simultaneously, generate NetworkPolicy YAML from the observed flows. Inspektor Gadget's "
    "advise_networkpolicy writes one policy per workload, with ingress and egress rules based on the peers it "
    "saw; it can also write CiliumNetworkPolicy. On Calico, a StagedNetworkPolicy shows in the flow logs what a "
    "policy would deny before it is enforced. These generated policies capture what traffic did flow, not what "
    "traffic should flow. The platform team reviews them, removes connections that should not have existed, "
    "and applies the cleaned-up policies alongside the default-deny. This audit step finds the connections "
    "nobody documented. The first default-deny rollout in a non-prod namespace immediately reveals undocumented "
    "dependencies: a monitoring agent scraping every pod, a legacy batch job connecting to an external "
    "database, a sidecar phoning home to a SaaS endpoint. Discovering these in dev or test is the point."])
S[261] = dict(body=[
    "Phase 3: the platform team introduces cluster-scoped guardrails with ClusterNetworkPolicy, in its Admin and "
    "Baseline tiers. These are the policies developers cannot override.",
    "Phase 4: app teams begin authoring their own namespace-scoped NetworkPolicies via pull request, with CI "
    "validation and platform team review.",
    "The transition from Phase 3 to Phase 4 is gradual — developers start by reviewing generated baselines, then "
    "modify them, then eventually author from scratch.",
    "The platform team controls the guardrails. Developers control their application connectivity. Even if a "
    "developer writes no policies at all, the Baseline tier ensures default-deny.",
], caption="The Baseline tier addresses the developer skill gap directly: safety by default.", notes=[
    "Explain the transition from platform-owned guardrails to developer ownership. In Phase 3, the platform "
    "team introduces ClusterNetworkPolicy rules in the Admin and Baseline tiers: cluster-scoped rules that "
    "developers cannot override. They enforce non-negotiable boundaries: deny cross-environment traffic, accept "
    "monitoring, restrict control-plane access. In Phase 4, app teams begin authoring their own namespace-scoped "
    "NetworkPolicies. The transition is gradual: developers start by reviewing generated baselines, then modify "
    "them, then eventually author from scratch as they build familiarity. The key architectural point: even if "
    "a developer writes no NetworkPolicies at all, the Baseline-tier default-deny keeps the namespace closed. "
    "This directly addresses the developer skill gap: the platform provides safety by default, and developers "
    "add precision as they learn. This is a fundamentally different model from asking every developer to be a "
    "firewall engineer."])
S[262] = dict(body=[
    "Tier 1 — ClusterNetworkPolicy, Admin tier: cluster-scoped, priority 0-1000, Accept/Deny/Pass. Cannot be "
    "overridden by tenants.",
    "Tier 2 — NetworkPolicy (NP): namespace-scoped, owned by app teams. Only evaluated if the Admin tier passed "
    "the traffic.",
    "Tier 3 — ClusterNetworkPolicy, Baseline tier: cluster-scoped safety net. Overridable by NetworkPolicy.",
    "Admin Accept/Deny are final — NP and the Baseline tier are skipped. Admin Pass hands evaluation to the next "
    "tier.",
], caption="Platform team controls tiers 1 and 3. App teams control tier 2.", caption_shape=6, notes=[
    "This is the most important conceptual slide. A CNI that implements the upstream ClusterNetworkPolicy API "
    "evaluates traffic against three tiers of policy. Tier 1 is the Admin tier: cluster-scoped, priority zero "
    "to one thousand, with Accept, Deny, or Pass actions. If the traffic matches an Admin Accept or Deny rule, "
    "tiers 2 and 3 are skipped entirely. If it matches a Pass rule, evaluation hands to tier 2. Tier 2 is "
    "standard Kubernetes NetworkPolicy: namespace-scoped, owned by app teams. Tier 3 is the Baseline tier, the "
    "safety net: it catches traffic that the Admin tier passed and no NetworkPolicy matched. Point to the "
    "diagram showing the evaluation flow. The value proposition: the platform team controls tiers 1 and 3, the "
    "guardrails. Developers control tier 2, their application's policies. This separation of concerns is what "
    "makes the model scalable."])
S[263] = dict(eyebrow="ADMIN · BASELINE", title="ClusterNetworkPolicy: Admin and Baseline tiers", body=[
    "The Admin tier enforces non-negotiable rules: deny traffic to the control plane, accept monitoring agents "
    "scraping all pods, deny cross-environment traffic (dev → prod).",
    "A Pass rule explicitly delegates to the NetworkPolicy tier — the platform team says 'app teams, this one is "
    "yours to decide.'",
    "The Baseline tier is the safety net. Recommended: a default-deny Baseline policy. If no Admin rule and no NP "
    "allows the traffic, the Baseline tier denies it.",
    "Critical: an Admin-tier policy with an empty namespace selector ({}) matches all namespaces including "
    "kube-system and the CNI's own. Use workload-specific label selectors.",
], caption="An overly broad Admin-tier policy can lock the cluster. Use workload-specific labels.", notes=[
    "Dive deeper into the two cluster tiers. The Admin tier enforces non-negotiable rules: deny traffic to the "
    "control plane from application namespaces, accept monitoring agents scraping all pods, deny "
    "cross-environment traffic like dev to prod. A Pass rule explicitly delegates the decision to the "
    "NetworkPolicy tier: this is how the platform team says app teams, this one is yours to decide. The Baseline "
    "tier is the safety net, configured as default-deny. If no Admin rule and no NetworkPolicy allows the "
    "traffic, the Baseline tier denies it, so a namespace with no NetworkPolicies still has a default-deny "
    "posture without the app team creating it. Critical caution: an Admin-tier policy with an empty namespace "
    "selector matches all namespaces, including kube-system and the CNI's own namespaces. This can lock the "
    "cluster. Label application namespaces and use that label as the namespace selector.",
    "Status, as of network-policy-api v0.2.0 (April 2026): ClusterNetworkPolicy is "
    "policy.networking.k8s.io/v1alpha2, an alpha API. It merged the earlier AdminNetworkPolicy and "
    "BaselineAdminNetworkPolicy (v1alpha1), which upstream now lists as previous APIs, and renamed Allow to "
    "Accept. Calico enforces it from 3.32 and no longer enforces the old pair; Cilium 1.20 enforces it behind "
    "the k8sClusterNetworkPolicy.enabled Helm value. Check the release notes before each upgrade."])
S[264] = dict(body=[
    "Generated baselines: developers review generated policies, not author from scratch. Reviewing a concrete "
    "policy is dramatically easier than writing one from zero.",
    "Platform-authored starter templates: web-facing service, internal API, batch job, database archetypes. "
    "Developers pick the template, customize selectors, submit a PR.",
    "The Baseline tier as safety net: a developer who deploys without any NetworkPolicy gets default-deny "
    "automatically. Missing policies become connectivity issues, not security gaps.",
    "Golden-path provisioning: new namespaces come with default-deny (a Kyverno generate rule), egress rules, "
    "starter templates, and RBAC bindings pre-installed.",
], notes=[
    "Walk through the four approaches for bridging the developer skill gap. First, generated baselines invert "
    "the skill requirement: developers review a policy generated from observed flows, they do not author one "
    "from scratch. Reviewing a concrete policy (does this look right, should this connection exist) is "
    "dramatically easier than writing one from zero. Second, platform-authored starter templates for common "
    "workload archetypes: web-facing, internal API, batch job, database. Developers pick the template, customize "
    "the namespace and label selectors, and submit a PR. Third, the Baseline tier as a safety net converts "
    "missing policies from a security gap into a connectivity issue that surfaces immediately in testing. "
    "Fourth, golden-path namespace provisioning includes default-deny, egress rules, starter templates, and RBAC "
    "bindings automatically; Kyverno's add-network-policy sample is a generate rule that creates the "
    "default-deny NetworkPolicy in every new namespace. The developer starts with a secured namespace and never "
    "sees the everything-is-open starting point that leads to procrastination."])
S[266] = dict(body=[
    "Schema check: kubeconform and kubectl apply --dry-run=client validate YAML and API version.",
    "Policy lint: conftest / kyverno test / gator verify enforce organizational rules (no allow-all, required "
    "labels); trivy config scans the manifests.",
    "Baseline diff: compare the change with the policy generated from observed flows; flag traffic outside the "
    "baseline.",
    "Review: CODEOWNERS enforces — app teams author NP (platform reviews), platform authors ClusterNetworkPolicy "
    "(firewall reviews).",
], caption_shape=6, notes=[
    "Walk through the policy CI/CD pipeline. Every policy change (NetworkPolicy, ClusterNetworkPolicy, egress "
    "rules) flows through the same pipeline. Schema check with kubeconform and kubectl apply --dry-run=client "
    "catches invalid YAML and wrong API versions. Policy lint with conftest, kyverno test or Gatekeeper's gator "
    "verify catches organizational policy violations like allow-all rules or missing labels, and trivy config "
    "scans the manifests (its KSV-0038 check flags network policies without pod or namespace selectors). The "
    "baseline diff compares the change with the policy generated from observed flows and flags rules that would "
    "allow traffic outside the baseline. Platform or security team reviews the PR; CODEOWNERS enforces who "
    "reviews based on the file path. Merge triggers an Argo CD sync to staging, smoke tests validate "
    "connectivity, then sync to production. Post-deploy validation reads the Hubble or Calico flow logs, and "
    "Falco alerts on unexpected egress at runtime. Point to the diagram. The key principle: the CI pipeline is "
    "the only path to production. No exceptions, no emergency kubectl apply, no just this once."])
S[265] = dict(notes=None)  # unchanged
S[267] = dict(body=[
    "platform-baselines/ — ClusterNetworkPolicy (Admin and Baseline tiers) and egress rules. Platform team "
    "authors, firewall/security team reviews. Cluster-wide scope.",
    "onboarding/ — starter NetworkPolicy templates per workload archetype. Platform team maintains, app teams "
    "consume.",
    "app-policies/ — per-namespace NetworkPolicy. App teams author, platform team reviews. Kustomize overlays "
    "for dev/test/prod.",
    "CODEOWNERS enforces review requirements by path. The same PR flow applies regardless of target "
    "environment.",
], notes=[
    "Describe the three-layer repository model. The platform-baselines directory contains the "
    "ClusterNetworkPolicy resources of the Admin and Baseline tiers and the egress rules: cluster-scoped "
    "policies authored by the platform team and reviewed by the firewall and security team. The onboarding "
    "directory contains starter NetworkPolicy templates per workload archetype, maintained by the platform team "
    "and consumed by app teams as starting points. The app-policies directory contains per-namespace "
    "NetworkPolicies authored by app teams, with base and overlay directories for Kustomize-based environment "
    "promotion. CODEOWNERS enforces review requirements by path: platform-baselines requires firewall team "
    "review, app-policies requires platform team review. This separation provides clear ownership boundaries. "
    "The same PR that modifies a policy flows through the same CI pipeline regardless of whether it targets "
    "dev, test, or production; only the Kustomize overlay differs."])
S[268] = dict(body=[
    "Firewall team: authors egress rules, reviews the Admin and Baseline tiers, owns the perimeter firewall "
    "(north-south and compliance).",
    "Platform team: authors ClusterNetworkPolicy guardrails and starter templates, reviews app NetworkPolicies, "
    "owns cluster security posture.",
    "App teams: author namespace-scoped NetworkPolicy, consume templates and generated baselines, own "
    "application connectivity.",
    "The firewall team moves from 'approve every rule' to 'set the boundaries and review the exceptions.'",
], caption_shape=6, notes=[
    "Describe the three-team ownership model and point to the diagram. The firewall team authors the egress "
    "rules for external destinations, reviews all cluster-scoped policies (the Admin and Baseline tiers) "
    "because they have cluster-wide blast radius, and continues to own the perimeter for north-south traffic, "
    "TLS inspection, and compliance logging. The platform team authors the ClusterNetworkPolicy guardrails, "
    "maintains starter templates, reviews app team NetworkPolicies, and owns the overall cluster security "
    "posture. App teams author namespace-scoped NetworkPolicy for their services, consume starter templates and "
    "generated baselines, and own their application's connectivity. The critical framing: the firewall team "
    "moves from approve every rule to set the boundaries and review the exceptions. This is faster for "
    "developers, safer for the organization, and a better use of the firewall team's expertise."])
S[269] = dict(body=[
    "Step 1: compare with the observed baseline — was this connection ever in the generated policies in Git?",
    "Step 2: read the flow logs (hubble observe --verdict DROPPED, or Calico's flow logs) and match the dropped "
    "flow to the policies that select the pod: which tier (Admin, NP, or Baseline) denied it tells you who "
    "updates the policy.",
    "Step 3: cilium sysdump or calicoctl cluster diags collects policy state, CNI configuration, and logs for "
    "offline analysis or escalation.",
    "Target: denied-flow triage should take under 30 minutes. If it takes longer, the observability tooling is "
    "not configured correctly.",
], caption="The flow logs and the tier that matched say who owns the fix.", notes=[
    "Walk through the denied-flow triage process. When a developer reports my service cannot reach X, the "
    "first step is comparing with the observed baseline: was this connection ever in the generated policies "
    "kept in Git? If not, it was likely never policy-allowed, and the decision is whether to add a policy or "
    "investigate why the new connection exists. The second step is the flow logs: hubble observe with "
    "--verdict DROPPED on Cilium, or the Calico flow logs in Whisker, show the dropped flow with source pod, "
    "destination and port. Matching it to the policies that select the pod tells you which tier denied the "
    "traffic: Admin, NetworkPolicy, or Baseline. If the Admin tier denied it, the platform team needs to act. "
    "If a NetworkPolicy denied it, the app team updates their policy. If the Baseline tier denied it, no one "
    "wrote a policy for this connection at all. The third step is a diagnostics bundle, cilium sysdump or "
    "calicoctl cluster diags, for offline analysis, an upstream issue, or escalation to your support provider. "
    "The target is under 30 minutes for triage. If it regularly takes longer, the observability tooling is not "
    "configured correctly."])
S[270] = dict(body=[
    "Break-glass: platform team creates a temporary Admin-tier Pass rule at high priority, time-boxed with an "
    "expiration annotation, logged via incident ticket. Proper policy change follows within 24 hours via normal "
    "PR.",
    "Argo CD drift detection: if someone manually applies a policy via kubectl apply instead of the PR pipeline, "
    "Argo CD detects the drift and alerts or reverts it (self-heal).",
    "Baseline drift: new flows outside the observed baseline show up in the flow logs and Falco alerts — catches "
    "both policy drift and application drift.",
    "All break-glass events are reviewed in the quarterly policy review.",
], notes=[
    "Explain the break-glass process and drift detection. When a denied flow is blocking a production incident "
    "and the normal PR process is too slow, a platform team member creates a temporary Admin-tier "
    "ClusterNetworkPolicy with a Pass rule at high priority. This is time-boxed with an expiration annotation "
    "and logged via an incident ticket. If the Baseline tier is default-deny and no NetworkPolicy covers the "
    "target, a temporary NetworkPolicy is needed as well. Within 24 hours, the proper policy change goes "
    "through the normal PR and CI pipeline, and the temporary rule is removed. All break-glass events are "
    "reviewed in the quarterly policy review. For drift detection: Argo CD reports sync status for every policy "
    "manifest; if someone manually applies a policy, Argo CD detects the drift and alerts, or reverts it when "
    "self-heal is on. Baseline drift catches new traffic flows outside the observed baseline, whether from "
    "policy changes or application changes. The critical lesson: define the break-glass process before you "
    "enforce anything in production. The first denied-flow incident without a break-glass process causes panic "
    "and a rollback of all policies."])
S[271] = dict(body=[
    "What stays: north-south edge controls (the perimeter firewall for TLS inspection, DDoS, compliance "
    "logging), egress rule authorship (approved CIDRs, DNS rules), Admin and Baseline tier review (cluster-wide "
    "blast radius).",
    "What shifts: east-west traffic segmentation moves to NetworkPolicy authored by app teams. The firewall team "
    "does not approve every pod-to-pod rule — that does not scale.",
    "The new model: the firewall team's expertise is applied at a new layer. Position this as elevation, not "
    "replacement.",
    "Teams that presented in-cluster policy as a replacement met resistance. Teams that positioned it as the "
    "firewall team's expertise at a new layer got buy-in.",
], notes=[
    "Frame the firewall team's evolving role as elevation, not replacement. What stays with the firewall team: "
    "north-south edge controls on the perimeter firewall for TLS inspection, DDoS mitigation, and compliance "
    "logging. Egress rule authorship: the firewall team catalogs approved external destinations and authors the "
    "egress rules, which is their domain expertise. Admin and Baseline tier review: the firewall team reviews "
    "all cluster-scoped policies because they have cluster-wide blast radius. What shifts to the platform and "
    "app teams: east-west traffic segmentation is handled by NetworkPolicy authored by app teams. The firewall "
    "team does not need to approve every pod-to-pod rule; that does not scale. The key framing: teams that "
    "presented in-cluster policy as a replacement for the firewall team met resistance. Teams that positioned "
    "it as the firewall team's expertise applied at a new layer got buy-in."])
S[272] = dict(eyebrow="EGRESS", body=[
    "Admin-tier ClusterNetworkPolicy egress rules with networks peers (CIDR, standard channel) restrict outbound "
    "traffic cluster-wide.",
    "DNS-based rules: CNP domainNames peers are experimental and Accept-only; Cilium's toFQDNs "
    "(CiliumNetworkPolicy) gives DNS-based egress today.",
    "The firewall team's domain: they catalog approved external endpoints and author the egress rules per "
    "environment.",
    "Combine with NetworkPolicy: NetworkPolicy for intra-cluster segmentation, cluster egress rules for external "
    "traffic control. They complement each other.",
], notes=[
    "Explain egress control with upstream APIs. A ClusterNetworkPolicy in the Admin tier can carry egress rules "
    "whose peers are networks, CIDR ranges, which is part of the standard channel; deny everything outside the "
    "approved ranges and accept the approved ones. DNS names are harder: the domainNames peer of "
    "ClusterNetworkPolicy is in the experimental channel and only valid in Accept rules, and Calico's "
    "open-source edition has no DNS-based policy. On Cilium, a CiliumNetworkPolicy with toFQDNs gives DNS-based "
    "egress today, through Cilium's DNS proxy, which matters for external services that change IP addresses "
    "without notice. The firewall team's domain: they catalog approved external endpoints and author the egress "
    "rules. This extends what they already do at the perimeter, controlling which destinations workloads can "
    "reach, to the cluster level, where the perimeter has no visibility. Combine the two: NetworkPolicy for "
    "intra-cluster segmentation, cluster egress rules for external traffic control. Caveat: DNS-based rules "
    "depend on the DNS answers the cluster sees, so test them against the real resolvers."])
S[273] = dict(body=[
    "Default-deny in every namespace — no namespace without coverage.",
    "Baselines reviewed — new flows outside them raise alerts.",
    "Admin-tier guardrails enforced — cross-environment traffic blocked, monitoring allowed.",
    "Baseline-tier default-deny — the cluster-wide safety net catches unmatched traffic.",
    "App teams authoring policies via PR — not kubectl apply.",
    "CI validates before merge — schema, lint, baseline diff, dry-run on every PR.",
    "Egress rules per environment — outbound traffic restricted to approved destinations.",
    "Denied-flow triage under 30 minutes. Quarterly policy review cadence.",
], notes=[
    "Walk through the maturity checklist. Default-deny in every namespace: no namespace without coverage. "
    "Baselines reviewed: every production namespace has a reviewed baseline in Git, and new flows outside it "
    "raise alerts. Admin-tier guardrails enforced: cross-environment traffic blocked, monitoring allowed, "
    "control-plane access restricted. Baseline-tier default-deny: the cluster-wide safety net catches any "
    "traffic not explicitly allowed. App teams authoring policies via PR, not kubectl apply. CI validates "
    "before merge: schema checks, policy linting, the baseline diff, and dry-run apply on every PR. Egress rules "
    "restrict outbound traffic to approved destinations. Firewall team reviews, does not block: turnaround on "
    "Admin and Baseline tier reviews is prompt. Denied-flow triage under 30 minutes. Quarterly policy review "
    "cadence covering break-glass events, stale policies, baseline refreshes, and RBAC audits. The maturity "
    "timeline is agreed upon by the organization; there is no universal pace."])
S[274] = dict(title="What teams wish they'd done", body=[
    "1. 'We should have started with observation, not enforcement.' Jumping to default-deny without observing "
    "the flows caused outages from denied traffic they didn't know existed.",
    "2. 'We over-engineered the templates.' Start with 3-5 archetypes, not twenty. Refine based on actual usage.",
    "3. 'We underestimated the egress work.' Cataloging every external endpoint is the most time-consuming part. "
    "Start this inventory in Phase 1.",
    "4. 'We should have involved the firewall team earlier.' Position as elevation, not replacement.",
    "5. 'We needed a break-glass process on day one.' The first denied-flow incident without break-glass caused "
    "panic and a rollback of all policies.",
], caption="These lessons come from real engagements.", notes=[
    "Walk through the top five lessons from real engagements. First, teams that jumped to default-deny without "
    "observing the flows caused outages from denied traffic they did not know existed. The observation phase "
    "pays for itself. Second, the first set of starter templates should be simple: three to five archetypes, "
    "not twenty. Start broad and refine based on actual PR volume. Third, cataloging every external endpoint "
    "every service needs to reach is the most time-consuming part of the shift. Start this inventory in Phase 1 "
    "alongside the flow observation. Fourth, teams that presented in-cluster policy as a replacement for the "
    "firewall team met resistance; teams that positioned it as the firewall team's expertise applied at a new "
    "layer got buy-in. Fifth, the first denied-flow incident in production without a break-glass process caused "
    "panic and a rollback of all policies. Define break-glass before you enforce. These lessons are from real "
    "engagements: they are patterns, not hypotheticals."])
S[275] = dict(body=[
    "Network Policy API (ClusterNetworkPolicy) — network-policy-api.sigs.k8s.io",
    "network-policy-api v0.2.0 release — github.com/kubernetes-sigs/network-policy-api/releases/tag/v0.2.0",
    "Calico ClusterNetworkPolicy (v3.32 release notes) — github.com/projectcalico/calico, release-notes/"
    "v3.32.0-release-notes.md",
    "Cilium network policy — docs.cilium.io/en/stable/network/kubernetes/policy/",
    "Inspektor Gadget advise_networkpolicy — inspektor-gadget.io/docs/latest/gadgets/advise_networkpolicy",
    "Kubernetes Network Policies — kubernetes.io/docs/concepts/services-networking/network-policies/",
    "Companion: Kubernetes Environment Access Policies (k8s-environment-policies.md)",
], notes=[
    "Point the audience to authoritative sources. The Network Policy API site covers ClusterNetworkPolicy, its "
    "Admin and Baseline tiers and the list of implementations. The v0.2.0 release notes record the move from "
    "AdminNetworkPolicy and BaselineAdminNetworkPolicy to ClusterNetworkPolicy and the Allow-to-Accept rename. "
    "The Calico 3.32 release notes and the Cilium network policy page say how each CNI enforces it. The "
    "Inspektor Gadget page covers generating NetworkPolicy from observed traffic. The Kubernetes Network "
    "Policies documentation covers the standard NetworkPolicy API that app teams will author. The companion "
    "document, Kubernetes Environment Access Policies, covers the broader governance framework including RBAC, "
    "admission control, GitOps, and audit that surrounds the network policy process described in this deck."])

FIG = {262: "net-advisory-tier-evaluation", 266: "net-advisory-ci-pipeline", 268: "net-advisory-team-ownership"}


def main():
    ops = []
    for sid in sorted(S):
        s = S[sid]
        if s.get("eyebrow"):
            ops.append({"op": "set_text", "sldId": sid, "shape_id": 2, "paragraphs": [s["eyebrow"]], "cat": "stack"})
        if s.get("title"):
            t = s["title"] if isinstance(s["title"], list) else [s["title"]]
            ops.append({"op": "set_text", "sldId": sid, "shape_id": 3, "paragraphs": t, "cat": "stack"})
        if s.get("body"):
            ops.append({"op": "set_text", "sldId": sid, "shape_id": 4, "paragraphs": s["body"], "cat": "stack"})
        if s.get("caption"):
            ops.append({"op": "set_text", "sldId": sid, "shape_id": s.get("caption_shape", 5),
                        "paragraphs": [s["caption"]], "cat": "stack"})
        if s.get("notes"):
            ops.append({"op": "set_notes", "sldId": sid, "paragraphs": s["notes"], "cat": "stack"})
        if sid in FIG:
            ops.append({"op": "replace_picture", "sldId": sid, "shape_id": 5, "png": P + FIG[sid] + ".png",
                        "cat": "stack", "_why": "vendor-neutral labels (tools/vendor_figures.py)"})
    for o in ops:
        o["_vendor"] = "S12 decision 7"
    OUT.write_text(json.dumps({"ops": ops}, indent=1, ensure_ascii=False) + "\n")
    print(len(ops))


if __name__ == "__main__":
    main()
