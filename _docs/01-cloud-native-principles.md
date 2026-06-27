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
   alt="A two-by-three grid of the six cloud-native pillars: Disposable (12-factor processes, fast start and clean stop, no local state), Observable (traces, metrics, logs; health and readiness; RED/USE signals), Resilient (timeouts, retries; circuit breakers; graceful degradation), Elastic (scale to load; scale to zero with KEDA; no fixed capacity), Automatable (declarative config; GitOps and CRDs; self-healing), and Loosely coupled (contracts not calls; async where it fits; independent deploy)."
   caption="Figure 1.1 — Cloud-native in six pillars: the runtime properties an API must exhibit on Kubernetes" %}

Read each as a behaviour you design toward, not a product you install:

- **Disposable** — twelve-factor: fast start, clean stop, no local state, so the
  platform can move or restart it at will.
- **Observable** — it emits traces, metrics, and logs, and exposes health probes.
- **Resilient** — timeouts, retries, circuit breakers, graceful degradation.
- **Elastic** — it scales to load, and to zero.
- **Automatable** — declarative config, GitOps, self-healing.
- **Loosely coupled** — contracts not calls, async where it fits.

These six are the rubric for the rest of the book. Hold each design decision up
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
is what actually delivers independent deployability: the contract *is* the
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
provides for free.

{% include excalidraw.html
   file="01-twelve-factor-ownership"
   alt="Two columns: the factors you still write per service (config from the environment, stateless processes, fast clean start and stop, logs as event streams, health and readiness probes) versus the factors the platform provides (build/release/run, concurrency and scaling, disposability, port binding, backing services, retries and timeouts)"
   caption="Figure 1.3 — The twelve factors, split by who owns them" %}

The left column is your job; the right column is the platform's. The whole point
of a cloud-native service is to do the left column well and trust the right
column — which is exactly what the code below does.

## Twelve factors, mapped to our system

Grouped by what each factor *asks of you*, the twelve land on concrete choices in
the running example — and most resolve to a platform default rather than code you
write.

{% include excalidraw.html
   file="01-factors-mapped"
   alt="Five rows mapping groups of factors to the system: build and ship becomes built once, run anywhere (one repo, Poetry, one image per release); configure becomes config from the environment (pydantic-settings, per-profile, secrets injected); run on the platform becomes disposable, stateless, scaled (KEDA scale-out and to-zero, fast start/stop, behind Istio); attach resources becomes backing services as swappable URLs (Postgres, Kafka via Strimzi, Apicurio, never in-process); operate becomes signals and admin off the hot path (OpenTelemetry to LGTM, admin as Jobs and CronJobs). Each row carries a section reference."
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

Two factors dominate the code you actually write: **config from the environment**
(factor III) and **health and readiness probes** the platform calls. Here it is
in each stack — pick your tab.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
# application.yml — config from the environment (factor III)
spring:
  application:
    name: order-service                           # surfaces in metrics, traces
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP}         # injected at runtime

management:                                       # Actuator publishes probes
  endpoint:
    health:
      probes:
        enabled: true                             # /actuator/health/liveness
  health:                                         #     /actuator/health/readiness
    livenessstate.enabled: true
    readinessstate.enabled: true

