---
title: "Security"
order: 12
part: "Security & anti-patterns"
description: "Security as four concentric layers — cloud, cluster, container, code — and seven patterns that secure them, from the sidecar that reads trusted identity headers to policy-as-code enforced at admission."
duration: 30 minutes
---

Security isn't a feature you bolt on; it's a property of every layer, and the
cloud-native way to reason about it is the CNCF's **4 C's** — concentric layers,
each protecting what's inside it, so a breach of one is contained by the next.

## The 4 C's of cloud-native security

{% include excalidraw.html
   file="12-four-cs"
   alt="Four concentric layers: Cloud (IAM, VPC, KMS, audit) on the outside, then Cluster (RBAC, NetworkPolicy, Pod Security, admission), then Container (minimal image, non-root, read-only filesystem, signed), with Code (authz, input validation, secrets, dependencies) at the centre"
   caption="Figure 12.1 — Cloud → Cluster → Container → Code, each layer protecting the one inside" %}

- **Cloud** — the perimeter, identities, and keys: IAM with least privilege, VPC
  isolation, KMS, audit logging, data-residency. Owned by the platform/cloud team.
  Failures here look like "someone left a bucket open" or "an over-permissive role
  enabled lateral movement."
- **Cluster** — the Kubernetes layer: RBAC, `NetworkPolicy` (default-deny plus
  targeted allows), Pod Security Standards (restricted), admission control.
- **Container** — a minimal image, non-root, read-only root filesystem, and a
  *signed* image so only trusted artifacts run.
- **Code** — your application: authorization, input validation, secret handling,
  and keeping dependencies patched.

The value of the model is that controls live at the right layer with the right
owner, instead of every team trying to do everything in application code.

## Seven patterns to know

These span the 4 C's, and you'll meet several again in the appendices:

- **Sidecar** — move cross-cutting security (mTLS, JWT, audit, rate-limiting) into a
  companion process. *(Cluster/container layer.)*
- **Valet key** — hand the client a short-lived signed token for *direct* access to
  a resource, so your app stops proxying large payloads and sheds attack surface.
- **Strangler fig** — encapsulate legacy auth behind a gateway and replace it piece
  by piece. *(The modernisation pattern from Appendix K, applied to security.)*
- **Zero-trust / identity-aware proxy** — every request authenticated and
  authorised; perimeter trust is dead.
- **Policy-as-code** — security gates declared in Git, enforced at admission and in
  CI.
- **Bulkhead** — isolate resources (per-tenant pools) so one tenant's overload
  can't sink the rest. *(Returns in Appendix M.)*
- **Claim-check** — for large payloads, publish a *reference* and let the consumer
  fetch the body, keeping secrets and bulk out of the event stream.

## The sidecar reads trusted headers

The sidecar pattern is the one to internalise, because the mesh chapters already
put an Envoy sidecar in every pod. It terminates mTLS, validates JWTs, and enforces
policy — so the app receives only authenticated, authorised requests and reads the
identity as **plain, trusted headers**. Two rules: the app must **reject** any
request missing the sidecar-set identity, and it must **never re-validate** the JWT
signature — the sidecar already did, and re-doing it duplicates trust and drifts.

