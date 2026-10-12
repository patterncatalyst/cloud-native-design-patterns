# K8s-Environment-Access-Policies

Source: K8s-Environment-Access-Policies.pptx · 18 slides

## [001] Kubernetes Environment Access Policies (sldId 256)

Dev · Test · Prod — RBAC, NetworkPolicy, and GitOps guardrails.

> Welcome the audience and set context. The subject is environment access governance for Kubernetes: the policies, guardrails, and automation that separate a cluster where developers can safely experiment from one where a single misconfigured kubectl command wipes production. We will walk through a layered model: RBAC for identity-based access, NetworkPolicy for traffic segmentation, OPA Gatekeeper for admission control, and GitOps for change management. The goal is a concrete, implementable framework that scales from a single dev namespace to a multi-team production fleet. By the end, the audience should understand not just what each layer does, but how they compose into a defense-in-depth posture across dev, test, and production environments. Ask the audience: how many of you have a documented policy for who can do what in your production Kubernetes cluster? The answer usually reveals the gap this deck fills.

## [002] THE PROBLEM · Why environment governance matters (sldId 257)

Every team running Kubernetes eventually faces the same question: who can do what, in which environment? Without clear governance, a developer's experimental kubectl delete namespace in the wrong context wipes production.

Network policies that were never tested allow lateral movement after a breach. Audit asks "who changed the firewall rules last Tuesday?" and nobody can answer.

Configuration drift between environments means staging never catches what breaks in prod. The cost of ungoverned access is measured in outages, security incidents, and audit failures.

The fix is a layered policy model (RBAC, NetworkPolicy, admission control, and GitOps) applied differently per environment.

The cost is measured in outages, security incidents, and failed audits.

p. 2

> Open with the cost of ungoverned access. Every team running Kubernetes hits the same pain points: a developer runs kubectl delete namespace in the wrong context and wipes production workloads. Network policies that were never tested allow lateral movement after a container is compromised. An auditor asks who changed the firewall rules last Tuesday and nobody can produce an answer. Configuration drift between environments means staging never catches what breaks in production. These are not hypothetical — they are incidents that happen in real organizations every quarter. The cost is measured in outages, security incidents, compliance failures, and engineering hours spent on incident response instead of building features. The fix is not one tool but a layered policy model (RBAC, NetworkPolicy, admission control, and GitOps) applied with increasing strictness from dev through test to production. Frame this as the motivation for everything that follows.

## [003] THREE ENVIRONMENTS · Risk profiles by environment (sldId 258)

Dev — freedom to experiment, iterate, break things. Full self-service within assigned namespaces. Deploy on every commit. Permissive networking.

Test / Staging — validate before promotion. CI-driven deploys, read-only manual access. Network topology mirrors production exactly.

Production — serve real users. Strictly read-only for humans. All changes via GitOps pipeline (ArgoCD/Flux). Strict micro-segmentation.

The principle: freedom increases as risk decreases. Dev is the most permissive, prod is the most restrictive, and test mirrors prod's topology so what passes test also passes prod.

Freedom ←→ Restriction: access decreases as environment risk increases.

p. 3

> Walk through the three environments as a risk gradient. Dev is where developers experiment, iterate, and break things — full self-service within their own namespace, deploy on every commit, permissive networking. The blast radius is one developer's sandbox. Test and staging exist to validate before promotion — CI-driven deploys, read-only manual access, and network topology that mirrors production exactly. If production only allows order-service to reach inventory on port 8080, test enforces the same rule. Production serves real users — strictly read-only for all humans, every change flows through a GitOps pipeline, strict micro-segmentation. The key principle is that freedom increases as risk decreases: dev is the most permissive, prod is the most restrictive, and test mirrors prod so what passes test also passes prod. Point to the diagram showing the three columns and stress that the RBAC verbs and deploy mechanisms differ by environment. This gradient drives every policy decision in the model.

