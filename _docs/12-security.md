---
title: "Security"
order: 12
part: "Security & anti-patterns"
description: "Security as four concentric layers (cloud, cluster, container, code) and seven patterns that secure them, from the sidecar that reads trusted identity headers to policy-as-code enforced at admission."
duration: 30 minutes
---

Security isn't a feature you bolt on; it's a property of every layer, and the
cloud-native way to reason about it is the CNCF's **4 C's**: concentric layers,
each protecting what's inside it, so a breach of one is contained by the next.

## The 4 C's of cloud-native security

{% include excalidraw.html
   file="12-four-cs"
   alt="Four concentric layers: Cloud (IAM, VPC, KMS, audit) on the outside, then Cluster (RBAC, NetworkPolicy, Pod Security, admission), then Container (minimal image, non-root, read-only filesystem, signed), with Code (authz, input validation, secrets, dependencies) at the centre"
   caption="Figure 12.1: Cloud → Cluster → Container → Code, each layer protecting the one inside" %}

- **Cloud**: the perimeter, identities, and keys: IAM with least privilege, VPC
  isolation, KMS, audit logging, data-residency. Owned by the platform/cloud team.
  Failures here look like "someone left a bucket open" or "an over-permissive role
  enabled lateral movement."
- **Cluster**: the Kubernetes layer: RBAC, `NetworkPolicy` (default-deny plus
  targeted allows), Pod Security Standards (restricted), admission control.
- **Container**: a minimal image, non-root, read-only root filesystem, and a
  *signed* image so only trusted artifacts run.
- **Code**: your application: authorization, input validation, secret handling,
  and keeping dependencies patched.

The value of the model is that controls live at the right layer with the right
owner, instead of every team trying to do everything in application code.

## Seven patterns to know

These span the 4 C's, and you'll meet several again in the appendices:

- **Sidecar**: move cross-cutting security (mTLS, JWT, audit, rate-limiting) into a
  companion process. *(Cluster/container layer.)*
- **Valet key**: hand the client a short-lived signed token for *direct* access to
  a resource, so your app stops proxying large payloads and sheds attack surface.
- **Strangler fig**: encapsulate legacy auth behind a gateway and replace it piece
  by piece. *(The modernisation pattern from Appendix K, applied to security.)*
- **Zero-trust / identity-aware proxy**: every request authenticated and
  authorised; perimeter trust is dead.
- **Policy-as-code**: security gates declared in Git, enforced at admission and in
  CI.
- **Bulkhead**: isolate resources (per-tenant pools) so one tenant's overload
  can't sink the rest. *(Returns in Appendix M.)*
- **Claim-check**: for large payloads, publish a *reference* and let the consumer
  fetch the body, keeping secrets and bulk out of the event stream.

## The sidecar reads trusted headers

The sidecar pattern is the one to internalise, because the mesh chapters already
put an Envoy sidecar in every pod. It terminates mTLS, validates JWTs, and enforces
policy, so the app receives only authenticated, authorised requests and reads the
identity as **plain, trusted headers**. Two rules: the app must **reject** any
request missing the sidecar-set identity, and it must **never re-validate** the JWT
signature. The sidecar already did, and re-doing it duplicates trust and drifts.

{% include excalidraw.html
   file="12-sidecar"
   alt="Clients reach a Kubernetes pod whose app container holds business logic only (no TLS, auth, rate-limit, or audit code), talking over localhost to an Envoy/OPA sidecar that terminates mTLS, validates JWTs, rate-limits, audits, enforces policy, and emits metrics and traces before egress. The app trusts the sidecar's headers."
   caption="Figure 12.2: Security concerns move out of the app and into an Envoy/OPA sidecar in the same pod" %}

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

The `X-Forwarded-Client-Cert` carries the validated caller identity from mTLS:
typically a SPIFFE id like `spiffe://cluster.local/ns/orders/sa/order-service`. The
app reads it as a value; it does no certificate work itself. Every tab is the same
two moves: deny if the identity header is absent, and trust (never re-check) the
claims the sidecar forwarded.

## The valet key hands out direct access

When a client needs a *large* resource (upload an attachment, download an export),
proxying those bytes through your service is wasted work and extra attack surface. The
**valet key** pattern hands the client a short-lived, scoped, signed token and lets it
talk to the storage system directly.

