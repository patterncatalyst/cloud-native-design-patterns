---
title: "Cloud-Native Principles"
order: 1
part: "Foundations & the system"
description: "Cloud-native as a set of runtime properties, not a stack of tools — the six pillars, leaning on the platform, design-first contracts, and the twelve-factor app reframed by who owns each factor."
duration: 17 minutes
---

Before any pattern, the principles that justify them. "Cloud-native" is not a
list of products you adopt; it is a set of **runtime properties** a system has —
and every later choice in this book either earns or spends one of them.

## Six pillars

A cloud-native service exhibits six runtime properties — and the platform exists to
make each of them the default:

{% include excalidraw.html
   file="01-six-pillars"
   alt="A central hub labelled Cloud-native API on Kubernetes radiates spokes to six surrounding pillars: Disposable (fast start, clean stop, no local state), Resilient (timeouts, retries, circuit breakers, graceful degradation), Automatable (declarative config, GitOps and CRDs, self-healing), Observable (traces, metrics, logs, health, RED/USE signals), Elastic (scale to load, scale to zero with KEDA), and Loosely coupled (contracts not calls, async where it fits, independent deploy). A note reads: cloud-native is a set of runtime properties an API must exhibit to thrive on Kubernetes, not a checklist of tools."
   caption="Figure 1.1 — Cloud-native in six pillars: the runtime properties an API must exhibit on Kubernetes" %}

Read each as a behaviour you design toward, not a product you install:

- **Disposable** — twelve-factor: fast start, clean stop, no local state, so the
  platform can move or restart it at will.
- **Observable** — it emits traces, metrics, and logs, and exposes health probes.
- **Resilient** — timeouts, retries, circuit breakers, graceful degradation.
- **Elastic** — it scales to load, and to zero.
- **Automatable** — declarative config, GitOps, self-healing.
- **Loosely coupled** — contracts not calls, async where it fits.

These six are the rubric for every pattern in this book. Hold each design decision up
to them.

## Lean on the platform

The most important move is to **lean on the platform instead of reimplementing
it.** Don't write your own retry library when the mesh does it at the wire; don't
build a bespoke autoscaler when KEDA scales on lag and request rate; don't
hand-roll metrics plumbing when OpenTelemetry and the LGTM stack give it to you.
Every line of resilience code you write *per service* is a line you maintain
forever and that drifts between teams. The platform makes the good behaviour the
default; your job is to stay out of its way and use it.

## Design-first: the contract precedes the code

Design-first is the cultural prerequisite for everything that follows. The
contract — OpenAPI, `.proto`, AsyncAPI — is agreed and registered *before* code
is written, owned by the producing domain, and gated in CI. Consumers code
against the contract and its generated stubs, never against your database. That
is what delivers independent deployability: the contract *is* the
service boundary. Skip it and you get distributed coupling — the worst of both
worlds.

## The twelve-factor app, revisited

The twelve-factor app is the 2011 Heroku methodology that first codified what we
now call cloud-native. It predates Kubernetes yet maps onto it almost perfectly.
Here are all twelve, one line each.

{% include excalidraw.html
   file="01-twelve-factors"
   alt="A grid of the twelve factors, each with a number, name, and one-line summary: 01 codebase (one repo, many deploys), 02 dependencies (declare and isolate), 03 config (read from the environment), 04 backing services (treat as attached resources), 05 build/release/run (keep the stages separate), 06 processes (stateless, share-nothing), 07 port binding (export a service via a port), 08 concurrency (scale out with processes), 09 disposability (fast start, graceful stop), 10 dev/prod parity (keep environments alike), 11 logs (treat as event streams), 12 admin processes (run as one-off tasks)."
   caption="Figure 1.2 — The twelve factors at a glance" %}

The useful way to read it today is not to recite all twelve, but to split them by
**who owns each one** — the few you still write, versus the many the platform now
provides built in.

{% include excalidraw.html
   file="01-twelve-factor-ownership"
   alt="Two columns: the factors you still write per service (config from the environment, stateless processes, fast clean start and stop, logs as event streams, health and readiness probes) versus the factors the platform provides (build/release/run, concurrency and scaling, disposability, port binding, backing services, retries and timeouts)"
   caption="Figure 1.3 — The twelve factors, split by who owns them" %}

The left column is your job; the right column is the platform's. The whole point
of a cloud-native service is to do the left column well and trust the right
column — which is exactly what this code does.

## Twelve factors, mapped to our system

Grouped by what each factor *asks of you*, the twelve land on concrete choices in
the running example — and most resolve to a platform default rather than code you
write.

