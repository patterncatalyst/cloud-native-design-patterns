---
title: "Security"
order: 12
part: "Security & anti-patterns"
description: "Security as four concentric layers — cloud, cluster, container, code — and seven patterns that secure them, from the sidecar that reads trusted identity headers to policy-as-code enforced at admission."
duration: 20 minutes
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

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

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

The `X-Forwarded-Client-Cert` carries the validated caller identity from mTLS —
typically a SPIFFE id like `spiffe://cluster.local/ns/orders/sa/order-service`. The
app reads it as a value; it does no certificate work itself. Every tab is the same
two moves: deny if the identity header is absent, and trust (never re-check) the
claims the sidecar forwarded.

## Policy-as-code

The other pattern worth showing in code is **policy-as-code**: security rules
declared in Git, enforced the same way at two points — `conftest`/Kyverno in CI
*pre-merge*, and OPA Gatekeeper or Kyverno at *admission* on the cluster. The same
policy catches a violation before merge and blocks it again if it somehow reaches
`kubectl apply`.

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

## Choosing the right pattern

Every pattern is a trade, so the cost line matters as much as the benefit:

- **Sidecar** when you want one uniform security policy across every workload
  regardless of language — cost: an extra container per pod (a few MB, a little
  startup time). For most systems the uniformity is worth it.
- **Valet key** when clients need direct access to a large resource (file upload,
  image download) — cost: the storage system must validate the token.
- **Bulkhead** when one noisy tenant must not sink the others — cost: capacity is
  partitioned, so you can't pool it.

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