## [004] RBAC · RBAC: the Kubernetes gate (sldId 259)

Kubernetes RBAC has four objects: Role (namespace-scoped permissions), ClusterRole (cluster-wide), RoleBinding (grants a Role to a user/group in a namespace), ClusterRoleBinding (grants cluster-wide).

Key verbs: get, list, watch (read-only) versus create, update, patch, delete (write). The governance question is which verbs each persona gets in each environment.

Industry best practice: least privilege, no cluster-admin for humans, audit logging of all RBAC decisions. Quarterly review of who has access to what. Remove stale bindings.

Reference: Kubernetes RBAC Good Practices (kubernetes.io) recommends namespace-scoped roles over cluster roles, and service accounts with minimal permissions.

kubernetes.io/docs/concepts/security/rbac-good-practices/

p. 4

> Introduce Kubernetes RBAC as the primary gate. There are four objects: Role (namespace-scoped permissions), ClusterRole (cluster-wide or reusable via RoleBinding), RoleBinding (grants a Role to a user, group, or service account in a namespace), and ClusterRoleBinding (grants cluster-wide). The critical distinction is the verbs: get, list, and watch are read-only; create, update, patch, and delete are write operations. The governance question is which verbs each persona gets in each environment. Industry best practice from the official Kubernetes RBAC Good Practices documentation recommends least privilege, no cluster-admin for human users, namespace-scoped roles over cluster roles, audit logging of all RBAC decisions, and quarterly review of bindings to remove stale access. RBAC is the foundation because it controls who can act, but it is not sufficient alone. You also need admission control to govern what they can create, and NetworkPolicy to govern what traffic can flow. The environment-specific RBAC matrix maps these verbs to each environment.

## [005] RBAC · MATRIX · Environment-specific RBAC matrix (sldId 260)

Dev: Pods/Deployments/Services = full CRUD. ConfigMaps/Secrets = full CRUD. NetworkPolicies = full CRUD. Developers own their namespace.

Test: All resources = get, list, watch only. Deploys happen via CI/CD pipeline. Manual kubectl apply is blocked by admission control.

Prod: All resources = get, list, watch only. No watch on Secrets. All changes flow through ArgoCD/Flux after automated validation and peer review.

Use the built-in ClusterRoles: "edit" for dev namespaces, "view" for test and prod. Bind via RoleBinding (namespace-scoped, not ClusterRoleBinding).

Built-in ClusterRoles: edit (dev), view (test/prod)

p. 5

> Walk the RBAC matrix column by column. In dev, developers get full CRUD on pods, deployments, services, ConfigMaps, Secrets, and NetworkPolicies within their own namespace — use the built-in ClusterRole 'edit' bound via a namespace-scoped RoleBinding. In test and staging, developers can read everything (get, list, watch) but deploys happen only through the CI/CD pipeline — manual kubectl apply is blocked by admission control. In production, everything is read-only for humans — use the built-in ClusterRole 'view'. No watch on Secrets in prod is an extra hardening step. All production changes flow through ArgoCD or Flux after automated validation and peer review. Stress the practical implementation: you do not need to write custom Roles — Kubernetes ships built-in ClusterRoles named 'edit' and 'view' that cover the common case. Bind them via RoleBinding, not ClusterRoleBinding, to keep permissions namespace-scoped. This is both simpler and more secure than crafting custom roles for each team.

## [006] NETWORKPOLICY · ZERO TRUST · Default-deny NetworkPolicy (sldId 261)

Zero-trust networking starts with a default-deny rule in every namespace. Without any NetworkPolicy, Kubernetes allows all traffic — any pod can reach any other pod in the cluster.

A single default-deny policy flips that to "nothing is allowed unless explicitly permitted." podSelector: {} matches every pod. policyTypes: [Ingress, Egress] denies both directions.

After the baseline, developers write targeted policies to open only necessary connections — port 5432 to the database, port 9092 to Kafka, port 8080 between specific services.