{% include excalidraw.html
   file="01-factors-mapped"
   alt="Five rows mapping groups of factors to the system: build and ship becomes built once, run anywhere (one repo, pinned requirements, one image per release); configure becomes config from the environment (pydantic-settings, per-profile, secrets injected); run on the platform becomes disposable, stateless, scaled (KEDA scale-out and to-zero, fast start/stop, behind Istio); attach resources becomes backing services as swappable URLs (Postgres, Kafka via Strimzi, Apicurio, never in-process); operate becomes signals and admin off the hot path (OpenTelemetry to LGTM, admin as Jobs and CronJobs). Each row carries a section reference."
   caption="Figure 1.4 — The twelve factors grouped by ask, mapped to where each lives in the system" %}

Five groups cover all twelve. *Build & ship* (codebase, dependencies, build/release/run,
parity) becomes one repo and one image per release. *Configure* (config) is read from
the environment. *Run on the platform* (stateless processes, concurrency, disposability,
port binding) is the runtime's job — KEDA scales it, Istio fronts it, the platform
disposes of it. *Attach resources* (backing services) makes Postgres, Kafka, and the
schema registry swappable URLs, never libraries compiled in. And *operate* (logs, admin
processes) pushes telemetry and one-off tasks off the request hot path, into
OpenTelemetry and Kubernetes Jobs. The section tags on each row point to where that
group is treated in depth — most of the twelve are now adopted, not authored.

## A twelve-factor service, ready for the platform

Two factors dominate the code you write: **config from the environment**
(factor III) and **health and readiness probes** the platform calls. Here it is
in each stack — pick your tab.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// HealthController.java (excerpt), examples/01-cloud-native-principles/spring-boot
// config from env (factor III): SPRING_DATASOURCE_URL, SERVICE_VERSION -> service.version
@RestController
public class HealthController {
    private final DataSource dataSource;
    @Value("${service.version}")
    private String serviceVersion;
    public HealthController(DataSource dataSource) { this.dataSource = dataSource; }
    @GetMapping("/healthz")                           // liveness: the process is up
    public Map<String, String> healthz() { return Map.of("status", "ok"); }
    @GetMapping("/readyz")                            // readiness: SELECT 1 on the pool
    public ResponseEntity<Map<String, Object>> readyz() {
        try (var conn = dataSource.getConnection()) {
            conn.createStatement().executeQuery("SELECT 1").close();
        } catch (Exception e) {                       // down: 503, the pod leaves the Service
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("status", "down", "checks", Map.of("database", "unreachable")));
        }
        return ResponseEntity.ok(Map.of("status", "ready",
                "checks", Map.of("database", "ok")));
    }
}
```

```java
// HealthResource.java (excerpt), examples/01-cloud-native-principles/quarkus
@Path("/") @Produces(MediaType.APPLICATION_JSON)
public class HealthResource {
    @ConfigProperty(name = "quarkus.datasource.jdbc.url") String jdbcUrl;  // env, factor III
    @GET @Path("healthz")                    // liveness: the process is up
    public Map<String, String> healthz() { return Map.of("status", "ok"); }
    @GET @Path("readyz")                     // readiness: SELECT 1 (one retry elided)
    public Response readyz() {
        try (var conn = DriverManager.getConnection(jdbcUrl, dbUser, dbPass);
             var rs = conn.createStatement().executeQuery("SELECT 1")) {
            return Response.ok(Map.of("status", "ready",
                    "checks", Map.of("database", "ok"))).build();
        } catch (Exception e) {              // down: 503, out of rotation
            return Response.status(Response.Status.SERVICE_UNAVAILABLE)
                .entity(Map.of("status", "down", "checks", Map.of("database", "unreachable")))
                .build();
        }
    }
}
```

```csharp
// Program.cs (excerpt), examples/01-cloud-native-principles/dotnet
var builder = WebApplication.CreateBuilder(args);
// ... ConnectionStrings__Default from the environment (factor III) -> NpgsqlDataSource
var app = builder.Build();
app.MapGet("/healthz", () => new { status = "ok" });          // liveness: the process is up
app.MapGet("/readyz", async (NpgsqlDataSource db) =>          // readiness: SELECT 1
{
    try
    {
        await using var conn = await db.OpenConnectionAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT 1";
        await cmd.ExecuteScalarAsync();
        return Results.Ok(new { status = "ready", checks = new { database = "ok" } });
    }
    catch                                                     // down: 503, out of rotation
    {
        return Results.Json(new { status = "down", checks = new { database = "unreachable" } },
            statusCode: StatusCodes.Status503ServiceUnavailable);
    }
});
```

```python
# main.py (excerpt); requirements.txt pins every package with ==
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings

class Settings(BaseSettings):           # config from env — factor III
    database_url: str
    kafka_bootstrap: str = ""
    service_version: str = "0.0.0"

settings = Settings()
app = FastAPI(title="order-service", version=settings.service_version, lifespan=lifespan)

@app.get("/healthz")                     # liveness — the process is up
def healthz(): return {"status": "ok"}

