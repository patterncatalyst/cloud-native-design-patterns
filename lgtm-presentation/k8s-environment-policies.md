# Kubernetes Environment Access Policies — Dev · Test · Prod

Governance, RBAC, NetworkPolicy, and GitOps guardrails for multi-environment
Kubernetes clusters.

---

## 1. The problem

Every team running Kubernetes eventually faces the same question: **who can do what,
in which environment?** Without clear governance:

- A developer's experimental `kubectl delete namespace` in the wrong context wipes
  production.
- Network policies that were never tested allow lateral movement after a breach.
- Audit asks "who changed the firewall rules last Tuesday?" and nobody can answer.
- Configuration drift between environments means staging never catches what breaks
  in prod.

The cost of ungoverned access is measured in outages, security incidents, and audit
failures. The fix is a layered policy model — RBAC, NetworkPolicy, admission control,
and GitOps — applied differently per environment.

---

## 2. Three environments, three risk profiles

Each environment serves a different purpose and demands a different level of control:

| Dimension | Dev | Test / Staging | Production |
|-----------|-----|----------------|------------|
| **Purpose** | Experiment, iterate, break things | Validate before promotion | Serve real users |
| **Change velocity** | High — deploy on every commit | Moderate — deploy on PR merge | Low — deploy on release |
| **Access model** | Self-service within namespace | CI-driven deploy, read-only manual | Read-only, all changes via GitOps |
| **Blast radius** | One developer's sandbox | Shared validation environment | Revenue, reputation, compliance |
| **Network policy** | Permissive within namespace | Match production topology | Strict micro-segmentation |
| **Who applies changes** | Developer directly | CI/CD pipeline | Platform / SRE team via ArgoCD/Flux |

The principle: **freedom increases as risk decreases.** Dev is the most permissive,
prod is the most restrictive, and test mirrors prod's topology so that what passes
test also passes prod.

---

## 3. RBAC: the Kubernetes gate

Kubernetes Role-Based Access Control (RBAC) is the primary mechanism for controlling
who can perform which actions on which resources. It has four objects:

- **Role** — a set of permissions (verbs on resources) scoped to a single namespace.
- **ClusterRole** — the same, but cluster-wide (or reusable across namespaces via
  RoleBindings).
- **RoleBinding** — grants a Role to a user, group, or service account in a namespace.
- **ClusterRoleBinding** — grants a ClusterRole cluster-wide.

The key verbs: `get`, `list`, `watch` (read-only) versus `create`, `update`, `patch`,
`delete` (write). The governance question is which verbs each persona gets in each
environment.

**Industry reference:** [Kubernetes RBAC Good Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)
recommends least privilege, no cluster-admin for humans, namespace-scoped roles over
cluster roles, service accounts with minimal permissions, audit logging of all RBAC
decisions, and quarterly review of bindings to remove stale access.

---

## 4. Environment-specific RBAC matrix

| Resource | Dev | Test / Staging | Production |
|----------|-----|----------------|------------|
| Pods, Deployments, Services | `*` (full CRUD) | `get, list, watch` | `get, list, watch` |
| ConfigMaps, Secrets | `*` | `get, list, watch` | `get, list` (no watch on Secrets) |
| NetworkPolicies | `*` | `get, list, watch` | `get, list, watch` |
| Namespaces | `get, list` | `get, list` | `get, list` |
| RBAC (Roles, Bindings) | `get, list` | `get, list` | `get, list` |
| CRDs (VirtualService, etc.) | `*` | `get, list, watch` | `get, list, watch` |

**Dev** — full self-service within assigned namespaces. Developers can create, modify,
and delete any workload or network policy. They learn by doing.

**Test / Staging** — developers can read everything but deploy only through the CI/CD
pipeline. Manual `kubectl apply` is blocked by admission control.

**Production** — strictly read-only for all humans. Every change flows through a
GitOps pipeline (ArgoCD or Flux) after passing automated validation.

**Practical tip:** you do not need to write custom Roles. Kubernetes ships built-in
ClusterRoles named `edit` (create, update, delete on most resources) and `view`
(get, list, watch only). Bind them via **RoleBinding** (namespace-scoped), not
ClusterRoleBinding, to keep permissions scoped to the team's namespace.