{% include excalidraw.html
   file="12-sidecar"
   alt="Clients reach a Kubernetes pod whose app container holds business logic only — no TLS, auth, rate-limit, or audit code — talking over localhost to an Envoy/OPA sidecar that terminates mTLS, validates JWTs, rate-limits, audits, enforces policy, and emits metrics and traces before egress. The app trusts the sidecar's headers."
   caption="Figure 12.2 — Security concerns move out of the app and into an Envoy/OPA sidecar in the same pod" %}

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// Istio sidecar already did mTLS + JWT validation. Trust its headers;
// reject anything arriving without the validated client identity.
@Component
public class IdentityFilter extends OncePerRequestFilter {
    @Override protected void doFilterInternal(HttpServletRequest req,
            HttpServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        String spiffe = req.getHeader("X-Forwarded-Client-Cert");  // sidecar-set only
        if (spiffe == null) { res.sendError(403); return; }        // no identity → deny
        String subject = req.getHeader("X-Jwt-Claim-Sub");         // claims, pre-validated
        chain.doFilter(req, res);                                  // never re-validate sig
    }
}
```

```java
// Trust the sidecar's headers; the app never re-validates the JWT signature.
@Provider
public class IdentityFilter implements ContainerRequestFilter {
    public void filter(ContainerRequestContext ctx) {
        String spiffe = ctx.getHeaderString("X-Forwarded-Client-Cert");  // sidecar-set
        if (spiffe == null) {
            ctx.abortWith(Response.status(403).build()); return;         // no id → deny
        }
        String subject = ctx.getHeaderString("X-Jwt-Claim-Sub");         // pre-validated
    }
}
```

```csharp
// Middleware: trust the sidecar-attached identity; reject requests without it.
app.Use(async (ctx, next) =>
{
    // X-Forwarded-Client-Cert is set ONLY by the Istio sidecar after mTLS
    if (!ctx.Request.Headers.TryGetValue("X-Forwarded-Client-Cert", out var spiffe))
    {
        ctx.Response.StatusCode = 403;        // no validated identity → deny
        return;
    }
    var subject = ctx.Request.Headers["X-Jwt-Claim-Sub"];   // claims, already validated
    await next();                              // never re-validate the signature
});
```

```python
from fastapi import Request, HTTPException

@app.middleware("http")
async def trust_sidecar(request: Request, call_next):
    # set ONLY by the Istio sidecar after mTLS — the app never sees raw certs
    spiffe = request.headers.get("x-forwarded-client-cert")
    if spiffe is None:
        raise HTTPException(status_code=403)            # no validated identity → deny
    subject = request.headers.get("x-jwt-claim-sub")    # claims, pre-validated upstream
    return await call_next(request)                     # do NOT re-validate the signature
```

```cpp
// Drogon filter: trust the sidecar's headers; reject requests lacking the cert.
class TrustSidecar : public drogon::HttpFilter<TrustSidecar> {
 public:
  void doFilter(const HttpRequestPtr& req, FilterCallback&& fail,
                FilterChainCallback&& next) override {
    auto spiffe = req->getHeader("x-forwarded-client-cert");  // sidecar-set, post-mTLS
    if (spiffe.empty()) {                                     // no identity → deny
      auto r = HttpResponse::newHttpResponse();
      r->setStatusCode(k403Forbidden); fail(r); return;
    }
    auto subject = req->getHeader("x-jwt-claim-sub");         // claims, pre-validated
    next();                                                   // never re-validate sig
  }
};
```

```go
// trustSidecar — trust the headers the Istio sidecar sets after mTLS; never re-validate
func trustSidecar(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// set ONLY by the sidecar after mTLS — the app never sees raw certs
		if r.Header.Get("X-Forwarded-Client-Cert") == "" {
			http.Error(w, "no validated identity", http.StatusForbidden) // deny
			return
		}
		_ = r.Header.Get("X-Jwt-Claim-Sub") // claims, pre-validated upstream
		next.ServeHTTP(w, r)                // do NOT re-validate the signature
	})
}
```

The `X-Forwarded-Client-Cert` carries the validated caller identity from mTLS —
typically a SPIFFE id like `spiffe://cluster.local/ns/orders/sa/order-service`. The
app reads it as a value; it does no certificate work itself. Every tab is the same
two moves: deny if the identity header is absent, and trust (never re-check) the
claims the sidecar forwarded.

## The valet key hands out direct access

When a client needs a *large* resource — upload an attachment, download an export —
proxying those bytes through your service is wasted work and extra attack surface. The
**valet key** pattern hands the client a short-lived, scoped, signed token and lets it
talk to the storage system directly.

{% include excalidraw.html
   file="12-valet-key"
   alt="A client requests a key from the application, which mints a scoped, time-bound, operation-restricted valet key and returns a signed token. The client then PUTs or GETs directly against the resource (S3, blob, file) using the token; the storage/KMS layer validates the token, permits the named operation, and rejects everything else. The app never proxies the bytes."
   caption="Figure 12.3 — The app mints a scoped, time-bound token; the client accesses storage directly and the app never proxies the bytes" %}