{% include excalidraw.html
   file="12-valet-key"
   alt="A client requests a key from the application, which mints a scoped, time-bound, operation-restricted valet key and returns a signed token. The client then PUTs or GETs directly against the resource (object store, file) using the token; the storage/KMS layer validates the token, permits the named operation, and rejects everything else. The app never proxies the bytes."
   caption="Figure 12.3: The app mints a scoped, time-bound token; the client accesses storage directly and the app never proxies the bytes" %}

The application mints a key that is *scoped* (this one object), *time-bound* (minutes,
not forever), and *operation-restricted* (PUT or GET, not both). The client uses it to
reach the resource directly; the storage system validates the token, permits exactly
the named operation, and rejects everything else. No long-lived credential ever lands
on the client, and your service is out of the data path:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// ValetKeyService.java (excerpt), examples/12-security/spring-boot: HMAC-SHA256 valet key
@Service
public class ValetKeyService {
    private static final int TTL_SECONDS = 300;                       // time-bound
    private final byte[] secret;          // VALET_SECRET, injected through @Value
    public Map<String, Object> mint(String resource, String operation) {
        long expires = System.currentTimeMillis() / 1000 + TTL_SECONDS;
        String payload = resource + ":" + operation + ":" + expires;  // one object, one op
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("resource", resource);
        result.put("operation", operation);
        result.put("expires", expires);
        result.put("token", hmac(payload));               // HmacSHA256, hex-encoded
        return result;
    }
    public boolean verify(String resource, String operation, long expires, String token) {
        if (System.currentTimeMillis() / 1000 > expires) return false;   // expired
        String expected = hmac(resource + ":" + operation + ":" + expires);
        return MessageDigest.isEqual(token.getBytes(), expected.getBytes()); // constant time
    }
}
// OrderController maps POST /valet-key to mint() and GET /verify-valet to verify()
```

```java
// ValetKeyService.java (excerpt), examples/12-security/quarkus: HMAC-SHA256 valet key
@ApplicationScoped
public class ValetKeyService {
    private static final int TTL_SECONDS = 300;                       // time-bound
    private final byte[] secret;          // VALET_SECRET, injected through @ConfigProperty
    public Map<String, Object> mint(String resource, String operation) {
        long expires = System.currentTimeMillis() / 1000 + TTL_SECONDS;
        String payload = resource + ":" + operation + ":" + expires;  // one object, one op
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("resource", resource);
        result.put("operation", operation);
        result.put("expires", expires);
        result.put("token", hmac(payload));               // HmacSHA256, hex-encoded
        return result;
    }
    public boolean verify(String resource, String operation, long expires, String token) {
        if (System.currentTimeMillis() / 1000 > expires) return false;   // expired
        String expected = hmac(resource + ":" + operation + ":" + expires);
        return MessageDigest.isEqual(token.getBytes(), expected.getBytes()); // constant time
    }
}
// OrderResource maps POST /valet-key to mint() and GET /verify-valet to verify()
```

```csharp
// Program.cs (excerpt), examples/12-security/dotnet: an HMAC-SHA256 valet key
var valetSecret = builder.Configuration.GetValue("VALET_SECRET", "demo-secret-do-not-use-in-prod");
app.MapPost("/valet-key", (HttpContext ctx) =>
{
    var resource = ctx.Request.Query["resource"].ToString();
    var operation = ctx.Request.Query["operation"].FirstOrDefault() ?? "GET";
    var expires = DateTimeOffset.UtcNow.ToUnixTimeSeconds() + 300;      // time-bound
    var payload = $"{resource}:{operation}:{expires}";                 // one object, one op
    var sig = ComputeHmac(valetSecret, payload);
    return Results.Ok(new { resource, operation, expires, token = sig });
});
// GET /verify-valet: 403 once expired, then a constant-time compare
    if (DateTimeOffset.UtcNow.ToUnixTimeSeconds() > expires)
        return Results.Json(new { detail = "expired valet key" }, statusCode: 403);
    var expected = ComputeHmac(valetSecret, $"{resource}:{operation}:{expires}");
    if (!CryptographicOperations.FixedTimeEquals(
            Encoding.UTF8.GetBytes(token), Encoding.UTF8.GetBytes(expected)))
        return Results.Json(new { detail = "invalid or expired valet key" }, statusCode: 403);
// ComputeHmac: HMACSHA256 keyed with the secret, Convert.ToHexStringLower of the hash
```

```python
# main.py (excerpt), examples/12-security/python: an HMAC-SHA256 valet key
class Settings(BaseSettings):                               # VALET_SECRET from the environment
    valet_secret: str = "demo-secret-do-not-use-in-prod"