This is the single highest-impact security measure for a Kubernetes namespace. Without it, a compromised pod can scan and reach every service in the cluster.

The single highest-impact security measure you can apply to a Kubernetes namespace.

p. 6

> This is the single highest-impact security measure you can apply to a Kubernetes namespace. Without any NetworkPolicy, Kubernetes allows all traffic — any pod can reach any other pod in the entire cluster. A single default-deny policy flips that to nothing is allowed unless explicitly permitted. The YAML is simple: podSelector empty (matches every pod), policyTypes includes both Ingress and Egress. After this baseline, developers write targeted policies to open only the connections their services need — port 5432 to the database, port 9092 to Kafka, port 8080 between specific services. Everything else is blocked. Without default-deny, a compromised pod can scan and reach every service in the cluster — it is the network equivalent of leaving every door unlocked. With it, a compromise is contained to the traffic the service was already authorized to send. This should be applied on day one of every new namespace, in every environment. Ask the audience to check: how many of your production namespaces have default-deny today? The answer drives urgency.

## [007] NETWORKPOLICY · BY ENVIRONMENT · NetworkPolicy by environment (sldId 262)

Dev: permissive within the namespace. Allow all intra-namespace traffic. Block cross-namespace to prevent accidental dependencies.

Test / Staging: mirror production's network topology exactly. If prod only allows order → inventory on port 8080, test enforces the same rule.

Prod: strict micro-segmentation. Each service-to-service connection is explicitly allowed by label selector, port, and protocol. Egress to external services is allow-listed by CIDR or DNS.

Same default-deny baseline everywhere; the allow rules differ by environment.

p. 7

> The same default-deny baseline applies everywhere, but the allow rules differ by environment. In dev, allow all intra-namespace traffic so developers can wire up services without filing tickets — but block cross-namespace traffic to prevent accidental dependencies on other teams' environments. In test and staging, mirror production's network topology exactly. If production only allows order-service to reach inventory on port 8080, test should enforce the same rule — this catches misconfigurations before they reach prod. In production, enforce strict micro-segmentation: each service-to-service connection is explicitly allowed by label selector, port, and protocol, and egress to external services is allow-listed by CIDR or DNS. Point to the diagram showing the namespace boundary with RBAC, NetworkPolicy, ResourceQuota, and LimitRange stacked as four controls. The cross-namespace traffic at the bottom is denied by default — that is the blast-radius boundary in action.

## [008] ADMISSION CONTROL · Policy-as-code with OPA Gatekeeper (sldId 263)

RBAC controls who can act; admission control controls what they can create. OPA Gatekeeper evaluates every object against policies written as code.

Common policies: images must come from a trusted registry, no privileged containers, resource limits required, namespace labels required (env, team).

Same policies run in two places: in CI (conftest) before merge, and at admission on the cluster. Violation in CI = PR comment. Violation at admission = hard reject.

Alternative: Kyverno — Kubernetes-native policies in YAML instead of Rego. Same dual-enforcement model (CI + admission).

Policy lives in Git and is enforced at admission; no human runs a checklist.

p. 8

> RBAC controls who can act; admission control controls what they can create. OPA Gatekeeper evaluates every object submitted to the Kubernetes API server against policies written as code in Rego. Common policies include: images must come from a trusted registry (block docker.io/random:latest), no privileged containers, resource limits required on every container, and namespace labels required for policy scoping. The key architectural point is dual enforcement: the same policies run in CI via conftest before merge, and at admission on the cluster via Gatekeeper. A violation caught in CI is a PR comment the developer fixes before merge. The same violation at admission is a hard reject — the object is never created. This means policy is code, lives in Git, is reviewed like code, and is enforced automatically. No human runs a checklist. Mention Kyverno as an alternative that uses Kubernetes-native YAML instead of Rego — same dual-enforcement model, different policy language. Point to the diagram showing the flow from developer through Git/CI to the admission controller.