The application mints a key that is *scoped* (this one object), *time-bound* (minutes,
not forever), and *operation-restricted* (PUT or GET, not both). The client uses it to
reach the resource directly; the storage system validates the token, permits exactly
the named operation, and rejects everything else. No long-lived credential ever lands
on the client, and your service is out of the data path:

```python
import boto3
from datetime import timedelta

s3 = boto3.client("s3")

def upload_ticket(bucket: str, key: str) -> str:
    # a valet key: this object, PUT only, expires in 5 minutes
    return s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=int(timedelta(minutes=5).total_seconds()),
    )
# the client PUTs straight to S3 with the returned URL; the app never sees the bytes
```

The same shape covers Azure SAS tokens, GCS signed URLs, and AWS STS scoped roles.

## Zero-trust: every request proves itself

The old perimeter model — VPN in, then trust everything on the intranet — fails the
moment one host is compromised: the attacker is *inside*, and lateral movement is
trivial. **Zero-trust** discards the perimeter. Every request, even service-to-service
inside the cluster, must carry a verifiable identity and pass policy on *every* hop.

{% include excalidraw.html
   file="12-zero-trust"
   alt="Top: the old perimeter model — VPN to a trusted intranet to any service — where getting in once means trusted forever and lateral movement is trivial. Bottom: the zero-trust model — user/device to an IAP/auth proxy (who, where, device, MFA, posture) to a policy engine making a per-request decision (OPA/Cedar) to a service that accepts only requests carrying a valid claim, repeated for every downstream call, with mTLS and SPIFFE identity inside the cluster."
   caption="Figure 12.4 — Perimeter trust versus zero-trust: identity and policy are checked on every hop, not once at the edge" %}

In our stack this is layered: an identity-aware proxy at the edge checks who and what
(user, device, MFA, posture), and inside the cluster every workload has a SPIFFE
identity over mTLS, with an Istio `AuthorizationPolicy` deciding per call. A breach of
one service buys the attacker nothing, because the next call still has to prove itself:

```yaml
# Istio AuthorizationPolicy — only order-service may call inventory, only POST
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata: { name: inventory-allow-order, namespace: inventory }
spec:
  selector: { matchLabels: { app: inventory } }
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/orders/sa/order-service"]   # SPIFFE id
      to:
        - operation: { methods: ["POST"], paths: ["/reserve"] }
```

## Policy-as-code

The other pattern worth showing in code is **policy-as-code**: security rules
declared in Git, enforced the same way at two points — `conftest`/Kyverno in CI
*pre-merge*, and OPA Gatekeeper or Kyverno at *admission* on the cluster. The same
policy catches a violation before merge and blocks it again if it somehow reaches
`kubectl apply`.

{% include excalidraw.html
   file="12-policy-as-code"
   alt="A developer commits to Git/CI (conftest, kyverno, pre-merge gate), then kubectl apply (or ArgoCD/Flux) sends objects to an admission controller (OPA Gatekeeper/Kyverno) that evaluates ConstraintTemplates against incoming objects and the API server accepts or rejects based on policy. Policy in Rego or Kyverno YAML — images must be signed, no privileged containers — is loaded into the admission controller."
   caption="Figure 12.5 — Policy lives in Git and is enforced at admission; no human runs a checklist" %}

```yaml
# OPA Gatekeeper ConstraintTemplate — reusable policy logic in Rego
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata: { name: k8srequiresignedimages }
spec:
  crd:
    spec:
      names: { kind: K8sRequireSignedImages }
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiresignedimages
        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not startswith(container.image, "registry.internal/")   # only signed registry
          msg := sprintf("image %v is not from a trusted registry", [container.image])
        }
```

## Bulkhead: bound the blast radius

Borrowed from ship design — watertight compartments stop one breach from sinking the
whole hull. In a service, the **bulkhead** isolates resources so one tenant's overload
can't starve the others. Share one connection pool and one thread group across every
tenant and a single client's storm drains the pool for everyone; give each tenant its
own bounded pool and the storm is contained to that tenant.

{% include excalidraw.html
   file="12-bulkhead"
   alt="Without bulkheads, a shared pool and shared thread group serve customer A traffic, customer B traffic, background jobs, and scheduled work together, so one client's storm starves everyone. With bulkheads, customer A, customer B, and background each get their own bounded connection pool and thread group, so A's storm fails only A while B and background keep working and the blast radius is bounded."
   caption="Figure 12.6 — Per-tenant pools bound the blast radius: one tenant's storm fails only that tenant" %}