// Custom readiness contributor — auto-discovered as a HealthIndicator bean
@Component
public class DatabaseReady implements HealthIndicator {
    private final JdbcTemplate jdbc;
    public DatabaseReady(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @Override public Health health() {
        try { jdbc.queryForObject("SELECT 1", Integer.class); return Health.up().build(); }
        catch (DataAccessException e)            { return Health.down(e).build(); }
    }
}
```

```java
# application.properties — config from the environment (factor III)
quarkus.application.name=order-service
quarkus.application.version=1.4.0
%prod.kafka.bootstrap.servers=${KAFKA_BOOTSTRAP}

// SmallRye Health publishes the probes Kubernetes calls
@Liveness                                    // /q/health/live — process is up
public class Alive implements HealthCheck {
    public HealthCheckResponse call() { return HealthCheckResponse.up("alive"); }
}

@Readiness                                   // /q/health/ready — deps reachable
public class Ready implements HealthCheck {
    @Inject PgPool db;                       // injected datastore client
    public HealthCheckResponse call() {
        return db.query("SELECT 1") != null ? up("ready") : down("ready"); }
}
```

```csharp
// Program.cs — minimal hosting, env-driven config (factor III)
var builder = WebApplication.CreateBuilder(args);
builder.Configuration.AddEnvironmentVariables();   // overrides appsettings.json

// Health checks: liveness vs readiness, just like the WCF heartbeat —
// only Kubernetes calls them now, not your monitoring server.
builder.Services.AddHealthChecks()
    .AddCheck("self", () => HealthCheckResult.Healthy(), tags: new[] { "live" })
    .AddNpgSql(builder.Configuration.GetConnectionString("Db")!,
               name: "db", tags: new[] { "ready" });        // AspNetCore.HealthChecks

var app = builder.Build();

// The cloud-native equivalent of IIS "Ping" + ARR health probes,
// but baked into the app, not the host.
app.MapHealthChecks("/healthz/live",  new() { Predicate = c => c.Tags.Contains("live")  });
app.MapHealthChecks("/healthz/ready", new() { Predicate = c => c.Tags.Contains("ready") });

app.Run();
```

```python
# pyproject.toml (Poetry) pins everything; config comes from the environment
from fastapi import FastAPI
from pydantic_settings import BaseSettings

class Settings(BaseSettings):           # config from env — factor III
    database_url: str
    kafka_bootstrap: str

settings = Settings()
app = FastAPI(title="order-service", version="1.4.0")

@app.get("/healthz")                     # liveness — process is up
def healthz(): return {"status": "ok"}

@app.get("/readyz")                      # readiness — deps are reachable
async def readyz():
    await check_db(); await check_kafka()
    return {"status": "ready"}
```

```cpp
{% raw %}// conanfile.py pins everything; config comes from the environment
#include <drogon/drogon.h>
#include <cstdlib>

struct Settings {                          // config from env — factor III
  std::string database_url    = std::getenv("DATABASE_URL");
  std::string kafka_bootstrap = std::getenv("KAFKA_BOOTSTRAP");
};

const Settings settings;                   // parsed once, immutable
constinit std::string_view kVersion = "1.4.0";

int main() {
  auto& app = drogon::app();
  app.registerHandler("/healthz", [](auto&&, auto&& cb){   // liveness — process is up
    cb(drogon::HttpResponse::newHttpJsonResponse({{"status","ok"}}));
  });
  app.registerHandler("/readyz", [](auto&&, auto&& cb){    // readiness — deps reachable
    check_db(); check_kafka();
    cb(drogon::HttpResponse::newHttpJsonResponse({{"status","ready"}}));
  });
  app.addListener("0.0.0.0", 8080).run();  // factor VII · port binding
}{% endraw %}
```

```go
// main.go — config from the environment (factor III); two probes, not one
type Settings struct {
	DatabaseURL    string // DATABASE_URL
	KafkaBootstrap string // KAFKA_BOOTSTRAP
}

func load() Settings { // config from env, never a baked-in file
	return Settings{
		DatabaseURL:    os.Getenv("DATABASE_URL"),
		KafkaBootstrap: os.Getenv("KAFKA_BOOTSTRAP"),
	}
}

func main() {
	cfg := load()
	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"}) // liveness
	})
	mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
		// readiness drains traffic on failure; it never restarts the pod
		if err := errors.Join(checkDB(r.Context()), checkKafka(r.Context())); err != nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "down"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ready"})
	})

	slog.Info("starting", "version", "1.4.0", "kafka", cfg.KafkaBootstrap)
	_ = http.ListenAndServe(":8080", mux) // factor VII · port binding
}
```

### How the code works

The same two ideas appear in every tab:

1. **Config comes from the environment, never from a baked-in file.** Spring and
   Quarkus read `${KAFKA_BOOTSTRAP}` from the environment, .NET calls
   `AddEnvironmentVariables()` so env vars override `appsettings.json`, Python
   binds a `BaseSettings` class to env vars, and C++ reads `std::getenv`. One
   image, many environments — factor III, and the thing that lets the same
   artifact run in dev, staging, and production unchanged.
2. **Two probes, not one.** *Liveness* answers "is the process up?" — if it fails,
   the platform restarts the pod. *Readiness* answers "are my dependencies
   reachable?" — if it fails, the platform stops routing traffic to this instance
   but leaves it running. Conflating the two is a classic mistake: a readiness
   blip should drain traffic, not trigger a restart loop. The frameworks differ
   in surface — Actuator endpoints, SmallRye `@Liveness`/`@Readiness`, ASP.NET
   tag-filtered health checks, plain handlers — but Kubernetes calls them the same
   way.

Notice what *isn't* here: no retry logic, no scaling code, no port-binding
plumbing. Those are the right column of Figure 1.3 — the platform's job.

### Cross-check it yourself

With the service running, the probes are just HTTP. Hit liveness and readiness
with `curl` and confirm liveness returns healthy while the database is down but
readiness does *not* — that difference is the whole point. `curl -i
localhost:8080/readyz` should flip from ready to not-ready as you stop and start
the database, without the process ever restarting.

The code is in `examples/01-cloud-native-principles/`. The run script there builds
and runs it; its `README.md` covers what it does and how to drive it.

---
*Verification status: unverified — code transcribed from the source decks, not yet
run against a live platform. The `examples/01-cloud-native-principles/` runner is
what moves it to verified.*