settings = Settings()

def _mint_valet(resource: str, operation: str, ttl: int = 300) -> dict:
    expires = int(time.time()) + ttl                        # time-bound
    payload = f"{resource}:{operation}:{expires}"           # one object, one operation
    sig = hmac.new(settings.valet_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {"resource": resource, "operation": operation, "expires": expires, "token": sig}

def _verify_valet(resource: str, operation: str, expires: int, token: str) -> bool:
    if time.time() > expires:
        return False                                        # expired: worthless
    payload = f"{resource}:{operation}:{expires}"
    expected = hmac.new(
        settings.valet_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(token, expected)             # constant-time compare

@app.post("/valet-key")
async def mint_key(resource: str, operation: str = "GET"):
    return _mint_valet(resource, operation)
# GET /verify-valet answers 403 for an expired or tampered key
```

```cpp
// valet.hpp (excerpt), examples/12-security/cpp: the valet key is an HS256 JWT (jwt-cpp)
inline Minted mint(const std::string& secret, const std::string& resource,
                   const std::string& operation,
                   std::chrono::seconds ttl = std::chrono::minutes(5)) {   // time-bound
    const auto now = std::chrono::system_clock::now();
    const auto exp = std::chrono::time_point_cast<std::chrono::seconds>(now + ttl);
    auto token = jwt::create()
                     .set_type("JWT")
                     .set_issuer(kIssuer)                         // "order-service"
                     .set_issued_at(now)
                     .set_expires_at(exp)
                     .set_payload_claim("res", jwt::claim(resource))   // one object
                     .set_payload_claim("op", jwt::claim(operation))   // one operation
                     .sign(jwt::algorithm::hs256{secret});
    return {std::move(token), exp.time_since_epoch().count()};
}
// verify(): HS256 pinned ("none" and RS256 never reach the verifier), then iss, res, op
const auto decoded = jwt::decode(token);
if (decoded.get_algorithm() != "HS256") return false;
jwt::verify().allow_algorithm(jwt::algorithm::hs256{secret}).with_issuer(kIssuer)
    .with_claim("res", jwt::claim(resource)).with_claim("op", jwt::claim(operation))
    .verify(decoded);                                  // signature + exp; throws on failure
```

```go
// main.go (excerpt), examples/12-security/go — the valet key is an HS256 JWT (golang-jwt v5)
type valetClaims struct {
	Resource  string `json:"res"`
	Operation string `json:"op"`
	jwt.RegisteredClaims
}

func mintValet(resource, operation string) map[string]any {
	expires := time.Now().Add(5 * time.Minute) // time-bound
	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, valetClaims{
		Resource:  resource,  // scoped: this one object
		Operation: operation, // operation-restricted: GET or PUT, not both
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(expires),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Issuer:    "order-service",
		},
	}).SignedString([]byte(valetSecret))
	if err != nil {
		slog.Error("sign valet key", "err", err)
	}
	return map[string]any{"resource": resource, "operation": operation,
		"expires": expires.Unix(), "token": token}
}
// the verifier accepts HS256 only, requires exp, checks the issuer, then matches res, op and exp
```

Example 12 mints and verifies the ticket in the service itself. Most object stores, open-source ones included,
accept signed URLs of the same shape: the method, the object key and the expiry signed into the URL.

## Zero-trust: every request proves itself

The old perimeter model (VPN in, then trust everything on the intranet) fails the
moment one host is compromised: the attacker is *inside*, and lateral movement is
trivial. **Zero-trust** discards the perimeter. Every request, even service-to-service
inside the cluster, must carry a verifiable identity and pass policy on *every* hop.

{% include excalidraw.html
   file="12-zero-trust"
   alt="Top: the old perimeter model (VPN to a trusted intranet to any service), where getting in once means trusted forever and lateral movement is trivial. Bottom: the zero-trust model: user/device to an IAP/auth proxy (who, where, device, MFA, posture) to a policy engine making a per-request decision (OPA/Cedar) to a service that accepts only requests carrying a valid claim, repeated for every downstream call, with mTLS and SPIFFE identity inside the cluster."
   caption="Figure 12.4: Perimeter trust versus zero-trust: identity and policy are checked on every hop, not once at the edge" %}

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
declared in Git, enforced the same way at two points: `conftest`/Kyverno in CI
*pre-merge*, and OPA Gatekeeper or Kyverno at *admission* on the cluster. The same
policy catches a violation before merge and blocks it again if it somehow reaches
`kubectl apply`.

{% include excalidraw.html
   file="12-policy-as-code"
   alt="A developer commits to Git/CI (conftest, kyverno, pre-merge gate), then kubectl apply (or ArgoCD/Flux) sends objects to an admission controller (OPA Gatekeeper/Kyverno) that evaluates ConstraintTemplates against incoming objects and the API server accepts or rejects based on policy. Policy in Rego or Kyverno YAML (images must be signed, no privileged containers) is loaded into the admission controller."
   caption="Figure 12.5: Policy lives in Git and is enforced at admission; no human runs a checklist" %}

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

Borrowed from ship design: watertight compartments stop one breach from sinking the
whole hull. In a service, the **bulkhead** isolates resources so one tenant's overload
can't starve the others. Share one connection pool and one thread group across every
tenant and a single client's storm drains the pool for everyone; give each tenant its
own bounded pool and the storm is contained to that tenant.

{% include excalidraw.html
   file="12-bulkhead"
   alt="Without bulkheads, a shared pool and shared thread group serve customer A traffic, customer B traffic, background jobs, and scheduled work together, so one client's storm starves everyone. With bulkheads, customer A, customer B, and background each get their own bounded connection pool and thread group, so A's storm fails only A while B and background keep working and the blast radius is bounded."
   caption="Figure 12.6: Per-tenant pools bound the blast radius: one tenant's storm fails only that tenant" %}

The implementation is a bounded resource per partition: a per-tenant connection pool,
a per-call thread group, or a semaphore that caps concurrency:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// examples/12-security/spring-boot/order-service: BulkheadService.java, OrderController.java (excerpts)
// application.properties: one Resilience4j bulkhead per tenant, created from the "tenant" config
//   resilience4j.bulkhead.configs.tenant.max-concurrent-calls=5
//   resilience4j.bulkhead.configs.tenant.max-wait-duration=0      <- refuse at once, don't queue
public Bulkhead forTenant(String tenant) {
    return registry.bulkhead(tenant, "tenant");
}

// POST /orders: A's storm can't drain B's capacity
try {
    Map<String, Object> order = bulkhead.forTenant(body.tenant())
            .executeSupplier(() -> placeOrder(body, identity, subject));
    return ResponseEntity.status(HttpStatus.CREATED).body(order);
} catch (BulkheadFullException e) {   // the tenant's 5 permits are taken
    return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS)
            .body(Map.of("detail", "tenant bulkhead full"));
}
```