```yaml
# Dev namespace — developer gets full access
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-full-access
  namespace: order-dev
subjects:
  - kind: Group
    name: order-team-devs
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: edit                       # built-in: create, update, delete on most resources
  apiGroup: rbac.authorization.k8s.io
---
# Prod namespace — developer gets read-only
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: prod-read-only
  namespace: order-prod
subjects:
  - kind: Group
    name: order-team-devs
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: view                       # built-in: get, list, watch only
  apiGroup: rbac.authorization.k8s.io
```

---

## 5. Default-deny NetworkPolicy

Zero-trust networking starts with a **default-deny** rule in every namespace. With no
NetworkPolicy, Kubernetes allows all traffic — any pod can reach any other pod in the
cluster. A single default-deny policy flips that to "nothing is allowed unless
explicitly permitted."

```yaml
# Default deny all ingress and egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: order-prod
spec:
  podSelector: {}        # matches every pod in the namespace
  policyTypes:
    - Ingress
    - Egress
```

After this baseline, developers write targeted policies to open only the connections
their services need — port 5432 to the database, port 9092 to Kafka, port 8080
between specific services. Everything else is blocked.

This is the single highest-impact security measure you can apply to a Kubernetes
namespace. Without it, a compromised pod can scan and reach every service in the
cluster. With it, a compromise is contained to the traffic the service was already
authorized to send. Apply default-deny on day one of every new namespace, in every
environment.

---

## 6. NetworkPolicy by environment

The same default-deny baseline applies everywhere, but the **allow rules** differ by
environment:

**Dev** — permissive within the namespace. Allow all intra-namespace traffic so
developers can wire up services without filing tickets. Block cross-namespace traffic
to prevent accidental dependencies on other teams' dev environments.

**Test / Staging** — mirror production's network topology exactly. If production only
allows order → inventory on port 8080, test should enforce the same rule. This catches
misconfigurations before they reach prod.

**Production** — strict micro-segmentation. Each service-to-service connection is
explicitly allowed by label selector, port, and protocol. Egress to external services
is allow-listed by CIDR or DNS. Everything else is denied.

```yaml
# Prod: only order-service can reach inventory on port 8080
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-order-to-inventory
  namespace: order-prod
spec:
  podSelector:
    matchLabels: { app: inventory }
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: { app: order-service }
      ports:
        - protocol: TCP
          port: 8080
```

---

## 7. Policy-as-code with OPA Gatekeeper

RBAC controls who can act; **admission control** controls what they can create.
OPA Gatekeeper (or Kyverno) evaluates every object submitted to the API server
against a set of policies written as code:

- **Images must come from a trusted registry** — block `docker.io/random:latest`.
- **No privileged containers** — reject `securityContext.privileged: true`.
- **Resource limits required** — every container must declare CPU and memory limits.
- **Namespace labels required** — every namespace must carry `env: dev|test|prod`
  and `team: <team-name>` labels for policy scoping.

The same policies run in two places: in CI (via `conftest`) *before* merge, and at
admission *on the cluster*. A violation caught in CI is a PR comment; the same
violation at admission is a hard reject.

```yaml
# OPA Gatekeeper ConstraintTemplate — require trusted registry
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata: { name: k8srequiretrustedregistry }
spec:
  crd:
    spec:
      names: { kind: K8sRequireTrustedRegistry }
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiretrustedregistry
        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not startswith(container.image, "registry.access.redhat.com/")
          not startswith(container.image, "registry.internal/")
          msg := sprintf("image %v is not from a trusted registry", [container.image])
        }
```

---

## 8. GitOps-gated production changes

In production, no human runs `kubectl apply`. Every change follows a GitOps pipeline:

1. **Developer opens a PR** against the environment repo (or a `kustomize` overlay
   for the prod branch).
2. **CI validates** — `kubeval` checks schema, `conftest` runs OPA policies, a
   staging deployment proves the change doesn't break.
3. **Peer review + approval** — at least one reviewer from the platform or SRE team.
4. **Merge triggers deployment** — ArgoCD or Flux detects the merge, syncs the
   cluster state to match Git.