## [009] GITOPS · GitOps-gated production changes (sldId 264)

In production, no human runs kubectl apply. Every change follows a GitOps pipeline: Developer opens PR → CI validates (kubeconform, conftest) → staging deploy + test → peer review → merge triggers ArgoCD/Flux sync.

Benefits: complete audit trail (Git history), separation of duties (developer proposes, SRE approves), reproducibility (any cluster state rebuilt from Git).

Drift detection: if someone manually changes the cluster, ArgoCD detects the drift and either alerts or auto-reverts to the Git-declared state.

The only path to production is a merged PR — no exceptions, no bypass.

p. 9

> In production, no human runs kubectl apply. Every change follows a GitOps pipeline: the developer opens a PR against the environment repo or a kustomize overlay for the prod branch. CI validates: kubeconform v0.8.0 checks the manifests against the Kubernetes and CRD schemas, conftest runs OPA policies, and a staging deployment proves the change does not break. A peer reviewer from the platform or SRE team approves. The merge triggers ArgoCD or Flux to sync the cluster state to match Git. If someone manually changes the cluster, ArgoCD detects the drift and either alerts or auto-reverts to the Git-declared state. This gives you three things compliance teams care about: a complete audit trail in Git history, separation of duties where the developer proposes and the SRE approves, and reproducibility where any cluster state can be rebuilt from Git. Point to the diagram showing the pipeline from developer through Git repo, CI lint, staging, approval, ArgoCD, and finally the production cluster with drift detection looping back. Stress: the only path to production is a merged PR. No exceptions, no bypass.

## [010] L7 ROUTING · POLICY LAYERS · The four-layer L7 stack (sldId 265)

Edge / Ingress: TLS termination, host-based routing, DDoS mitigation. Tools: Ingress controller, cloud load balancer.

API Gateway: authentication, rate limiting, API key validation. Tools: Kong, Ambassador, Envoy Gateway.

Service Mesh: mTLS, AuthorizationPolicy, circuit breaking, retry budgets. Tools: Istio / Envoy sidecar.

In-app: business rules, feature flags, tenant isolation. Place policies at the lowest layer that has the information needed to decide.

Each layer adds capability but also latency (~1-3ms per L7 hop).

p. 10

> Policy decisions in a cloud-native architecture happen at four layers, each with a distinct scope and toolset. At the edge and ingress layer, the ingress controller or cloud load balancer handles TLS termination, host-based routing, and DDoS mitigation. The API gateway layer (Kong, Ambassador, Envoy Gateway) handles authentication, rate limiting, and API key validation. The service mesh layer (Istio with Envoy sidecars) provides mTLS encryption, AuthorizationPolicy for identity-based access control, circuit breaking, and retry budgets. The in-app layer handles business rules, feature flags, and tenant isolation. Each layer adds capability but also latency — roughly one to three milliseconds per L7 hop. The governance principle is to place policies at the lowest layer that has the information needed to decide. TLS belongs at the edge, authentication at the gateway, service identity at the mesh, and business logic in the application. Point to the diagram showing the north-south and east-west request paths. The mesh is the same L7 routing applied to every internal call, not just at the edge.

## [011] ISTIO · ZERO TRUST · Istio AuthorizationPolicy (sldId 266)

Inside the mesh, every workload gets a SPIFFE identity: cluster.local/ns/<namespace>/sa/<service-account>. Istio AuthorizationPolicy controls which identities can call which endpoints.

Example: only order-service in the orders namespace can POST to /reserve on inventory. Even if a pod is compromised, it can only call the exact endpoints its identity is authorized for.

Combined with mTLS (enabled by default in the mesh), every service-to-service call is authenticated, encrypted, and authorized.

This is zero-trust at the service level — the mesh enforces it without application code changes.

Zero-trust at the service level: even compromised pods are contained.

p. 11