```java
// examples/12-security/quarkus/order-service: BulkheadService.java, OrderResource.java (excerpts)
// One SmallRye Fault Tolerance guard per tenant (an annotation cannot be keyed by tenant):
// 5 concurrent calls and no queue, so the sixth fails at once with BulkheadException.
public <T> T run(String tenant, Supplier<T> work, Class<T> type) {
    return pools.computeIfAbsent(tenant, t -> newPool()).guard().get(work, type);
}

private static Pool newPool() {
    var inFlight = new AtomicInteger();
    var guard = Guard.create()
            .withBulkhead().limit(CAPACITY)
                .onAccepted(inFlight::incrementAndGet)   // feeds /bulkhead-state
                .onFinished(inFlight::decrementAndGet)
                .done()
            .build();
    return new Pool(guard, inFlight);
}

// POST /orders: A's storm can't drain B's capacity
try {
    return bulkhead.run(body.tenant(), () -> placeOrder(body, identity, subject), Response.class);
} catch (BulkheadException e) {
    return Response.status(429).entity(Map.of("detail", "tenant bulkhead full")).build();
}
```

```csharp
// examples/12-security/dotnet/OrderService/Program.cs (excerpts)
// One concurrency limiter per tenant (System.Threading.RateLimiting): 5 permits, no queue.
const int BulkheadLimit = 5;
var bulkhead = PartitionedRateLimiter.Create<string, string>(tenant =>
    RateLimitPartition.GetConcurrencyLimiter(tenant, _ => new ConcurrencyLimiterOptions
    {
        PermitLimit = BulkheadLimit,
        QueueLimit = 0,
    }));

// POST /orders: A's storm can't drain B's capacity
app.MapPost("/orders", async (OrderRequest body, HttpContext ctx) =>
{
    using var lease = await bulkhead.AcquireAsync(body.Tenant);
    if (!lease.IsAcquired)   // the tenant's 5 permits are taken
        return Results.Json(new { detail = "tenant bulkhead full" }, statusCode: StatusCodes.Status429TooManyRequests);
    // ... create the order while the lease is held
});
```