@app.get("/readyz")                      # readiness — dependencies are reachable
async def readyz():
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        return JSONResponse({"status": "down", "checks": {"database": "unreachable"}}, 503)
    return {"status": "ready", "checks": {"database": "ok"}}
```

```cpp
// main.cpp (excerpt), examples/01-cloud-native-principles/cpp; conan.lock pins every library
using Callback = std::function<void(const HttpResponsePtr&)>;
const char* env(const char* name, const char* fallback) {   // config from env, factor III
  const char* v = std::getenv(name);  return v ? v : fallback;   // unset: the default
}
int main() {
  g_version = env("SERVICE_VERSION", "1.0.0");
  g_pool = std::make_unique<cndp::PgPool>(
      env("PG_CONNINFO", "postgresql://appuser:apppass@postgres:5432/appdb"),
      std::atoi(env("PG_POOL_SIZE", "4")));
  app().registerHandler("/healthz", [](const HttpRequestPtr&, Callback&& cb) {
    Json::Value j;  j["status"] = "ok";  cb(HttpResponse::newHttpJsonResponse(j));  // liveness
  }, {Get});
  app().registerHandler("/readyz", [](const HttpRequestPtr&, Callback&& cb) {
    const bool db_ok = db_ready();             // SELECT 1 via the libpq pool (retry elided)
    Json::Value j;  j["status"] = db_ok ? "ready" : "down";
    auto resp = HttpResponse::newHttpJsonResponse(j);
    if (!db_ok) resp->setStatusCode(k503ServiceUnavailable);   // down: out of rotation
    cb(resp);
  }, {Get});
  app().addListener("0.0.0.0", 8080).run();    // factor VII: port binding
}
```

```go
// main.go (excerpt), examples/01-cloud-native-principles/go: config from env, two probes
func (s *Server) handleHealthz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(HealthResponse{Status: "ok"}) // liveness: the process is up
}
func (s *Server) handleReadyz(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	w.Header().Set("Content-Type", "application/json")
	if err := s.pool.Ping(ctx); err != nil { // readiness: the database answers
		w.WriteHeader(http.StatusServiceUnavailable) // 503: out of rotation, not restarted
		json.NewEncoder(w).Encode(ReadinessResponse{Status: "down",
			Checks: map[string]string{"database": "unreachable"}})
		return
	}
	json.NewEncoder(w).Encode(ReadinessResponse{Status: "ready",
		Checks: map[string]string{"database": "ok"}})
}
// main(): SERVICE_VERSION and DATABASE_URL come from the environment (factor III); the mux
// serves /, /healthz, /readyz and /orders on :8080 (factor VII, port binding)
```

### How the code works

The same two ideas appear in every tab:

1. **Config comes from the environment, never from a baked-in file.** Spring and
   Quarkus resolve their datasource URL and `service.version` from environment
   variables, .NET reads `ConnectionStrings__Default` through its configuration
   (env vars override `appsettings.json`), Python binds a `BaseSettings` class to env
   vars, and C++ and Go read `std::getenv` and `os.Getenv`. One
   image, many environments — factor III, and the thing that lets the same
   artifact run in dev, staging, and production unchanged.
2. **Two probes, not one.** *Liveness* answers "is the process up?" — if it fails,
   the platform restarts the pod. *Readiness* answers "are my dependencies
   reachable?" — if it fails, the platform stops routing traffic to this instance
   but leaves it running. Conflating the two is a classic mistake: a readiness
   blip should drain traffic, not trigger a restart loop. The probe reads the
   **status code**, not the body: Kubernetes counts any answer from 200 to 399 as
   ready, so `/readyz` answers `503` (with `"status": "down"` in the body for
   people) when the database is unreachable. Every tab writes the two handlers by
   hand, as the examples do, so all six languages serve the same paths and bodies;
   Spring Boot Actuator, SmallRye Health and ASP.NET Core health checks are the
   framework routes to the same pair, and Kubernetes calls them the same way.

Notice what *isn't* here: no retry logic, no scaling code, no port-binding
plumbing. Those are the right column of Figure 1.3 — the platform's job.

### Cross-check it yourself

With the service running, the probes are just HTTP. Hit liveness and readiness
with `curl` and confirm liveness returns healthy while the database is down but
readiness does *not* — that difference is the whole point. `curl -i
localhost:8080/readyz` should flip from `200` ready to `503` down as you stop the
database and back as you start it, without the process ever restarting.

The code is in [`examples/01-cloud-native-principles/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/01-cloud-native-principles/). The run script there builds
and runs it; its `README.md` covers what it does and how to drive it.

---
*Verification status: verified — [`examples/01-cloud-native-principles/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/01-cloud-native-principles/) passes 13/13 checks in each of the six languages on Docker Engine (2026-10-12)
(health probes, config from environment, CRUD, readiness flip on dependency failure).*