> Inside the service mesh, Istio AuthorizationPolicy provides namespace-scoped, identity-based access control. Every workload gets a SPIFFE identity in the form cluster.local/ns/namespace/sa/service-account, and policies control which identities can call which endpoints. The example on the slide shows that only order-service in the orders namespace can POST to the /reserve endpoint on inventory — no other service, no other method, no other path is allowed. This is zero-trust at the service level: even if a pod is compromised, it can only call the exact endpoints its identity is authorized for. Combined with mTLS, which the mesh enables by default, every service-to-service call is authenticated with cryptographic identity, encrypted in transit, and authorized against a declared policy. The application code does not need to implement any of this — the mesh enforces it transparently via the sidecar proxy. In production this guarantees that services communicate only along defined paths, regardless of what the application code attempts.

## [012] L7 ROUTING · SAFE ROLLOUTS · Traffic steering for safe rollouts (sldId 267)

Canary: route 5% of traffic to the new version, monitor error rates, gradually increase. Rollback = set weight to 0.

Blue/Green: two identical environments; switch traffic atomically by updating the VirtualService.

Header-based dark launch: route requests with x-canary: true to the new version. Only opted-in developers or QA see it. Production users are unaffected.

Shadow/mirror: duplicate production traffic to a test deployment without affecting responses. Validate behavior under real load with zero risk.

L7 routing enables environment-safe deployments without modifying RBAC or network policies.

p. 12

> L7 routing enables environment-safe deployments without modifying RBAC or network policies. Walk through four patterns: Canary deploys route a small percentage of traffic, say five percent, to the new version while monitoring error rates — rollback is just setting the weight to zero. Blue/green maintains two identical environments and switches traffic atomically by updating the VirtualService. Header-based dark launches route only requests with a specific header like x-canary: true to the new version — only opted-in developers or QA see it, production users are unaffected. Shadow or mirror mode duplicates production traffic to a test deployment without affecting responses, letting you validate behavior under real load with zero risk. Point to the diagram showing the six release shapes: canary, blue/green, A/B test, header-based, geo/latency, and shadow. Stress that each pattern is a header or weight rule away — the value is in the deploy and rollback discipline around them, not the routing mechanism itself.

## [013] NAMESPACE ISOLATION · Namespace isolation architecture (sldId 268)

A well-governed namespace is a blast-radius boundary with four controls stacked: RBAC (who can act), NetworkPolicy (what traffic flows), ResourceQuota (how much the namespace consumes), LimitRange (per-container defaults).

Together, these prevent one team's namespace from consuming cluster resources, accessing another team's data, or receiving unauthorized traffic.

ResourceQuota bounds the namespace: max CPU, memory, pod count, service count. LimitRange sets defaults so no single container can claim unbounded resources.

Four controls stack to make each namespace a blast-radius boundary.

p. 13

> A well-governed namespace is a blast-radius boundary with four controls stacked. RBAC determines who can act in this namespace via RoleBindings — view-only in production, edit in development. NetworkPolicy determines what traffic can enter and leave — default-deny plus explicit allow rules. ResourceQuota bounds how much CPU, memory, storage, and how many pods and services the namespace can consume — preventing one team from starving the cluster. LimitRange sets default and maximum resource limits for individual containers — so no single container can claim unbounded resources even if the developer forgets to set limits. Together, these four controls prevent one team's namespace from consuming cluster resources, accessing another team's data, or receiving traffic it should not. Point to the diagram showing these four controls at the top of the namespace boundary, with services communicating via allowed paths inside and cross-namespace traffic denied at the bottom. This is the architecture every production namespace should have from day one.

## [014] CI/CD PIPELINE · CI/CD validation pipeline (sldId 269)

Every policy change flows through: Schema validation (kubeconform) → Policy lint (conftest/kyverno) → Dry-run apply (kubectl --dry-run=server) → Staging deploy (ArgoCD sync) → Smoke test (curl/hey/newman) → Approval gate (PR review) → Prod deploy.