```python
# examples/12-security/python/order-service/main.py (excerpts)
# One semaphore of 5 permits per tenant; a request that finds them all taken is refused at once.
BULKHEAD_LIMIT = 5
_sems: dict[str, asyncio.Semaphore] = {}


def _tenant_sem(tenant: str) -> asyncio.Semaphore:
    return _sems.setdefault(tenant, asyncio.Semaphore(BULKHEAD_LIMIT))


@app.post("/orders", status_code=201)
async def create_order(body: OrderIn, request: Request):
    sem = _tenant_sem(body.tenant)
    if sem.locked():  # the tenant's 5 permits are taken
        return JSONResponse(status_code=429, content={"detail": "tenant bulkhead full"})
    async with sem:  # A's storm can't drain B's capacity
        ...
```

```cpp
// examples/12-security/cpp/order-service/src/main.cpp (excerpts): one lock-free counter per tenant
struct TenantBulkhead {
    static constexpr int CAPACITY = 5;                        // 5 concurrent per tenant
    std::atomic<int> active{0};
    bool try_acquire() {
        int current = active.load();
        while (current < CAPACITY) {
            if (active.compare_exchange_weak(current, current + 1)) return true;
        }
        return false;                                         // full: refuse, don't queue
    }
    void release() { active.fetch_sub(1); }
};

// POST /orders (a coroutine handler): A's storm can't drain B's capacity
auto& bulkhead = bulkhead_manager.get_or_create(tenant);     // map + mutex, one per tenant
if (!bulkhead.try_acquire()) {
    co_return reply(k429TooManyRequests, detail("tenant bulkhead full"));
}
BulkheadPermit permit{bulkhead};   // released when the handler finishes, however it finishes
```

```go
// examples/12-security/go/cmd/server/main.go (excerpts)
// One golang.org/x/sync semaphore per tenant: 5 permits; TryAcquire refuses the sixth at once.
type bulkhead struct {
	sem      *semaphore.Weighted
	inFlight atomic.Int64 // semaphore.Weighted does not report its count
}

func getTenantBulkhead(tenant string) *bulkhead {
	v, _ := bulkheads.LoadOrStore(tenant, &bulkhead{sem: semaphore.NewWeighted(bulkheadCapacity)})
	return v.(*bulkhead)
}

// POST /orders: A's storm can't drain B's capacity
bh := getTenantBulkhead(in.Tenant)
if !bh.sem.TryAcquire(1) { // the tenant's 5 permits are taken
	writeJSON(w, http.StatusTooManyRequests, map[string]string{"detail": "tenant bulkhead full"})
	return
}
bh.inFlight.Add(1)
defer func() {
	bh.inFlight.Add(-1)
	bh.sem.Release(1)
}()
```

Every version refuses at once with 429 when a tenant's pool is full, rather than queueing, so a storm fails
fast for that tenant instead of piling up waiting requests. The JVM examples take the bulkhead from their
resilience library (Resilience4j, SmallRye Fault Tolerance) and .NET from System.Threading.RateLimiting; Python
and Go use a semaphore from the standard library and `golang.org/x/sync`. At the mesh, Istio's per-destination
connection-pool limits do the same job for every service at once.

## Claim-check: send a reference, not the payload

When a message is large *or* sensitive, putting it on the topic is wrong twice: it
bloats the broker, and the payload then lives in topic retention where it can leak. The
**claim-check** pattern publishes only a *reference* (a URI plus a signed token) and
stores the body in an encrypted object store the consumer fetches directly.

{% include excalidraw.html
   file="12-claim-check"
   alt="A producer PUTs a large or sensitive payload to an encrypted object store/vault (ACLs per object, retention policy) and publishes only a small, routable claim (a URI plus signed token) to the Kafka message bus, which holds only the token with no PII in topic history. A consumer consumes the claim and then fetches the payload directly from the vault using the token."
   caption="Figure 12.7: The producer stores the payload and publishes only a claim; the consumer fetches the body out of band" %}