5. **Drift detection** — if someone manually changes the cluster, ArgoCD detects the
   drift and either alerts or auto-reverts.

This gives you a complete audit trail (Git history), separation of duties (developer
proposes, SRE approves), and reproducibility (any cluster state can be rebuilt from
Git).

---

## 9. The four-layer L7 stack

Policy decisions happen at four layers, each with a distinct scope:

| Layer | Tool | Policy scope |
|-------|------|-------------|
| **Edge / Ingress** | Ingress controller, cloud LB | TLS termination, host-based routing, DDoS mitigation |
| **API Gateway** | Kong, Ambassador, Envoy Gateway | Authentication, rate limiting, API key validation |
| **Service Mesh** | Istio / Envoy sidecar | mTLS, AuthorizationPolicy, circuit breaking, retry budgets |
| **In-app** | Application code, rule engines | Business rules, feature flags, tenant isolation |

Each layer adds capability but also latency (~1-3ms per L7 hop). Place policies at
the **lowest layer** that has the information needed to decide. TLS at the edge,
auth at the gateway, service identity at the mesh, business logic in the app.

*Diagram: 22-l7-layers — the four-layer L7 stack*

---

## 10. Istio AuthorizationPolicy

Inside the mesh, Istio's `AuthorizationPolicy` provides **namespace-scoped,
identity-based access control**. Every workload gets a SPIFFE identity
(`cluster.local/ns/<namespace>/sa/<service-account>`), and policies control which
identities can call which endpoints:

```yaml
# Only order-service in the orders namespace can POST to /reserve
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: inventory-allow-order
  namespace: inventory
spec:
  selector:
    matchLabels: { app: inventory }
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/orders/sa/order-service"]
      to:
        - operation:
            methods: ["POST"]
            paths: ["/reserve"]
```

This is **zero-trust at the service level**: even if a pod is compromised, it can
only call the exact endpoints its identity is authorized for. Combined with mTLS
(which the mesh enables by default), every service-to-service call is authenticated
with cryptographic identity, encrypted in transit, and authorized against a declared
policy. The application code does not need to implement any of this — the mesh
enforces it transparently via the sidecar proxy.

---

## 11. Traffic steering for safe rollouts

L7 routing enables environment-safe deployments without modifying RBAC or network
policies:

- **Canary** — route 5% of traffic to the new version, monitor error rates, gradually
  increase. Rollback = set weight to 0.
- **Blue/Green** — two identical environments; switch traffic atomically by updating
  the VirtualService.
- **Header-based dark launch** — route requests with `x-canary: true` to the new
  version. Only opted-in developers or QA see it. Production users are unaffected.
- **Shadow / mirror** — duplicate production traffic to a test deployment without
  affecting responses. Validate behavior under real load with zero risk.

```yaml
# Istio VirtualService — canary with 5% traffic split
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: order-service, namespace: orders }
spec:
  hosts: [order-service]
  http:
    - route:
        - destination:
            host: order-service
            subset: stable
          weight: 95
        - destination:
            host: order-service
            subset: canary
          weight: 5
```

*Diagram: 22-traffic-steering — six release shapes*

---

## 12. Namespace isolation architecture

A well-governed namespace is a **blast-radius boundary** with four controls stacked:

- **RBAC** — who can act in this namespace (RoleBindings).
- **NetworkPolicy** — what traffic can enter and leave (default-deny + allow rules).
- **ResourceQuota** — how much CPU, memory, and storage the namespace can consume.
- **LimitRange** — default and maximum resource limits for individual containers.

Together, these prevent one team's namespace from consuming cluster resources,
accessing another team's data, or receiving traffic it shouldn't.

```yaml
# ResourceQuota — bound the namespace
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
  namespace: order-prod
spec:
  hard:
    requests.cpu: "8"
    requests.memory: 16Gi
    limits.cpu: "16"
    limits.memory: 32Gi
    pods: "50"
    services: "20"
```

---

## 13. CI/CD validation pipeline

Every policy change — NetworkPolicy, RBAC Role, OPA Constraint — flows through the
same validation pipeline before reaching any cluster:

| Stage | Tool | What it catches |
|-------|------|----------------|
| **Schema validation** | kubeval, kubeconform | Invalid YAML, unknown fields, wrong API versions |
| **Policy lint** | conftest, kyverno CLI | Violations of organizational policies (no privileged, trusted registry, etc.) |
| **Dry-run apply** | `kubectl apply --dry-run=server` | API server rejects (quota exceeded, admission denial) |
| **Staging deploy** | ArgoCD sync to staging | Runtime failures, misconfigured selectors, broken connectivity |
| **Smoke test** | curl, hey, newman | Service health, API contract, latency regression |
| **Approval gate** | GitHub PR review | Human sign-off from platform/SRE team |
| **Prod deploy** | ArgoCD sync to prod | Identical manifests, proven in staging |

The key principle: **the CI pipeline is the only path to production.** No exceptions,
no emergency `kubectl apply`, no "just this once." If the pipeline is too slow for
emergencies, fix the pipeline — don't bypass it. Every stage produces artifacts —
schema validation results, policy compliance reports, staging test results — that
feed the audit trail.

---

## 14. Audit & compliance

Kubernetes provides native audit logging, but governance requires more:

- **API server audit logs** — every `kubectl` command, every API call, with user
  identity, timestamp, resource, and verb. Configure at the `Metadata` or `Request`
  level for sensitive resources (Secrets, RBAC, NetworkPolicies).
- **OPA decision logs** — every admission decision (allow/deny) with the policy that
  matched and the object that triggered it.
- **Git history as audit trail** — with GitOps, every production change is a Git
  commit with author, reviewer, timestamp, and diff. This is the audit trail
  compliance teams want.
- **RBAC review cadence** — quarterly review of who has access to what. Remove stale
  bindings. Verify no human has cluster-admin.
- **Network policy coverage** — regularly scan for namespaces missing default-deny.
  Tools like `kubectl np-viewer` or Cilium's policy visualization help.

---

## 15. Anti-patterns to avoid

| Anti-pattern | Why it's dangerous | Fix |
|-------------|-------------------|-----|
| **cluster-admin for developers** | One typo deletes a namespace, one compromise owns the cluster | Use `edit` in dev, `view` in prod |
| **No default-deny** | Any pod can reach any pod — lateral movement is trivial | Apply default-deny in every namespace on day one |
| **Manual `kubectl apply` in prod** | No audit trail, no review, no rollback — "who changed this?" | GitOps pipeline with ArgoCD/Flux |
| **Shared namespaces across teams** | No blast-radius boundary — one team's quota spike starves another | One namespace per team per environment |
| **Test doesn't mirror prod** | NetworkPolicies that work in test fail in prod because the topology differs | Same policies, same selectors, same deny baseline |
| **No resource quotas** | One runaway deployment consumes all cluster memory | ResourceQuota + LimitRange in every namespace |

---

## 16. Summary & recommendations

**Checklist for environment governance:**

1. **Default-deny NetworkPolicy** in every namespace — the single highest-impact
   measure.
2. **Environment-tiered RBAC** — `edit` in dev, `view` in test and prod, with
   CI/CD as the only deploy path.
3. **Policy-as-code** — OPA Gatekeeper or Kyverno at admission, `conftest` in CI,
   same policies in both.
4. **GitOps for production** — ArgoCD or Flux, no manual `kubectl apply`, drift
   detection enabled.
5. **Namespace isolation** — RBAC + NetworkPolicy + ResourceQuota + LimitRange per
   namespace per team.
6. **Audit everything** — API server audit logs, OPA decision logs, Git history as
   the source of truth.
7. **Test mirrors prod** — same network topology, same policies, same deny baseline.

The order matters: default-deny and RBAC tiering give you the most security for the
least effort, while GitOps and policy-as-code take more infrastructure investment but
close the remaining gaps. Start with the first two this week.

---

## 17. References

- [Kubernetes RBAC Good Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/)
- [Kyverno](https://kyverno.io/)
- [Istio AuthorizationPolicy](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
- [ArgoCD](https://argo-cd.readthedocs.io/) / [Flux](https://fluxcd.io/)
- [CNCF Cloud Native Security Whitepaper](https://github.com/cncf/tag-security/tree/main/security-whitepaper)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [SPIFFE / SPIRE](https://spiffe.io/)