The key principle: the CI pipeline is the only path to production. No exceptions, no emergency kubectl apply, no "just this once." If the pipeline is too slow for emergencies, fix the pipeline.

Every stage produces artifacts: schema validation results, policy compliance reports, staging test results. These feed the audit trail.

Fail at any stage → PR blocked. No exceptions, no bypass.

p. 14

> Every policy change (NetworkPolicy, RBAC Role, OPA Constraint, ResourceQuota) flows through the same validation pipeline before reaching any cluster. Walk through the stages: schema validation with kubeconform v0.8.0 catches invalid YAML, unknown fields and wrong API versions, including custom resources through the CRDs-catalog schemas. Policy lint with conftest or the Kyverno CLI catches organizational policy violations like untrusted registries or missing resource limits. Dry-run apply with kubectl apply --dry-run=server catches API server rejections like quota exceeded or admission denial. Staging deploy via ArgoCD sync catches runtime failures, misconfigured selectors, and broken connectivity. Smoke tests with curl, hey, or newman verify service health, API contracts, and latency regression. An approval gate requires human sign-off from the platform or SRE team. Finally, prod deploy applies the identical manifests that were proven in staging. Point to the diagram showing the linear pipeline. The key principle: the CI pipeline is the only path to production. No exceptions, no emergency kubectl apply, no just this once. If the pipeline is too slow for emergencies, fix the pipeline — do not bypass it.

## [015] AUDIT & COMPLIANCE · Audit & compliance (sldId 270)

API server audit logs: every kubectl command, every API call, with user identity, timestamp, resource, and verb. Configure at Metadata or Request level for sensitive resources.

OPA decision logs: every admission decision (allow/deny) with the policy that matched and the object that triggered it.

Git history as audit trail: with GitOps, every production change is a Git commit with author, reviewer, timestamp, and diff. This is the audit trail compliance teams want.

RBAC review cadence: quarterly review of who has access. Remove stale bindings. Verify no human has cluster-admin. Scan for namespaces missing default-deny.

Git history + audit logs + OPA decision logs = complete compliance trail.

p. 15

> Governance requires more than access control — it requires proof that the controls are working. Walk through four audit dimensions. API server audit logs capture every kubectl command and API call with user identity, timestamp, resource, and verb — configure at the Metadata or Request level for sensitive resources like Secrets, RBAC objects, and NetworkPolicies. OPA decision logs record every admission decision, allow or deny, with the policy that matched and the object that triggered it. With GitOps, Git history becomes the audit trail: every production change is a Git commit with author, reviewer, timestamp, and diff — this is exactly what compliance teams want when they ask who changed what and when. Finally, establish a quarterly RBAC review cadence: review who has access to what, remove stale bindings, verify no human has cluster-admin, and scan for namespaces missing default-deny using tools like kubectl np-viewer or Cilium's policy visualization. The combination of API server logs, OPA decision logs, and Git history creates a complete compliance trail.

## [016] ANTI-PATTERNS · Anti-patterns to avoid (sldId 271)

cluster-admin for developers: one typo deletes a namespace, one compromise owns the cluster. Fix: use edit in dev, view in prod.

No default-deny: any pod can reach any pod — lateral movement is trivial. Fix: apply default-deny in every namespace on day one.

Manual kubectl apply in prod: no audit trail, no review, no rollback. Fix: GitOps pipeline with ArgoCD/Flux.

Shared namespaces across teams: no blast-radius boundary. Fix: one namespace per team per environment. No resource quotas: one runaway deployment consumes all cluster memory. Fix: ResourceQuota + LimitRange everywhere.

Each anti-pattern has a concrete, deployable fix.

p. 16