The implementation is a bounded resource per partition — a per-tenant connection pool,
a per-call thread group, or a semaphore that caps concurrency:

```python
import asyncio

# one bounded compartment per tenant; A's storm can't drain B's capacity
_sems: dict[str, asyncio.Semaphore] = {}

def _tenant_sem(tenant: str) -> asyncio.Semaphore:
    return _sems.setdefault(tenant, asyncio.Semaphore(20))   # 20 concurrent / tenant

async def handle(tenant: str, work):
    async with _tenant_sem(tenant):        # blocks only this tenant when full
        return await work()
```

Frameworks ship this directly — Resilience4j and Polly bulkheads, or Istio
per-destination connection-pool limits at the mesh.

## Claim-check: send a reference, not the payload

When a message is large *or* sensitive, putting it on the topic is wrong twice: it
bloats the broker, and the payload then lives in topic retention where it can leak. The
**claim-check** pattern publishes only a *reference* — a URI plus a signed token — and
stores the body in an encrypted object store the consumer fetches directly.

{% include excalidraw.html
   file="12-claim-check"
   alt="A producer PUTs a large or sensitive payload to an encrypted object store/vault (ACLs per object, retention policy) and publishes only a small, routable claim (a URI plus signed token) to the Kafka message bus, which holds only the token with no PII in topic history. A consumer consumes the claim and then fetches the payload directly from the vault using the token."
   caption="Figure 12.7 — The producer stores the payload and publishes only a claim; the consumer fetches the body out of band" %}

The producer PUTs the payload to the vault and publishes the claim; the consumer reads
the claim and fetches the payload with the token. The broker holds **only the claim**,
so PII never crosses Kafka's wire or sits in its retention — and because the token can
expire and the store can revoke it, access stays time-bound and auditable. This is the
security-angled cousin of the large-payload handling in the failure-modes appendix:

```python
# producer: store the body, publish only a reference
key = f"payloads/{order_id}"
store.put(key, large_payload, encrypt=True)            # encrypted at rest, ACL'd
await producer.send("order.documents", {               # claim only — small, routable
    "order_id": order_id,
    "uri": f"s3://vault/{key}",
    "token": mint_scoped_token(key, ttl_seconds=900),  # time-bound, revocable
})

# consumer: read the claim, fetch the body out of band
async for msg in consumer:
    body = store.get(msg["uri"], token=msg["token"])   # PII never touched the topic
```

## Choosing the right pattern

Every pattern is a trade, so the cost line matters as much as the benefit:

- **Sidecar** when you want one uniform security policy across every workload
  regardless of language — cost: an extra container per pod (a few MB, a little
  startup time). For most systems the uniformity is worth it.
- **Valet key** when clients need direct access to a large resource (file upload,
  image download) — cost: the storage system must validate the token.
- **Bulkhead** when one noisy tenant must not sink the others — cost: capacity is
  partitioned, so you can't pool it.
- **Zero-trust** when a breach must stay contained — cost: identity and policy on every
  hop, which the mesh largely absorbs for you.
- **Policy-as-code** when security rules must be enforced uniformly and reviewably —
  cost: writing and maintaining the policies, paid back the first time CI catches a bad
  change.
- **Claim-check** when payloads are large or sensitive — cost: a second fetch and a
  store to manage, in exchange for keeping bulk and PII off the broker.

### Cross-check it yourself

Test the deny path, which is the one that matters. Call `order-service` *directly*,
bypassing the mesh, with no `X-Forwarded-Client-Cert`, and confirm you get `403` —
the app trusts only the sidecar. Then apply a Deployment with an unsigned image and
confirm Gatekeeper rejects it at admission, and that the same policy fails the CI
step pre-merge. A request without identity being refused, and an unsigned image
being blocked twice, is the layered model working.

---
*Verification status: unverified — code transcribed and normalised from the source
decks, not yet run against a live mesh + Gatekeeper. The `examples/12-security/`
runner moves it to verified.*