The producer PUTs the payload to the vault and publishes the claim; the consumer reads
the claim and fetches the payload with the token. The broker holds **only the claim**,
so PII never crosses Kafka's wire or sits in its retention, and because the token can
expire and the store can revoke it, access stays time-bound and auditable. This is the
security-angled cousin of the large-payload handling in the failure-modes appendix:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key
@Service
public class ClaimPublisher {
    private final ObjectStore store;                           // any encrypted object store
    private final KafkaTemplate<String, Map<String, Object>> kafka;
    private final ValetKeyService valet;                       // examples/12-security
    // constructor injection omitted
    public void publish(String orderId, byte[] body) {
        String key = "payloads/" + orderId;
        store.put(key, body, true);                            // encrypted at rest, ACL'd
        Map<String, Object> claim = new LinkedHashMap<>(valet.mint(key, "GET"));
        claim.put("order_id", orderId);
        claim.put("uri", "https://objects.internal/" + key);
        kafka.send("order.documents", orderId, claim);         // only the claim on the topic
    }
}
// consumer: read the claim, fetch the body out of band
@KafkaListener(topics = "order.documents", groupId = "documents")
public void onClaim(Map<String, Object> claim) {
    byte[] body = store.get((String) claim.get("uri"), (String) claim.get("token"));
    handle(body);                                              // PII never touched the topic
}
```

```java
// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key
@ApplicationScoped
public class ClaimPublisher {
    @Inject ObjectStore store;                                 // any encrypted object store
    @Inject ValetKeyService valet;                             // examples/12-security
    @Inject @Channel("documents-out") Emitter<JsonObject> claims;   // topic order.documents
    public void publish(String orderId, byte[] body) {
        String key = "payloads/" + orderId;
        store.put(key, body, true);                            // encrypted at rest, ACL'd
        JsonObject claim = new JsonObject(valet.mint(key, "GET"))
            .put("order_id", orderId)
            .put("uri", "https://objects.internal/" + key);
        claims.send(claim);                                    // only the claim on the topic
    }
}
@ApplicationScoped
public class ClaimConsumer {
    @Inject ObjectStore store;
    @Incoming("documents-in")                                  // topic order.documents
    public void onClaim(JsonObject claim) {
        byte[] body = store.get(claim.getString("uri"), claim.getString("token"));
        handle(body);                                          // PII never touched the topic
    }
}
```

```csharp
// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key
var key = $"payloads/{orderId}";
await store.PutAsync(key, largePayload, encrypt: true);   // encrypted at rest, ACL'd
var expires = DateTimeOffset.UtcNow.ToUnixTimeSeconds() + 900;
var token = ComputeHmac(valetSecret, $"{key}:GET:{expires}");   // GET only, 15 minutes
await producer.ProduceAsync("order.documents",
    new Message<Null, string> { Value = JsonSerializer.Serialize(new {
        order_id = orderId,
        uri = $"https://objects.internal/{key}",
        resource = key, operation = "GET", expires, token,
    }) });                                             // claim only: small, routable
// consumer: read the claim, fetch the body out of band
var claim = JsonSerializer.Deserialize<Claim>(cr.Message.Value)!;
var body = await store.GetAsync(claim.Uri, claim.Token);  // PII never touched the topic
consumer.Commit(cr);
```

```python
# claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key
async def publish_with_claim(producer: AIOKafkaProducer, order_id: str, body: bytes):
    key = f"payloads/{order_id}"
    await store.put(key, body, encrypt=True)                # encrypted at rest, ACL'd
    claim = {
        "order_id": order_id,
        "uri": f"https://objects.internal/{key}",
        **_mint_valet(key, "GET", ttl=900),                  # resource, op, expires, token
    }
    await producer.send_and_wait(                           # only the claim goes on the topic
        "order.documents", json.dumps(claim).encode(), key=order_id.encode())

# consumer: read the claim, fetch the body out of band
async for msg in consumer:
    claim = json.loads(msg.value)
    body = await store.get(claim["uri"], token=claim["token"])   # the store checks the ticket
    await handle(body)                                      # PII never touched the topic
    await consumer.commit()                                 # after the side effect