> Walk through each anti-pattern and its fix — these are drawn from real incidents, not hypothetical risks. Cluster-admin for developers: one typo deletes a namespace, one compromise owns the entire cluster. Fix: use the built-in edit role in dev and view in prod. No default-deny: any pod can reach any pod, lateral movement after a breach is trivial. Fix: apply default-deny in every namespace on day one. Manual kubectl apply in prod: no audit trail, no review, no rollback path — nobody can answer who changed this. Fix: GitOps pipeline with ArgoCD or Flux. Shared namespaces across teams: no blast-radius boundary, one team's quota spike starves another. Fix: one namespace per team per environment. Test that does not mirror prod: NetworkPolicies that pass in test fail in prod because the topology differs. Fix: same policies, same selectors, same deny baseline. No resource quotas: one runaway deployment consumes all cluster memory. Fix: ResourceQuota plus LimitRange in every namespace. Ask the audience which of these they recognize in their own clusters.

## [017] SUMMARY · Recommendations (sldId 272)

1. Default-deny NetworkPolicy in every namespace — the single highest-impact measure.
2. Environment-tiered RBAC — edit in dev, view in test and prod, CI/CD as the only deploy path.
3. Policy-as-code — OPA Gatekeeper or Kyverno at admission, conftest in CI, same policies in both.
4. GitOps for production — ArgoCD or Flux, no manual kubectl apply, drift detection enabled.
5. Namespace isolation — RBAC + NetworkPolicy + ResourceQuota + LimitRange per namespace.
6. Audit everything — API server audit logs, OPA decision logs, Git history as the source of truth.

p. 17

> Close with the priority-ordered checklist. First, apply default-deny NetworkPolicy in every namespace — it is the single highest-impact security measure and costs nothing to implement. Second, implement environment-tiered RBAC: edit in dev, view in test and prod, with CI/CD as the only deploy path. Third, adopt policy-as-code with OPA Gatekeeper or Kyverno at admission and conftest in CI, running the same policies in both places. Fourth, enforce GitOps for production — ArgoCD or Flux, no manual kubectl apply, drift detection enabled. Fifth, implement namespace isolation with RBAC plus NetworkPolicy plus ResourceQuota plus LimitRange per namespace per team. Sixth, audit everything — API server audit logs, OPA decision logs, and Git history as the source of truth. The order matters: default-deny and RBAC tiering give you the most security for the least effort, while GitOps and policy-as-code take more infrastructure investment but close the remaining gaps. Start with the first two this week.

## [018] REFERENCES · References (sldId 273)

Kubernetes RBAC Good Practices — kubernetes.io/docs/concepts/security/rbac-good-practices/

Kubernetes Network Policies — kubernetes.io/docs/concepts/services-networking/network-policies/

OPA Gatekeeper — open-policy-agent.github.io/gatekeeper/

Kyverno — kyverno.io

Istio AuthorizationPolicy — istio.io/latest/docs/reference/config/security/authorization-policy/

ArgoCD: argo-cd.readthedocs.io · Flux: fluxcd.io

CNCF Cloud Native Security Whitepaper — github.com/cncf/tag-security

Pod Security Standards — kubernetes.io/docs/concepts/security/pod-security-standards/

p. 18

> Point the audience to the authoritative sources for deeper reading. The Kubernetes RBAC Good Practices page is the official guidance on least privilege, namespace-scoped roles, and audit logging. The NetworkPolicy documentation covers the spec and includes worked examples. OPA Gatekeeper and Kyverno are the two leading admission controllers — both open source, both CNCF. The Istio AuthorizationPolicy reference is the specification for service-level zero-trust. ArgoCD and Flux are the two leading GitOps operators. The CNCF Cloud Native Security Whitepaper is the industry-consensus framework for cloud-native security posture, covering supply chain, runtime, and governance. Pod Security Standards define three levels (privileged, baseline, restricted) and replace PodSecurityPolicy, which was removed in Kubernetes 1.25. SPIFFE and SPIRE provide the workload identity framework that underpins mesh-based AuthorizationPolicy. Encourage the audience to start with the RBAC Good Practices and the CNCF whitepaper — together they cover most of what this deck presented.