```

```cpp
{% raw %}
// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key
void publish_with_claim(const std::string& order_id, const std::string& body) {
  const auto key = "payloads/" + order_id;
  store_.put(key, body, /*encrypt=*/true);                     // 1. store: encrypted, ACL'd
  auto ticket = cndp::valet::mint(VALET_SECRET, key, "GET", std::chrono::minutes(15));
  auto claim = nlohmann::json{{"order_id", order_id},
                              {"uri", "https://objects.internal/" + key},
                              {"token", ticket.token}, {"expires", ticket.expires}}.dump();
  producer_->produce("order.documents", RdKafka::Topic::PARTITION_UA,
                     RdKafka::Producer::RK_MSG_COPY, claim.data(), claim.size(),
                     order_id.data(), order_id.size(), 0, nullptr);   // 2. claim only
}
// Consumer: consume the claim, fetch the payload, then handle
std::unique_ptr<RdKafka::Message> msg(consumer_->consume(100));
if (msg->err() == RdKafka::ERR_NO_ERROR) {
  auto claim = nlohmann::json::parse(payload_of(*msg));
  auto body = store_.get(claim["uri"].get<std::string>(),
                         claim["token"].get<std::string>());     // the store checks the ticket
  handle(body);                                                // PII never touched the topic
  consumer_->commitSync(msg.get());                            // after handle
}
{% endraw %}
```

```go
// claim-check sketch: store is any encrypted object store; the token is the valet-key JWT
func publishWithClaim(ctx context.Context, cl *kgo.Client, orderID string, body []byte) error {
	key := "payloads/" + orderID
	if err := store.Put(ctx, key, body, true); err != nil { return err } // encrypted, ACL'd
	claim, _ := json.Marshal(map[string]any{
		"order_id": orderID,
		"uri":      "https://objects.internal/" + key,
		"token":    mintValet(key, "GET")["token"],          // GET only, five minutes
	})
	return cl.ProduceSync(ctx,                               // only the claim goes on the topic
		&kgo.Record{Topic: "order.documents", Key: []byte(orderID), Value: claim}).FirstErr()
}
func onClaim(ctx context.Context, r *kgo.Record) error {
	var c Claim
	if err := json.Unmarshal(r.Value, &c); err != nil { return err }
	body, err := store.Get(ctx, c.URI, c.Token)              // the store verifies the ticket
	if err != nil { return err }
	return handle(ctx, body)                                 // PII never touched the topic
}
```

## Choosing the right pattern

Every pattern is a trade, so the cost line matters as much as the benefit:

- **Sidecar** when you want one uniform security policy across every workload
  regardless of language. Cost: an extra container per pod (a few MB, a little
  startup time). For most systems the uniformity is worth it.
- **Valet key** when clients need direct access to a large resource (file upload,
  image download). Cost: the storage system must validate the token.
- **Bulkhead** when one noisy tenant must not sink the others. Cost: capacity is
  partitioned, so you can't pool it.
- **Zero-trust** when a breach must stay contained. Cost: identity and policy on every
  hop, which the mesh largely absorbs for you.
- **Policy-as-code** when security rules must be enforced uniformly and reviewably.
  Cost: writing and maintaining the policies, paid back the first time CI catches a bad
  change.
- **Claim-check** when payloads are large or sensitive. Cost: a second fetch and a
  store to manage, in exchange for keeping bulk and PII off the broker.

## Build, run, observe

```bash
cd examples/12-security/python     # or any of the six language stacks
docker compose up -d --build --wait
cd ..
./verify.sh
```

`verify.sh` runs the language-agnostic end-to-end checks against the running
stack (18/18 in each of the six languages), asserting: `/healthz` bypasses the
identity check; a request with no `X-Forwarded-Client-Cert` is refused with
`403` and a "no validated identity" body, while a request carrying the header
succeeds with `201` and echoes back the sidecar identity and the JWT subject
claim; a valet key is minted, verifies successfully, and is rejected with `403`
when tampered or used for the wrong operation; the per-tenant bulkhead reports
independent pools per tenant, and filling one tenant's pool with eight
concurrent slow requests gets some of them refused with `429` while another
tenant is still served `201`; and conftest's Rego policy accepts a
compliant manifest and rejects one with an untrusted image. JWT signature
validation, RBAC enforcement, and rate limiting are not covered.

Test the deny path, which is the one that matters. Call `order-service` *directly*,
bypassing the mesh, with no `X-Forwarded-Client-Cert`, and confirm you get `403`:
the app trusts only the sidecar. Then apply a Deployment with an unsigned image and
confirm Gatekeeper rejects it at admission, and that the same policy fails the CI
step pre-merge. A request without identity being refused, and an unsigned image
being blocked twice, is the layered model working.
