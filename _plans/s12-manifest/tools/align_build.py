#!/usr/bin/env python3
"""S12 example alignment: deck edit files for the readiness, shutdown and write-back fixes.

    align_build.py [--check]

Writes lgtm-presentation/edits/<deck>.fixN.json (the next free fix number of each language deck at
the time of the round) so that the deck slides, captions and notes follow
examples/01-cloud-native-principles (readiness answers 503 when the database is down; the Spring,
Quarkus and .NET probes are hand-written handlers), examples/21-graceful-shutdown (one SIGTERM:
readiness 503, DRAIN_DELAY_SECONDS, stop accepting, in-flight drain bounded at 20 s, cleanup, exit 0),
examples/25-caching (write-back answers 202 on /write-back/metrics/{id}; upsert; bounded retry with
a metric:attempts hash, a metric:failed set and backoff) and examples/04-data/quarkus (plain JDBC
outbox insert). Every code box is checked against 95 columns and the line capacity of its box
(probed on the committed decks). --check only runs the checks. The same line lists are the source
of the site codetabs (align_site.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EDITS = REPO / "lgtm-presentation" / "edits"
MAX_COLS = 95

OUT = {
    "Python": "Designing-Cloud-Native-APIs-Python.fix4.json",
    "Go": "Designing-Cloud-Native-APIs-Go.fix3.json",
    "Cpp": "Designing-Cloud-Native-APIs-Cpp.fix3.json",
    "Quarkus": "Designing-Cloud-Native-APIs-Quarkus.fix4.json",
    "Spring": "Designing-Cloud-Native-APIs-Spring.fix5.json",
    "DotNet": "Designing-Cloud-Native-APIs-DotNet.fix5.json",
}

# line capacity of each code box (deck_edit.box_capacity at the box's current font, probed on the
# committed decks); set_code also allows max(22, current line count)
CAP = {
    ("Python", 419): 21, ("Python", 476): 25, ("Python", 500): 24,
    ("Go", 269): 21, ("Go", 419): 19, ("Go", 476): 20, ("Go", 500): 21,
    ("Cpp", 269): 23, ("Cpp", 419): 23, ("Cpp", 476): 24, ("Cpp", 500): 23,
    ("Quarkus", 269): 18, ("Quarkus", 287): 19, ("Quarkus", 419): 20, ("Quarkus", 476): 25,
    ("Quarkus", 500): 24,
    ("Spring", 269): 25, ("Spring", 423): 25, ("Spring", 480): 24, ("Spring", 504): 25,
    ("DotNet", 270): 21, ("DotNet", 427): 24, ("DotNet", 490): 25, ("DotNet", 514): 25,
}

WB_CAPTION_OLD = ("The dirty set is the key idea — it tells the flusher what to drain. "
                  "Failed batches go back on the set for retry.")
WB_CAPTION_NEW = ("A write answers 202 Accepted. A failed flush re-queues its ids with backoff; "
                  "after five attempts an id is parked on metric:failed.")
PROBE_READS = ("The probe reads the status code, not the body: Kubernetes treats any answer from 200 "
               "to 399 as ready.")

# ------------------------------------------------------------------ code (shared with the site)

CODE = {}

# --- Example 01: readiness -------------------------------------------------------------------

CODE["Go", 269] = [
    "// main.go (excerpt), examples/01-cloud-native-principles/go: config from env, two probes",
    "func (s *Server) handleHealthz(w http.ResponseWriter, r *http.Request) {",
    "   w.Header().Set(\"Content-Type\", \"application/json\")",
    "   json.NewEncoder(w).Encode(HealthResponse{Status: \"ok\"}) // liveness: the process is up",
    "}",
    "func (s *Server) handleReadyz(w http.ResponseWriter, r *http.Request) {",
    "   ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)",
    "   defer cancel()",
    "   w.Header().Set(\"Content-Type\", \"application/json\")",
    "   if err := s.pool.Ping(ctx); err != nil { // readiness: the database answers",
    "      w.WriteHeader(http.StatusServiceUnavailable) // 503: out of rotation, not restarted",
    "      json.NewEncoder(w).Encode(ReadinessResponse{Status: \"down\",",
    "         Checks: map[string]string{\"database\": \"unreachable\"}})",
    "      return",
    "   }",
    "   json.NewEncoder(w).Encode(ReadinessResponse{Status: \"ready\",",
    "      Checks: map[string]string{\"database\": \"ok\"}})",
    "}",
    "// main(): SERVICE_VERSION and DATABASE_URL come from the environment (factor III); the mux",
    "// serves /, /healthz, /readyz and /orders on :8080 (factor VII, port binding)",
]

CODE["Cpp", 269] = [
    "// main.cpp (excerpt), examples/01-cloud-native-principles/cpp; conan.lock pins every library",
    "using Callback = std::function<void(const HttpResponsePtr&)>;",
    "const char* env(const char* name, const char* fallback) {   // config from env, factor III",
    "  const char* v = std::getenv(name);  return v ? v : fallback;   // unset: the default",
    "}",
    "int main() {",
    "  g_version = env(\"SERVICE_VERSION\", \"1.0.0\");",
    "  g_pool = std::make_unique<cndp::PgPool>(",
    "      env(\"PG_CONNINFO\", \"postgresql://appuser:apppass@postgres:5432/appdb\"),",
    "      std::atoi(env(\"PG_POOL_SIZE\", \"4\")));",
    "  app().registerHandler(\"/healthz\", [](const HttpRequestPtr&, Callback&& cb) {",
    "    Json::Value j;  j[\"status\"] = \"ok\";  cb(HttpResponse::newHttpJsonResponse(j));  // liveness",
    "  }, {Get});",
    "  app().registerHandler(\"/readyz\", [](const HttpRequestPtr&, Callback&& cb) {",
    "    const bool db_ok = db_ready();             // SELECT 1 via the libpq pool (retry elided)",
    "    Json::Value j;  j[\"status\"] = db_ok ? \"ready\" : \"down\";",
    "    auto resp = HttpResponse::newHttpJsonResponse(j);",
    "    if (!db_ok) resp->setStatusCode(k503ServiceUnavailable);   // down: out of rotation",
    "    cb(resp);",
    "  }, {Get});",
    "  app().addListener(\"0.0.0.0\", 8080).run();    // factor VII: port binding",
    "}",
]

CODE["Quarkus", 269] = [
    "// HealthResource.java (excerpt), examples/01-cloud-native-principles/quarkus",
    "@Path(\"/\") @Produces(MediaType.APPLICATION_JSON)",
    "public class HealthResource {",
    "    @ConfigProperty(name = \"quarkus.datasource.jdbc.url\") String jdbcUrl;  // env, factor III",
    "    @GET @Path(\"healthz\")                    // liveness: the process is up",
    "    public Map<String, String> healthz() { return Map.of(\"status\", \"ok\"); }",
    "    @GET @Path(\"readyz\")                     // readiness: SELECT 1 (one retry elided)",
    "    public Response readyz() {",
    "        try (var conn = DriverManager.getConnection(jdbcUrl, dbUser, dbPass);",
    "             var rs = conn.createStatement().executeQuery(\"SELECT 1\")) {",
    "            return Response.ok(Map.of(\"status\", \"ready\",",
    "                    \"checks\", Map.of(\"database\", \"ok\"))).build();",
    "        } catch (Exception e) {              // down: 503, out of rotation",
    "            return Response.status(Response.Status.SERVICE_UNAVAILABLE)",
    "                .entity(Map.of(\"status\", \"down\", \"checks\", Map.of(\"database\", \"unreachable\")))",
    "                .build();",
    "        }",
    "    }",
]
# 18 lines; the closing brace of the class is cut (excerpt)

CODE["Spring", 269] = [
    "// HealthController.java (excerpt), examples/01-cloud-native-principles/spring-boot",
    "// config from env (factor III): SPRING_DATASOURCE_URL, SERVICE_VERSION -> service.version",
    "@RestController",
    "public class HealthController {",
    "    private final DataSource dataSource;",
    "    @Value(\"${service.version}\")",
    "    private String serviceVersion;",
    "    public HealthController(DataSource dataSource) { this.dataSource = dataSource; }",
    "    @GetMapping(\"/healthz\")                           // liveness: the process is up",
    "    public Map<String, String> healthz() { return Map.of(\"status\", \"ok\"); }",
    "    @GetMapping(\"/readyz\")                            // readiness: SELECT 1 on the pool",
    "    public ResponseEntity<Map<String, Object>> readyz() {",
    "        try (var conn = dataSource.getConnection()) {",
    "            conn.createStatement().executeQuery(\"SELECT 1\").close();",
    "        } catch (Exception e) {                       // down: 503, the pod leaves the Service",
    "            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)",
    "                .body(Map.of(\"status\", \"down\", \"checks\", Map.of(\"database\", \"unreachable\")));",
    "        }",
    "        return ResponseEntity.ok(Map.of(\"status\", \"ready\",",
    "                \"checks\", Map.of(\"database\", \"ok\")));",
    "    }",
    "}",
]

CODE["DotNet", 270] = [
    "// Program.cs (excerpt), examples/01-cloud-native-principles/dotnet",
    "var builder = WebApplication.CreateBuilder(args);",
    "// ... ConnectionStrings__Default from the environment (factor III) -> NpgsqlDataSource",
    "var app = builder.Build();",
    "app.MapGet(\"/healthz\", () => new { status = \"ok\" });          // liveness: the process is up",
    "app.MapGet(\"/readyz\", async (NpgsqlDataSource db) =>          // readiness: SELECT 1",
    "{",
    "    try",
    "    {",
    "        await using var conn = await db.OpenConnectionAsync();",
    "        await using var cmd = conn.CreateCommand();",
    "        cmd.CommandText = \"SELECT 1\";",
    "        await cmd.ExecuteScalarAsync();",
    "        return Results.Ok(new { status = \"ready\", checks = new { database = \"ok\" } });",
    "    }",
    "    catch                                                     // down: 503, out of rotation",
    "    {",
    "        return Results.Json(new { status = \"down\", checks = new { database = \"unreachable\" } },",
    "            statusCode: StatusCodes.Status503ServiceUnavailable);",
    "    }",
    "});",
]

# --- Example 21: one SIGTERM ------------------------------------------------------------------

CODE["Python", 419] = [
    "# main.py (excerpt), examples/21-graceful-shutdown/python",
    "import asyncio, signal          # (contextlib and fastapi imports elided)",
    "DRAIN_DELAY_SECONDS = 5        # lets endpoint removal propagate (the preStop sleep)",
    "shutting_down, uvicorn_sigterm, loop = False, None, None",
    "def handle_sigterm(signum, frame):",
    "    global shutting_down",
    "    if shutting_down: return     # one SIGTERM drives the whole drain",
    "    shutting_down = True         # fail readiness now, keep serving for the delay",
    "    loop.call_soon_threadsafe(loop.call_later, DRAIN_DELAY_SECONDS,",
    "                              uvicorn_sigterm, signum, frame)   # then uvicorn drains HTTP",
    "@asynccontextmanager",
    "async def lifespan(app):",
    "    global uvicorn_sigterm, loop # uvicorn's handler is already installed: chain to it",
    "    loop = asyncio.get_running_loop()",
    "    uvicorn_sigterm = signal.signal(signal.SIGTERM, handle_sigterm)",
    "    yield                        # --- runs after uvicorn has drained HTTP ---",
    "    await db_pool.close()        # close pools, flush, release resources",
    "app = FastAPI(lifespan=lifespan)",
    "@app.get(\"/readyz\")",
    "async def readyz(): return JSONResponse({}, 503 if shutting_down else 200)",
    "# run: uvicorn main:app --timeout-graceful-shutdown 20   # bounds the HTTP drain",
]

CODE["Go", 419] = [
    "// main.go (excerpt), examples/21-graceful-shutdown/go: one SIGTERM drives the drain",
    "const shutdownTimeout = 20 * time.Second // drain delay + this stays under the 30s grace",
    "func main() {",
    "   // ... pgx pool, s := &server{pool: pool}; GET /readyz answers 503 once s.shuttingDown",
    "   httpServer := &http.Server{Addr: \":8080\", Handler: mux}",
    "   ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)",
    "   defer stop()",
    "   go httpServer.ListenAndServe()",
    "   <-ctx.Done()               // 1. the single SIGTERM",
    "   stop()                     //    a later signal terminates at once",
    "   s.shuttingDown.Store(true) //    readiness fails first, the server keeps serving",
    "   time.Sleep(drainDelay())   // 2. DRAIN_DELAY_SECONDS (5s): endpoints update",
    "   shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)",
    "   defer cancel()             // 3. stop accepting, finish in-flight requests",
    "   if err := httpServer.Shutdown(shutdownCtx); err != nil {",
    "      slog.Error(\"shutdown incomplete\", \"err\", err, \"in_flight\", s.inFlight.Load())",
    "   }",
    "}                             // 4. deferred pool.Close(), exit 0",
]

CODE["Cpp", 419] = [
    "// order-service (excerpt), examples/21-graceful-shutdown/cpp: one SIGTERM drives the drain",
    "std::atomic<bool> g_shutting_down{false};     // /readyz answers 503 once it is set",
    "std::atomic<int>  g_in_flight{0};             // RAII InFlightGuard: one per request",
    "extern \"C\" void sigterm_handler(int) {        // async-signal-safe: one atomic store",
    "  g_shutting_down.store(true, std::memory_order_release);",
    "}",
    "void shutdown_watcher() {                     // outside signal context",
    "  while (!g_shutting_down.load(std::memory_order_acquire))",
    "    std::this_thread::sleep_for(50ms);        // (also returns on g_watcher_stop)",
    "  const int delay = std::atoi(env(\"DRAIN_DELAY_SECONDS\", \"5\"));",
    "  std::this_thread::sleep_for(std::chrono::seconds(delay));    // endpoints update",
    "  const auto deadline = std::chrono::steady_clock::now() + 20s; // bounded in-flight wait",
    "  while (g_in_flight.load() > 0 && std::chrono::steady_clock::now() < deadline)",
    "    std::this_thread::sleep_for(100ms);",
    "  app().quit();                               // stop the listeners: run() returns",
    "}",
    "int main() {",
    "  app().registerBeginningAdvice([] { std::signal(SIGTERM, sigterm_handler); });  // after init",
    "  std::thread watcher(shutdown_watcher);      // ... handlers, addListener(\"0.0.0.0\", 8080)",
    "  app().run();  g_watcher_stop.store(true);  watcher.join();",
    "  g_pool.reset();                             // close the database connections; exit 0",
    "}",
]

CODE["Quarkus", 419] = [
    "// SignalHandler.java (excerpt), examples/21-graceful-shutdown/quarkus",
    "// application.properties: quarkus.shutdown.timeout=20s (bounds the in-flight wait)",
    "@ApplicationScoped",
    "public class SignalHandler {",
    "    @Inject ShutdownState shutdownState;     // GET /readyz answers 503 once it is set",
    "    void onStart(@Observes StartupEvent ev) { // replaces the JVM's default SIGTERM handler",
    "        Signal.handle(new Signal(\"TERM\"), signal -> {",
    "            if (!shutdownState.markShuttingDown()) return;  // one SIGTERM drives the drain",
    "            long delay = drainDelaySeconds();               // DRAIN_DELAY_SECONDS, default 5",
    "            new Thread(() -> {",
    "                try { Thread.sleep(delay * 1000); }         // keep serving: endpoints update",
    "                catch (InterruptedException e) { Thread.currentThread().interrupt(); }",
    "                Quarkus.asyncExit(0);   // stop accepting, finish in-flight, close the pool",
    "            }, \"drain\").start();",
    "        });",
    "    }",
    "}",
]

CODE["Spring", 423] = [
    "// OrderServiceApplication.java (excerpt), examples/21-graceful-shutdown/spring-boot",
    "// application.properties: server.shutdown=graceful",
    "//                         spring.lifecycle.timeout-per-shutdown-phase=20s",
    "@SpringBootApplication",
    "public class OrderServiceApplication {",
    "    public static void main(String[] args) {",
    "        // registered before Spring starts: replaces the JVM's default SIGTERM handler",
    "        Signal.handle(new Signal(\"TERM\"), signal -> {",
    "            ShutdownState state = ShutdownState.getInstance();  // GET /readyz reads it: 503",
    "            if (!state.markShuttingDown()) return;   // one SIGTERM drives the drain",
    "            long delay = drainDelaySeconds();        // DRAIN_DELAY_SECONDS, default 5",
    "            new Thread(() -> {",
    "                try { Thread.sleep(delay * 1000); }  // keep serving: endpoints update",
    "                catch (InterruptedException e) { Thread.currentThread().interrupt(); }",
    "                System.exit(0);  // shutdown hook: stop accepting, finish in-flight, close pool",
    "            }, \"drain\").start();",
    "        });",
    "        SpringApplication.run(OrderServiceApplication.class, args);",
    "    }",
    "}",
    "// Kafka consumers, the scheduler and WebSockets drain in a ContextClosedEvent listener.",
]

CODE["DotNet", 427] = [
    "// Program.cs (excerpt), examples/21-graceful-shutdown/dotnet: one SIGTERM drives the drain",
    "builder.Services.AddSingleton<IHostLifetime, ManualLifetime>();  // not ConsoleLifetime",
    "builder.Services.Configure<HostOptions>(o => o.ShutdownTimeout = TimeSpan.FromSeconds(20));",
    "var app = builder.Build();",
    "var shuttingDown = false;                 // GET /readyz answers 503 once it is set",
    "var drainDelay = int.TryParse(Environment.GetEnvironmentVariable(\"DRAIN_DELAY_SECONDS\"),",
    "    out var d) && d >= 0 ? d : 5;",
    "PosixSignalRegistration.Create(PosixSignal.SIGTERM, ctx =>",
    "{",
    "    ctx.Cancel = true;                    // the host does not stop at once",
    "    if (shuttingDown) return;             // already draining",
    "    shuttingDown = true;                  // 1. readiness fails first",
    "    _ = Task.Run(async () =>",
    "    {",
    "        await Task.Delay(TimeSpan.FromSeconds(drainDelay));  // 2. serve on: endpoints update",
    "        app.Lifetime.StopApplication();   // 3. Kestrel stops accepting, finishes in-flight",
    "    });",
    "});",
    "app.Lifetime.ApplicationStopped.Register(() => dataSource.Dispose());   // 4. close the pool",
    "// ... MapGet /healthz (always 200), /readyz, /orders; app.Run();",
    "// ManualLifetime : IHostLifetime: WaitForStartAsync and StopAsync return Task.CompletedTask",
]

# --- Appendix M recaps of Example 21 ------------------------------------------------------------

CODE["Python", 500] = [
    "# main.py (excerpt), examples/21-graceful-shutdown/python: one SIGTERM, four steps",
    "def handle_sigterm(signum, frame):            # installed in the lifespan, chained to uvicorn's",
    "    global shutting_down",
    "    if shutting_down: return                  # already draining",
    "    shutting_down = True                      # 1. /readyz answers 503: the LB stops routing",
    "    loop.call_soon_threadsafe(loop.call_later, DRAIN_DELAY_SECONDS,   # 2. keep serving 5 s",
    "                              stop_server, signum, frame)",
    "def stop_server(signum, frame):               # 3. uvicorn stops accepting, finishes in-flight",
    "    uvicorn_sigterm(signum, frame)            #    (--timeout-graceful-shutdown 20)",
    "@asynccontextmanager",
    "async def lifespan(app: FastAPI):",
    "    global uvicorn_sigterm, loop",
    "    loop = asyncio.get_running_loop()",
    "    uvicorn_sigterm = signal.signal(signal.SIGTERM, handle_sigterm)",
    "    yield                                     # ---------- app serves ----------",
    "    await db_pool.close()                     # 4. close resources, exit 0",
    "@app.get(\"/readyz\")",
    "async def readyz():",
    "    if shutting_down:                         # liveness (/healthz) stays 200",
    "        return JSONResponse({\"ready\": False, \"reason\": \"shutting down\"}, 503)",
    "    return {\"ready\": True}                    # (the example also pings Postgres here)",
    "# K8s: terminationGracePeriodSeconds: 30 >= 5 s delay + 20 s drain + buffer  (App. H)",
]

CODE["Go", 500] = [
    "// main.go (excerpt), examples/21-graceful-shutdown/go: shutdown is a failure mode",
    "func (s *server) readyz(w http.ResponseWriter, r *http.Request) {",
    "   if s.shuttingDown.Load() {            // liveness (/healthz) stays 200",
    "      w.WriteHeader(http.StatusServiceUnavailable)",
    "      json.NewEncoder(w).Encode(map[string]any{\"ready\": false, \"reason\": \"shutting down\"})",
    "      return",
    "   }",
    "   // ... ping the pool: 503 \"db unreachable\", else {\"ready\": true}",
    "}",
    "func main() {",
    "   // ... pool, mux, httpServer; ctx, stop := signal.NotifyContext(..., SIGTERM, SIGINT)",
    "   <-ctx.Done()                          // SIGTERM: terminationGracePeriod has started",
    "   stop()",
    "   s.shuttingDown.Store(true)            // 1. readiness starts failing",
    "   time.Sleep(drainDelay())              // 2. let the LB stop routing to us (5s)",
    "   shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)",
    "   defer cancel()",
    "   httpServer.Shutdown(shutdownCtx)      // 3. finish in-flight work (20s budget)",
    "}                                        // 4. deferred pool.Close(), exit 0",
]

CODE["Cpp", 500] = [
    "// Recap of Appendix H in the failure-mode context: shutdown is a failure mode.",
    "// A pod that dies mid-request causes 5xx; a pod that drains cleanly does not.",
    "std::atomic<bool> g_shutting_down{false};         // /readyz answers 503 once it is set",
    "std::atomic<int>  g_in_flight{0};                 // InFlightGuard per request",
    "extern \"C\" void sigterm_handler(int) {            // async-signal-safe: one atomic store",
    "  g_shutting_down.store(true, std::memory_order_release);",
    "}",
    "void shutdown_watcher() {                         // one SIGTERM drives the rest",
    "  // ... wait for the flag, sleep DRAIN_DELAY_SECONDS (5), wait for g_in_flight == 0 (20 s)",
    "  app().quit();                                   // stop the listeners: run() returns",
    "}",
    "int main() {",
    "  app().registerBeginningAdvice([] { std::signal(SIGTERM, sigterm_handler); });",
    "  std::thread watcher(shutdown_watcher);",
    "  app().addListener(\"0.0.0.0\", 8080).run();",
    "  watcher.join();",
    "  g_pool.reset();                                 // close the pool, then exit 0",
    "}",
    "// K8s pod spec: terminationGracePeriodSeconds: 30 (>= 5 s delay + 20 s drain + buffer)",
]

CODE["Quarkus", 500] = [
    "// OrderResource + SignalHandler (excerpt), examples/21-graceful-shutdown/quarkus",
    "@GET @Path(\"readyz\")                                 // OrderResource",
    "public Response readyz() {",
    "    if (shutdownState.isShuttingDown())              // 1. readiness flips: 503",
    "        return Response.status(503)",
    "                .entity(Map.of(\"ready\", false, \"reason\", \"shutting down\")).build();",
    "    // ... SELECT 1 on the datasource: 200 {\"ready\": true}, or 503 \"db unreachable\"",
    "}",
    "@GET @Path(\"healthz\")                                // liveness stays 200 while draining",
    "public Map<String, String> healthz() { return Map.of(\"status\", \"ok\"); }",
    "void onStart(@Observes StartupEvent ev) {            // SignalHandler",
    "    Signal.handle(new Signal(\"TERM\"), signal -> {    // one SIGTERM drives the drain",
    "        if (!shutdownState.markShuttingDown()) return;",
    "        new Thread(() -> {",
    "            try { Thread.sleep(drainDelaySeconds() * 1000); }   // 2. the LB stops routing",
    "            catch (InterruptedException e) { Thread.currentThread().interrupt(); }",
    "            Quarkus.asyncExit(0);   // 3. drain in-flight HTTP (quarkus.shutdown.timeout=20s)",
    "        }, \"drain\").start();                          // 4. Quarkus closes pools, exit 0",
    "    });",
    "}",
]

CODE["Spring", 504] = [
    "// excerpt, examples/21-graceful-shutdown/spring-boot: one SIGTERM drives the drain",
    "# application.properties: server.shutdown=graceful, timeout-per-shutdown-phase=20s",
    "Signal.handle(new Signal(\"TERM\"), signal -> {      // registered before SpringApplication.run",
    "    ShutdownState state = ShutdownState.getInstance();",
    "    if (!state.markShuttingDown()) return;          // 1. readiness flips: /readyz answers 503",
    "    new Thread(() -> {",
    "        try { Thread.sleep(drainDelaySeconds() * 1000); }   // 2. the LB stops routing (5 s)",
    "        catch (InterruptedException e) { Thread.currentThread().interrupt(); }",
    "        System.exit(0);              // 3. graceful shutdown drains in-flight HTTP (20 s)",
    "    }, \"drain\").start();                            // 4. the context closes the pool, exit 0",
    "});",
    "@GetMapping(\"/readyz\")                              // OrderController",
    "public ResponseEntity<Map<String, Object>> readyz() {",
    "    if (shutdownState.isShuttingDown())",
    "        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)",
    "                .body(Map.of(\"ready\", false, \"reason\", \"shutting down\"));",
    "    // ... SELECT 1: 200 {\"ready\": true}, or 503 \"db unreachable\"; /healthz stays 200",
    "}",
]

CODE["DotNet", 514] = [
    "// OrderService/Program.cs (excerpt, example 21): one SIGTERM drives the drain",
    "var shuttingDown = false;",
    "PosixSignalRegistration.Create(PosixSignal.SIGTERM, ctx =>",
    "{",
    "    ctx.Cancel = true;           // the app drains; the host does not stop at once",
    "    if (shuttingDown) return;    // already draining",
    "    shuttingDown = true;         // 1. readiness → 503: the Service stops routing",
    "    _ = Task.Run(async () =>",
    "    {",
    "        await Task.Delay(TimeSpan.FromSeconds(drainDelay));   // 2. endpoints update (5 s)",
    "        app.Lifetime.StopApplication();  // 3. Kestrel drains in-flight (ShutdownTimeout 20 s)",
    "    });",
    "});",
    "app.MapGet(\"/healthz\", () => new { status = \"ok\" });        // liveness stays 200",
    "app.MapGet(\"/readyz\", () => shuttingDown                    // (the example also pings",
    "    ? Results.Json(new { ready = false, reason = \"shutting down\" }, statusCode: 503)",
    "    : Results.Ok(new { ready = true }));                    //  Postgres here)",
    "app.MapPost(\"/orders\", async (HttpContext ctx, NpgsqlDataSource db) =>",
    "{",
    "    if (shuttingDown) return Results.Json(new { error = \"shutting down\" }, statusCode: 503);",
    "    // ... in-flight requests finish before the host stops; 4. the pool is disposed, exit 0",
    "});",
]

# --- Example 25: write-back -----------------------------------------------------------------------

CODE["Python", 476] = [
    "MAX_FLUSH_ATTEMPTS, MAX_FLUSH_BACKOFF = 5, 8   # excerpt, examples/25-caching/python",
    "async def flusher():                                  # 2. drain the dirty set to the DB",
    "    failures = 0",
    "    while True:                                       # back off after a failed flush",
    "        await asyncio.sleep(min(FLUSH_PERIOD * 2**failures, MAX_FLUSH_BACKOFF))",
    "        ids = await cache.spop(\"metric:dirty\", FLUSH_BATCH)  # cache: decode_responses=True",
    "        if not ids: continue",
    "        rows = [(m, json.dumps(d)) for m in ids if (d := await cache.hgetall(f\"metric:{m}\"))]",
    "        try:                                          # upsert: an id flushed twice is one row",
    "            async with pool.acquire() as conn:",
    "                await conn.executemany(\"INSERT INTO metrics (id, payload) VALUES ($1, $2) \"",
    "                    \"ON CONFLICT (id) DO UPDATE SET payload = $2, ts = NOW()\", rows)",
    "            failures = 0",
    "        except Exception:                             # 3. re-queue, bounded by attempts",
    "            log.exception(\"flusher error: flush failed\"); failures += 1",
    "            for mid in ids:",
    "                n = await cache.hincrby(\"metric:attempts\", mid, 1)",
    "                key = \"metric:failed\" if n >= MAX_FLUSH_ATTEMPTS else \"metric:dirty\"",
    "                await cache.sadd(key, mid)              # parked after 5 tries, never dropped",
    "@app.put(\"/write-back/metrics/{mid}\")",
    "async def write_back_write(mid: str, body: MetricIn):",
    "    mapping = {\"value\": str(body.value), \"tags\": json.dumps(body.tags)}",
    "    await cache.hset(f\"metric:{mid}\", mapping=mapping)   # 1. cache only",
    "    await cache.sadd(\"metric:dirty\", mid)                # mark for flush",
    "    return JSONResponse(status_code=202, content={\"ok\": True, \"action\": \"cached-for-flush\"})",
]

CODE["Go", 476] = [
    "// main.go (excerpt), examples/25-caching/go: write-back",
    "func handleWriteBackPut(w http.ResponseWriter, r *http.Request) {",
    "   key := \"metric:\" + r.PathValue(\"id\")       // body decoded into parsed, id added: data",
    "   safeSet(r.Context(), key, string(data), 0) // 1. cache only, no TTL",
    "   rdb.SAdd(r.Context(), \"metric:dirty\", key) //    mark for flush",
    "   writeJSON(w, 202, parsed)                  // 202: queued, not yet durable",
    "}",
    "func flusher(ctx context.Context) {           // 2. drain the dirty set to the DB",
    "   failures := 0",
    "   for {",
    "      wait := flushPeriod                     // 1s, doubling to 8s after failures",
    "      if failures > 0 { wait = min(flushPeriod<<failures, maxFlushBackoff) }",
    "      select { case <-ctx.Done(): return; case <-time.After(wait): }",
    "      members, err := rdb.SPopN(ctx, \"metric:dirty\", flushBatch).Result()",
    "      // ... skip on err or none; upsert each key (ON CONFLICT (id) DO UPDATE); collect failed",
    "      if len(failed) == 0 { failures = 0; continue }",
    "      failures++",
    "      requeue(ctx, failed) // 3. HINCRBY metric:attempts; dirty again, metric:failed at 5",
    "   }",
    "}",
]

CODE["Cpp", 476] = [
    "// cache-service main.cpp (excerpt), examples/25-caching/cpp: write-back",
    "app().registerHandler(\"/write-back/metrics/{id}\",   // cache_val {id, payload}; body {ok, ...}",
    "    [](const HttpRequestPtr& req, Callback&& callback, const std::string& id) {",
    "      redis_set(\"metric:\" + id, writer.write(cache_val), std::chrono::hours(1));  // 1. cache",
    "      redis_sadd(\"writeback:dirty\", \"metric:\" + id);  // 2. mark dirty",
    "      auto resp = HttpResponse::newHttpJsonResponse(body);  resp->setStatusCode(k202Accepted);",
    "      callback(resp);                                 // 3. 202: queued, not yet durable",
    "    }, {Put});",
    "void writeback_flusher() {                          // std::thread, joined at shutdown",
    "  std::map<std::string, int> attempts;  int failures = 0;   // per-key failure count",
    "  while (!g_shutdown) {   // ... each cycle first sleeps std::min(2 << failures, 8) s",
    "    for (const auto& key : redis_smembers(\"writeback:dirty\")) {  // key -> id, cached payload",
    "      auto res = g_flush_db->exec(\"INSERT INTO metrics (id, payload) VALUES ($1, $2) \"",
    "          \"ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, ts = NOW()\",",
    "          {id, payload});",
    "      if (res && PQresultStatus(res.get()) == PGRES_COMMAND_OK) {",
    "        redis_srem(\"writeback:dirty\", key);  attempts.erase(key);  continue;  // DB has it",
    "      }                                             // failed: stays dirty, retried next cycle",
    "      if (++attempts[key] >= kMaxFlushAttempts)     // bounded: park after 5 attempts",
    "        { redis_sadd(\"writeback:failed\", key);  redis_srem(\"writeback:dirty\", key); }",
    "    }   // ... failures + 1 (at most 2) after a cycle with a failure, 0 after a clean one",
    "  }",
]
# 24 lines; the closing brace of the function is cut (excerpt)

CODE["Quarkus", 476] = [
    "// CacheResource + BackgroundTasks (excerpt), examples/25-caching/quarkus: write-back",
    "@PUT @Path(\"write-back/metrics/{mid}\")                // CacheResource",
    "public Response writeBackWrite(@PathParam(\"mid\") String mid, Map<String, Object> body) {",
    "    // ... HSET metric:<mid> {value, tags}; SADD metric:dirty <mid> (503 when Redis is down)",
    "    return Response.accepted(Map.of(\"ok\", true, \"pattern\", \"write-back\",",
    "            \"action\", \"cached-for-flush\")).build();   // 202: queued, not yet durable",
    "}",
    "@Scheduled(every = \"${cache-service.flush-period:1s}\")  // concurrent runs are skipped",
    "void flusher() {                                       // BackgroundTasks",
    "    if (System.currentTimeMillis() < nextFlushAt) return;   // backing off after a failure",
    "    Set<String> ids = cache.spop(\"metric:dirty\", FLUSH_BATCH);",
    "    if (ids == null || ids.isEmpty()) return;",
    "    List<String> failed = new ArrayList<>();",
    "    for (String mid : ids) {",
    "        try (var conn = dataSource.getConnection(); var ps = conn.prepareStatement(",
    "                \"INSERT INTO metrics (id, payload) VALUES (?, ?::jsonb) \"",
    "                + \"ON CONFLICT (id) DO UPDATE SET payload = ?::jsonb, ts = NOW()\")) {",
    "            // ... bind mid and the cached hash as JSON; executeUpdate (one row per id)",
    "            cache.hdel(\"metric:attempts\", mid);",
    "        } catch (Exception e) { failed.add(mid); }       // Log.errorf: flush failed for <mid>",
    "    }",
    "    if (failed.isEmpty()) { failures = 0; return; }",
    "    nextFlushAt = System.currentTimeMillis() + Math.min(FLUSH_PERIOD_MS << ++failures, 8000);",
    "    requeue(failed);   // HINCRBY metric:attempts; SADD metric:dirty, or metric:failed at 5",
    "}",
]

CODE["Spring", 480] = [
    "@PutMapping(\"/write-back/metrics/{mid}\")   // CacheController (excerpt)",
    "public ResponseEntity<Map<String, Object>> writeBackWrite(",
    "        @PathVariable String mid, @RequestBody Map<String, Object> body) {",
    "    // ... HSET metric:<mid> {value, tags}; SADD metric:dirty <mid> (503 when Redis is down)",
    "    return ResponseEntity.accepted().body(Map.of(\"ok\", true, \"pattern\", \"write-back\",",
    "            \"action\", \"cached-for-flush\"));               // 202: queued, not yet durable",
    "}                                   // examples/25-caching/spring-boot",
    "@Scheduled(fixedDelayString = \"${cache-service.flush-period-ms:1000}\")",
    "public void flusher() {                                // BackgroundTasks",
    "    if (System.currentTimeMillis() < nextFlushAt) return;   // backing off after a failure",
    "    Set<String> ids = cache.spop(\"metric:dirty\", FLUSH_BATCH);",
    "    if (ids == null || ids.isEmpty()) return;",
    "    List<String> failed = new ArrayList<>();",
    "    for (String mid : ids) {",
    "        try {                                     // upsert: an id flushed twice is one row",
    "            jdbc.sql(\"INSERT INTO metrics (id, payload) VALUES (?, ?::jsonb) \"",
    "                    + \"ON CONFLICT (id) DO UPDATE SET payload = ?::jsonb, ts = NOW()\")",
    "                    .param(mid).param(json).param(json).update();   // json: the cached hash",
    "            cache.hdel(\"metric:attempts\", mid);",
    "        } catch (Exception e) { failed.add(mid); }     // logged: flush failed for <mid>",
    "    }",
    "    if (failed.isEmpty()) { failures = 0; return; }",
    "    nextFlushAt = System.currentTimeMillis() + Math.min(flushPeriodMs << ++failures, 8000);",
    "    requeue(failed);   // HINCRBY metric:attempts; SADD metric:dirty, or metric:failed at 5",
]
# 24 lines; the closing brace of flusher() is cut (excerpt)

CODE["DotNet", 490] = [
    "// Program.cs (excerpt), examples/25-caching/dotnet: write-back",
    "app.MapPut(\"/write-back/metrics/{mid}\", async (string mid, HttpContext ctx) =>",
    "{",
    "    // ... HSET metric:<mid> {value, tags}; SADD metric:dirty <mid> (503 when Redis is down)",
    "    return Results.Json(new { ok = true, pattern = \"write-back\", action = \"cached-for-flush\" },",
    "        statusCode: StatusCodes.Status202Accepted);          // 202: queued, not yet durable",
    "});",
    "_ = Task.Run(async () =>                                     // the flusher, started at boot",
    "{",
    "    var failures = 0;",
    "    while (!cts.Token.IsCancellationRequested)",
    "    {",
    "        await Task.Delay(Math.Min(FlushPeriodMs << failures, MaxFlushBackoffMs), cts.Token);",
    "        var ids = await db.SetPopAsync(\"metric:dirty\", 100);     // atomic batch dequeue",
    "        if (ids.Length == 0) continue;",
    "        var failed = new List<RedisValue>();  // Upsert: HGETALL, INSERT ... ON CONFLICT (id)",
    "        foreach (var mid in ids)",
    "            try { await Upsert(mid); await db.HashDeleteAsync(\"metric:attempts\", mid); }",
    "            catch (Exception ex) { logger.LogError(ex, \"flush failed\"); failed.Add(mid); }",
    "        if (failed.Count == 0) { failures = 0; continue; }",
    "        failures = Math.Min(failures + 1, 3);                 // back off: 2 s, 4 s, 8 s",
    "        await Requeue(db, failed);   // HINCRBY metric:attempts: dirty again, failed after 5",
    "    }",
    "});",
]

# --- Example 04 (Quarkus): plain JDBC outbox ---------------------------------------------------

CODE["Quarkus", 287] = [
    "// OrderResource.java (excerpt), examples/04-data/quarkus: two rows, one transaction",
    "@POST @Transactional                       // one JTA transaction around both inserts",
    "public Response createOrder(CreateOrderRequest request) throws Exception {",
    "    String orderId = UUID.randomUUID().toString();",
    "    try (Connection conn = dataSource.getConnection();   // Agroal enlists it in the txn",
    "         PreparedStatement stmt = conn.prepareStatement(",
    "             \"INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, ?) \"",
    "             + \"RETURNING created_at\")) {",
    "        // ... bind orderId, sku, quantity, \"confirmed\"; executeQuery (the state change)",
    "        try (PreparedStatement outboxStmt = conn.prepareStatement(",
    "                \"INSERT INTO outbox (aggregate_id, event_type, payload) \"",
    "                + \"VALUES (?, ?, ?::jsonb)\")) {",
    "            // ... setString: orderId, \"order.placed\", payloadJson {order_id, sku, quantity}",
    "            outboxStmt.executeUpdate();              // same transaction: the outbox row",
    "        }",
    "        return Response.status(Response.Status.CREATED).entity(order).build();",
    "    }",
    "}",
    "// No Kafka call on the request path: Debezium tails the WAL and publishes order.placed.",
]

# ------------------------------------------------------------------ notes

N = {}

N["Python", 419] = (
    "Three moving parts, all started by one SIGTERM, the only signal Kubernetes sends before SIGKILL. "
    "First, the handler flips a readiness flag so /readyz returns 503 at once; this is the 'stop new "
    "traffic' step, and the process keeps serving while the load balancer stops routing to it. Second, "
    "after DRAIN_DELAY_SECONDS (5 s in Example 21; it plays the part of a preStop sleep) the handler "
    "chains to uvicorn's own: uvicorn installs its signal handlers before it imports the app and runs "
    "the lifespan, so a handler that replaces them without chaining means uvicorn never starts its drain "
    "and the process waits for SIGKILL. uvicorn then stops accepting and finishes in-flight HTTP; "
    "--timeout-graceful-shutdown 20 bounds that wait, so delay plus drain stays inside the 30-second "
    "grace period. Third, FastAPI's lifespan shutdown block (after the yield) runs once HTTP has "
    "drained: that is where you stop consumers (an aiokafka consumer commits offsets and leaves the "
    "group) and close pools, and the process exits 0. The order matters: readiness down, drain HTTP, "
    "then drain everything else. Pair this with the preStop hook and the termination grace period in "
    "the pod spec.")

N["Python", 500] = (
    "The shutdown sequence that prevents dropped requests during a rolling deploy, from Example 21. One "
    "SIGTERM starts it: (1) the handler flips a flag so /readyz returns 503 and Kubernetes stops sending "
    "new traffic, while /healthz stays 200; (2) the service keeps serving for DRAIN_DELAY_SECONDS so "
    "the load balancer's removal propagates; (3) the handler then hands over to uvicorn, which stops "
    "accepting and finishes in-flight requests within --timeout-graceful-shutdown; (4) the lifespan "
    "exit closes the pools and the process exits 0. The ordering matters: stop taking new work before "
    "draining existing work. This is the application half; Appendix H covers the Kubernetes half "
    "(preStop hook, terminationGracePeriodSeconds). Together they give zero-downtime rollouts.")


def wb_notes(intro, flusher, failure, tail):
    return f"{intro} {flusher} {failure} {tail}"


WB_TAIL = ("Caveats: this is only safe with Redis persistence (AOF, appendonly yes); without it a Redis "
           "crash loses unflushed writes. For data that must not be lost, use write-through. For "
           "high-throughput telemetry where losing the last second is acceptable, write-back is what "
           "lets the service scale.")

N["Python", 476] = wb_notes(
    "Write-back has more moving parts than the other patterns; the slide shows the shape of Example 25. "
    "(1) PUT /write-back/metrics/{mid} writes the metric to a Redis hash, adds the id to a 'dirty set', "
    "which tells the flusher which ids still have to reach the database, and answers 202 Accepted: the "
    "value is queued, not yet durable.",
    "(2) The flusher runs as a background asyncio task: it SPOPs up to FLUSH_BATCH dirty ids and writes "
    "them in one executemany upsert (ON CONFLICT (id) DO UPDATE), so an id flushed twice stays one row. "
    "SPOP is atomic, so two flusher instances each get a distinct subset of ids and the flusher scales "
    "out.",
    "(3) When the flush fails, each id's count in the metric:attempts hash goes up and the id goes back "
    "on the dirty set; after five attempts it moves to metric:failed with its value still in the cache "
    "and the failure in the log, so an outage never loses a write without a trace. The sleep between "
    "cycles doubles after each failed flush, from one second to at most eight.",
    WB_TAIL)

N["Go", 269] = [
    "Walk the code from Example 01: configuration comes from the environment with os.Getenv (factor "
    "III), never from a baked-in file: SERVICE_VERSION names the version the image reports, and "
    "DATABASE_URL points the pgx pool at Postgres. The router is the standard library's ServeMux, so "
    "there is no router dependency.",
    "The two probes are the contract with Kubernetes: /healthz is liveness (is the process up? if not, "
    "restart it) and never checks a dependency; /readyz is readiness (can it serve?): it pings the "
    "database with a two-second timeout and, when that fails, answers 503 with status down, which takes "
    "the pod out of rotation without killing it. " + PROBE_READS + " Getting liveness and readiness "
    "wrong is a common cause of cascading restarts, so stress the distinction.",
]

N["Go", 419] = [
    "Four steps, all started by one SIGTERM, the only signal Kubernetes sends before SIGKILL. (1) "
    "signal.NotifyContext turns SIGTERM into a cancelled context; main calls stop() so that a later "
    "signal terminates at once, and flips the atomic.Bool behind /readyz, so readiness answers 503 and "
    "the Service stops sending new traffic. (2) The service keeps serving for DRAIN_DELAY_SECONDS (5 s "
    "in Example 21; it plays the part of a preStop sleep) while the endpoint removal propagates.",
    "(3) http.Server.Shutdown stops accepting connections and waits for in-flight requests, bounded by "
    "a 20-second context so a stuck request cannot hang the rollout; delay plus drain stays inside the "
    "30-second grace period. (4) The deferred pool.Close() runs and the process exits 0; a service "
    "with a franz-go client closes it here, which commits offsets and leaves the consumer group. Pair "
    "it with the preStop hook and the grace period on the Kubernetes side.",
]

N["Go", 476] = wb_notes(
    "Write-back has more moving parts than the other patterns; the slide shows the shape of Example 25. "
    "(1) PUT /write-back/metrics/{id} stores the metric in Redis with no TTL, adds the key to a 'dirty "
    "set', which tells the flusher which keys still have to reach the database, and answers 202 "
    "Accepted: the value is queued, not yet durable.",
    "(2) The flusher runs as a background goroutine: it SPOPs up to flushBatch dirty keys and upserts "
    "each one (ON CONFLICT (id) DO UPDATE), so a key flushed twice stays one row. SPOP is atomic, so "
    "two flusher instances each get a distinct subset of keys and the flusher scales out.",
    "(3) A key whose upsert fails is re-queued: HIncrBy counts its attempts in metric:attempts and it "
    "goes back on the dirty set, or, after five attempts, onto metric:failed with its value still in "
    "the cache and the failure in the log. The wait between cycles doubles after each failed one, from "
    "one second to at most eight.",
    WB_TAIL)

N["Go", 500] = (
    "The shutdown sequence that prevents dropped requests during a rolling deploy, from Example 21. One "
    "SIGTERM cancels the signal context: (1) the shuttingDown flag flips so /readyz returns 503 and "
    "Kubernetes stops sending new traffic, while /healthz stays 200; (2) the service keeps serving for "
    "DRAIN_DELAY_SECONDS so the load balancer's removal propagates; (3) Server.Shutdown stops accepting "
    "and finishes in-flight requests within a 20-second budget; (4) the deferred pool close runs and "
    "the process exits 0. The ordering matters: stop taking new work before draining existing work, "
    "and close pools last. This is the application half; Appendix H covers the Kubernetes half (preStop "
    "hook, terminationGracePeriodSeconds). Together they give zero-downtime rollouts.")

N["Cpp", 419] = [
    "The application side of graceful shutdown, from the C++ example; one SIGTERM, the only signal "
    "Kubernetes sends before SIGKILL, drives all of it. (1) The SIGTERM handler only stores an atomic "
    "flag, which is async-signal-safe: no locks, no allocation, no destructors. Drogon installs its own "
    "SIGTERM handler that quits at once, so the example replaces it after initialisation with "
    "registerBeginningAdvice. /readyz answers 503 once the flag is set, which removes the pod from the "
    "Service endpoints while the process keeps serving the requests already routed to it.",
    "(2) A watcher thread does the rest outside signal context: it sees the flag, keeps serving for "
    "DRAIN_DELAY_SECONDS (5 s in Example 21; it plays the part of a preStop sleep) so the endpoint "
    "removal propagates, waits up to 20 seconds for the RAII InFlightGuard count to reach zero, and "
    "calls app().quit(), which stops the listeners so run() returns. (3) main() joins the watcher, "
    "closes the libpq pool and returns 0, inside the 30-second grace period. std::stop_token and "
    "std::jthread extend the same pattern to worker threads such as Kafka consumers: the watcher calls "
    "request_stop() after it sees the flag, never inside the handler. Deterministic destruction makes "
    "the teardown order predictable.",
]

N["Cpp", 476] = [
    "Write-back from Example 25: PUT /write-back/metrics/{id} stores the payload in Redis under "
    "metric:<id> with a one-hour TTL (a queued write has to outlive a database outage), adds the key to "
    "the writeback:dirty set and answers 202 Accepted: the write is queued, not yet durable. A "
    "background std::thread wakes every two seconds, reads the dirty set, upserts each metric into "
    "Postgres with INSERT ... ON CONFLICT DO UPDATE, and removes the key from the set only after the "
    "upsert succeeds, so a failed write stays dirty and is retried on the next cycle.",
    "Retries are bounded: a per-key counter parks a key on writeback:failed after five failed attempts, "
    "with its value still in the cache and an error in the log, and the cycle time backs off to four "
    "and then eight seconds while flushes fail. The upsert makes a repeated flush harmless. The flusher "
    "has its own libpq connection, separate from the request handlers', and main() joins it after the "
    "shutdown flag is set (Appendix H). The risk is the one every write-back carries: a write that was "
    "acknowledged but not yet flushed is lost if Redis loses it, so keep write-back for data that "
    "tolerates that window, such as metrics.",
]

N["Cpp", 500] = (
    "Recap of App H in the failure-mode context: pod shutdown is itself a failure mode that graceful "
    "drain converts into a non-failure. The C++ disposability discipline of Example 21 (one SIGTERM, an "
    "async-signal-safe flag, /readyz answering 503, the drain delay, a bounded in-flight wait, "
    "app().quit(), the pool closed and exit 0) is what makes rolling deploys clean.")

N["Quarkus", 269] = (
    "Walk the code: config comes from the environment via MicroProfile Config (factor III): "
    "QUARKUS_DATASOURCE_JDBC_URL, the username and password and SERVICE_VERSION override "
    "application.properties, never a baked-in file. The two probes are plain JAX-RS handlers in Example "
    "01: /healthz is liveness (am I alive? if not, restart me) and never checks a dependency; /readyz is "
    "readiness (can I serve?): it runs SELECT 1 over JDBC, retrying once after a second, and when the "
    "database is unreachable it answers 503 with status down, which takes the pod out of rotation "
    "without killing it. " + PROBE_READS + " SmallRye Health (@Liveness and @Readiness checks on "
    "/q/health/live and /q/health/ready) is the extension that serves the same pair without handler "
    "code; the example writes them by hand so every language serves the same paths and bodies. Getting "
    "liveness vs readiness wrong is a top cause of cascading restarts, so stress the distinction. Maven "
    "with the quarkus-bom (platform 3.40.1) pins every dependency reproducibly.")

N["Quarkus", 287] = [
    "The whole trick is the @Transactional method: the insert of the order row and the insert of the "
    "outbox row run on one Agroal connection inside one JTA transaction, so they commit or roll back "
    "together. There is no Kafka call inside the request path: if the broker is down, the order still "
    "commits and the event ships later when Debezium tails the write-ahead log and relays the outbox "
    "row in commit order. This decouples request latency and availability from Kafka's.",
    "Example 04 needs no outbox extension: the outbox is a small table (aggregate id, event type, JSON "
    "payload, created_at), the payload is serialized with Jackson, and a standard Debezium Postgres "
    "connector handles the CDC. The Debezium Outbox Event Router single-message transform unwraps the "
    "row into the event envelope on the connector side. The same commit-together discipline reappears "
    "in the saga appendix.",
]

N["Quarkus", 419] = (
    "Example 21 handles the signal itself, so the whole sequence is visible. A sun.misc.Signal handler, "
    "registered on StartupEvent, replaces the JVM's default SIGTERM handler, which would start the "
    "shutdown hooks at once. One SIGTERM, the only signal Kubernetes sends before SIGKILL, drives "
    "everything: the handler flips the ShutdownState flag, so the hand-written /readyz answers 503 and "
    "the Service stops routing, and a drain thread keeps the service serving for DRAIN_DELAY_SECONDS "
    "(5 s; it plays the part of a preStop sleep) while the endpoint removal propagates. It then calls "
    "Quarkus.asyncExit(0): Quarkus stops accepting connections, waits for in-flight requests up to "
    "quarkus.shutdown.timeout (20 s), closes the datasource and exits 0, inside the 30-second grace "
    "period. A ShutdownEvent observer is the hook for what Quarkus leaves to you: Kafka consumers, the "
    "scheduler, WebSockets. Quarkus also has a built-in pre-shutdown delay (quarkus.shutdown.delay-"
    "enabled, a build-time flag) that reports readiness down through SmallRye Health; the example keeps "
    "its own /readyz, as Example 01 does. Pair it with the Kubernetes side: probes, preStop and the "
    "grace period.")

N["Quarkus", 476] = [
    "Quarkus write-back, as Example 25 runs it. (1) PUT /write-back/metrics/{mid} writes the metric to "
    "a Redis hash, adds the id to a dirty set, which tells the flusher what still has to reach the "
    "database, and answers 202 Accepted: the value is queued, not yet durable. (2) A @Scheduled method "
    "runs every second (a run is skipped while one is in flight), pops up to FLUSH_BATCH dirty ids with "
    "SPOP (atomic, so two flusher instances get distinct subsets and the flusher scales out) and "
    "upserts each one over JDBC with INSERT ... ON CONFLICT (id) DO UPDATE, so an id flushed twice "
    "stays one row. (3) An id whose upsert fails is re-queued: its count in the metric:attempts hash "
    "goes up and it goes back on the dirty set, or, after five attempts, onto metric:failed with its "
    "value still in the cache and the failure in the log. After a failed run the flusher waits two "
    "seconds, then four, then eight before it tries again.",
    "This is only safe with Redis persistence (AOF, appendonly yes); without it a Redis crash loses "
    "unflushed writes. For data that must not be lost, use write-through. For high-throughput telemetry "
    "where losing the last second is acceptable, write-back is what lets the service scale.",
]

N["Quarkus", 500] = (
    "Example 21 handles SIGTERM itself. A sun.misc.Signal handler, registered on StartupEvent, takes "
    "the single SIGTERM: (1) it flips the ShutdownState flag, so the hand-written /readyz answers 503 "
    "and Kubernetes stops routing new traffic, while /healthz stays 200; (2) a drain thread keeps the "
    "service serving for DRAIN_DELAY_SECONDS so the load balancer's removal propagates; (3) it calls "
    "Quarkus.asyncExit(0), and Quarkus stops accepting and drains in-flight HTTP within "
    "quarkus.shutdown.timeout (20 s); (4) Quarkus closes the datasource and the process exits 0. "
    "Appendix H covers the Kubernetes-side preStop and terminationGracePeriodSeconds.")

N["Spring", 269] = (
    "Walk the code: config comes from the environment through Spring's property resolution (factor "
    "III): SPRING_DATASOURCE_URL and its credentials configure the DataSource and SERVICE_VERSION feeds "
    "service.version, never a baked-in file; Spring profiles override per environment. The application "
    "name (spring.application.name) shows up in Micrometer metrics and traces. The two probes are a "
    "plain @RestController in Example 01: /healthz is liveness (am I alive? if not, restart me) and "
    "never checks a dependency; /readyz is readiness (can I serve?): it runs SELECT 1 on a pooled "
    "connection and, when that fails, answers 503 with status down, which takes the pod out of "
    "rotation without killing it. " + PROBE_READS + " Spring Boot Actuator offers the same pair as "
    "/actuator/health/liveness and /actuator/health/readiness with HealthIndicator beans; the example "
    "writes them by hand so every language serves the same paths and bodies. Getting liveness vs "
    "readiness wrong is a top cause of cascading restarts, so stress the distinction. Maven with "
    "spring-boot-starter-parent pins every dependency reproducibly. Constructor injection is the "
    "idiomatic Spring style: the bean stays immutable and is unit-testable without a container.")

N["Spring", 423] = (
    "Example 21 takes the signal itself, so the whole sequence is visible. A sun.misc.Signal handler "
    "registered before Spring starts replaces the JVM's default SIGTERM handler, which would run the "
    "shutdown hooks at once. One SIGTERM, the only signal Kubernetes sends before SIGKILL, drives "
    "everything: the handler flips ShutdownState, so the hand-written /readyz answers 503 and the "
    "Service stops routing, and a drain thread keeps the service serving for DRAIN_DELAY_SECONDS (5 s; "
    "it plays the part of a preStop sleep) while the endpoint removal propagates. It then calls "
    "System.exit(0), which runs Spring's shutdown hook: with server.shutdown=graceful the embedded "
    "Tomcat, Jetty or Reactor Netty stops accepting new connections and finishes in-flight HTTP, "
    "bounded by spring.lifecycle.timeout-per-shutdown-phase (20 s here; the default is 30 s), then the "
    "context closes the pool and the process exits 0, inside the 30-second grace period. Use "
    "@EventListener(ContextClosedEvent.class), @PreDestroy or SmartLifecycle to drain what Spring does "
    "not drain for you: Kafka consumers (consumer.wakeup() then commit on close), the scheduler (stop "
    "accepting new triggers), WebSockets (send a close frame so clients reconnect elsewhere). With "
    "Actuator, publishing ReadinessState.REFUSING_TRAFFIC flips /actuator/health/readiness the same "
    "way; the example keeps its own /readyz, as Example 01 does. Pair it with the Kubernetes settings: "
    "readiness, preStop and the grace period.")

N["Spring", 480] = (
    "Spring's @Scheduled drives write-back in Example 25. (1) PUT /write-back/metrics/{mid} writes the "
    "metric to a Redis hash, adds the id to a 'dirty set', which tells the flusher what still has to "
    "reach the database, and answers 202 Accepted: the value is queued, not yet durable. (2) "
    "@Scheduled(fixedDelayString = ...) runs every second, SPOPs up to FLUSH_BATCH dirty ids and "
    "upserts each one through JdbcClient with INSERT ... ON CONFLICT (id) DO UPDATE, so an id flushed "
    "twice stays one row. SPOP is atomic, so two replicas each get a distinct subset of ids and no lock "
    "is needed to scale out. (3) An id whose upsert fails is re-queued: its count in the "
    "metric:attempts hash goes up and it goes back on the dirty set, or, after five attempts, onto "
    "metric:failed with its value still in the cache and the failure in the log. After a failed run "
    "the flusher skips runs for two seconds, then four, then eight. " + WB_TAIL)

N["Spring", 504] = (
    "Example 21 takes SIGTERM itself. A sun.misc.Signal handler registered before Spring starts flips "
    "ShutdownState on the single SIGTERM: (1) the hand-written /readyz answers 503, so the Kubernetes "
    "readiness probe sees the pod go not-ready and stops routing, while /healthz stays 200; (2) a drain "
    "thread keeps the service serving for DRAIN_DELAY_SECONDS so the load balancer's removal "
    "propagates; (3) System.exit(0) runs Spring's graceful shutdown, which stops accepting and drains "
    "in-flight HTTP within timeout-per-shutdown-phase (20 s); (4) the context closes the pool and the "
    "process exits 0. Appendix H covers the Kubernetes preStop + terminationGracePeriodSeconds side.")

N["DotNet", 270] = (
    "Walk the code: ASP.NET Core 10 uses minimal hosting (Program.cs as a top-level script). Config "
    "flows from appsettings.json overridden by environment variables (factor III): "
    "ConnectionStrings__Default reaches GetConnectionString(\"Default\"), the cloud-native equivalent of "
    "web.config transforms, except that the cluster injects the values through ConfigMaps and Secrets "
    "instead of an MSDeploy package. The two probes are mapped by hand in Example 01: /healthz is "
    "liveness (am I alive? if not, restart me, and Kubernetes kills the Pod) and never checks a "
    "dependency; /readyz is readiness (can I serve? if not, take me out of rotation but don't kill me): "
    "it opens a pooled Npgsql connection and runs SELECT 1, and when that fails it answers 503 with "
    "status down, which removes the Pod from the Service endpoints. " + PROBE_READS + " Getting these "
    "wrong is a top cause of cascading restarts, the same way wrong IIS app-pool ping settings used to "
    "crash apps under load. AddHealthChecks with MapHealthChecks and the AspNetCore.HealthChecks.* "
    "community packages (MIT) are the framework route to the same pair; the example writes the handlers "
    "by hand so every language serves the same paths and bodies. The .NET runtime side: the service "
    "ships as a Linux container image built from a UBI Containerfile, not an MSI deployed to IIS.")

N["DotNet", 427] = (
    "ASP.NET Core's default ConsoleLifetime stops the host as soon as SIGTERM arrives, which leaves no "
    "time to fail readiness first. Example 21 replaces it with a ManualLifetime and takes the signal "
    "itself through PosixSignalRegistration; one SIGTERM, the only signal Kubernetes sends before "
    "SIGKILL, drives everything. The handler cancels the default action and flips a flag, so the "
    "hand-written /readyz answers 503 and the Service stops routing, then a task keeps the service "
    "serving for DRAIN_DELAY_SECONDS (5 s; it plays the part of a preStop sleep) while the endpoint "
    "removal propagates. It then calls StopApplication(): the host signals ApplicationStopping, Kestrel "
    "stops accepting and finishes in-flight requests, and every IHostedService gets StopAsync, all "
    "bounded by HostOptions.ShutdownTimeout (20 s here; the default is 30 s). ApplicationStopped "
    "disposes the data source and the process exits 0, inside the 30-second grace period. The pattern "
    "for other work: one BackgroundService per long-running concern (a Kafka consumer, a scheduler, the "
    "Temporal worker from Appendix D, the Streamiz processor from Section 6), each draining in its own "
    "StopAsync: consumer.Close() commits offsets and leaves the group, a SignalR hub sends close frames, "
    "a Temporal worker shuts down. For the WCF refugees: this is the in-box equivalent of "
    "ServiceHost.Close, except that SIGTERM triggers it and the budget is HostOptions.ShutdownTimeout "
    "rather than a per-binding timeout. The Kubernetes settings (probes, preStop, grace period) are the "
    "platform half of the contract.")

N["DotNet", 490] = (
    "Write-back in .NET, as Example 25 runs it. PUT /write-back/metrics/{mid} writes the metric fields "
    "to a Redis hash, adds the id to a 'dirty set' that tells the flusher what to drain, and answers "
    "202 Accepted in microseconds: the value is queued, not yet durable. The flusher is a background "
    "loop started with the app (a BackgroundService works the same way) that SPOPs up to 100 dirty ids "
    "at once. SPOP is the right primitive: it removes and returns elements in one call, so two flusher "
    "instances would each get a distinct subset of ids and horizontal scale works. Each id is upserted "
    "with INSERT ... ON CONFLICT (id) DO UPDATE, so an id flushed twice stays one row. An id whose "
    "upsert fails is re-queued: HashIncrementAsync counts its attempts in metric:attempts and it goes "
    "back on the dirty set, or, after five attempts, onto metric:failed with its value still in the "
    "cache and the failure in the log; the loop then waits two, four and at most eight seconds between "
    "runs. " + WB_TAIL)

N["DotNet", 514] = [
    "The application half of graceful shutdown, from the running example's .NET order-service. "
    "PosixSignalRegistration catches the single SIGTERM and cancels the default immediate shutdown; the "
    "handler flips a flag so /readyz answers 503 and Kubernetes takes the Pod out of the Service, while "
    "/healthz stays 200 so the kubelet does not restart a Pod that is winding down.",
    "New requests get 503. After DRAIN_DELAY_SECONDS the handler calls StopApplication(): Kestrel stops "
    "accepting and finishes in-flight requests within HostOptions.ShutdownTimeout (20 s), the data "
    "source is disposed and the process exits 0, inside terminationGracePeriodSeconds. Appendix H "
    "covers the hosted-service drain hooks, the preStop hook and the grace period.",
]

# ------------------------------------------------------------------ text replacements

R = {}  # deck -> list of (sldId, scope, find, repl, why)

R["Python"] = [
    (269, "slide", 'return {"status": "down", "checks": {"database": "unreachable"}}',
     'return JSONResponse({"status": "down", "checks": {"database": "unreachable"}}, 503)',
     "examples/01 python: readiness answers 503 when the database is down (937f8d7)"),
    (269, "notes", "it runs SELECT 1 on the database pool and reports down otherwise, which takes the "
     "pod out of rotation without killing it.",
     "it runs SELECT 1 on the database pool and, when that fails, answers 503 with status down, which "
     "takes the pod out of rotation without killing it. " + PROBE_READS,
     "notes follow the 503"),
    (419, "slide", "The first SIGTERM flips readiness; the next goes to uvicorn, which drains in-flight "
     "HTTP (bounded by --timeout-graceful-shutdown).",
     "One SIGTERM flips readiness; after DRAIN_DELAY_SECONDS the handler hands over to uvicorn, which "
     "drains in-flight HTTP within 20 s.",
     "examples/21: one SIGTERM drives the drain (9676f32)"),
    (476, "slide", WB_CAPTION_OLD, WB_CAPTION_NEW, "examples/25: 202 and bounded retry (ebca295)"),
]

R["Go"] = [
    (419, "slide", "signal.NotifyContext catches SIGTERM; readiness fails first so the Service stops "
     "routing, then Server.Shutdown drains within a 15-second budget.",
     "One SIGTERM: readiness fails first, the service keeps serving for DRAIN_DELAY_SECONDS, then "
     "Server.Shutdown drains within 20 seconds.",
     "examples/21 go: drain delay and a 20 s shutdown budget (9676f32)"),
    (476, "slide", WB_CAPTION_OLD, WB_CAPTION_NEW, "examples/25: 202 and bounded retry (ebca295)"),
]

R["Cpp"] = [
    (269, "notes", "/readyz runs SELECT 1 through the libpq pool and reports ready or down (readiness), "
     "so the probe",
     "/readyz runs SELECT 1 through the libpq pool and answers 200 with status ready, or 503 with "
     "status down (readiness; the probe reads the status code, not the body), so the probe",
     "examples/01 cpp: readiness answers 503 when the database is down (937f8d7)"),
    (419, "slide", "SIGTERM → fail readiness → keep serving while endpoints update → drain in-flight → "
     "RAII closes the pool.",
     "One SIGTERM → fail readiness → serve DRAIN_DELAY_SECONDS → drain in-flight (20 s) → quit → "
     "close the pool.",
     "examples/21 cpp: watcher thread, drain delay, bounded wait, app().quit() (9676f32)"),
    (476, "slide", "Write to Redis and mark dirty; a flusher upserts every 2 s and clears a mark only "
     "once the DB has the row.",
     "PUT answers 202; the flusher upserts every 2 s, clears a mark once the DB has the row, and parks a "
     "key after 5 failures.",
     "examples/25 cpp: 202 and bounded retry (ebca295)"),
    (500, "slide", "Shutdown is a failure mode: readiness flip, drain in-flight requests, RAII cleanup.",
     "Shutdown is a failure mode: readiness flip, drain delay, bounded in-flight drain, then cleanup.",
     "examples/21 cpp (9676f32)"),
]

R["Quarkus"] = [
    (269, "slide", "java · Quarkus + SmallRye Health", "java · Quarkus REST",
     "examples/01 quarkus hand-writes /healthz and /readyz"),
    (287, "slide", "java · Hibernate Panache + Debezium", "java · Agroal JDBC + Debezium",
     "examples/04 quarkus: plain JDBC inserts into the outbox table"),
    (419, "slide", "delay flips readiness DOWN first (a build-time setting), then in-flight HTTP gets "
     "`timeout` to finish; only HTTP is automatic — drain the rest in a ShutdownEvent observer.",
     "One SIGTERM flips readiness; after DRAIN_DELAY_SECONDS, Quarkus.asyncExit(0) drains in-flight "
     "HTTP within quarkus.shutdown.timeout (20 s).",
     "examples/21 quarkus: Signal handler, drain delay, asyncExit (9676f32)"),
    (476, "slide", "java · Quarkus + @Scheduled + Redis + Panache", "java · Quarkus + @Scheduled + Redis + JDBC",
     "examples/25 quarkus flushes with JDBC per-id upserts"),
    (476, "slide", WB_CAPTION_OLD, WB_CAPTION_NEW, "examples/25: 202 and bounded retry (ebca295)"),
    (500, "slide", "java · Quarkus + SmallRye Health", "java · Quarkus",
     "examples/21 quarkus: hand-written /readyz"),
]

R["Spring"] = [
    (269, "slide", "java · Spring Boot 4 + Actuator", "java · Spring Boot 4",
     "examples/01 spring-boot hand-writes /healthz and /readyz"),
    (423, "slide", "server.shutdown=graceful drains HTTP; publish a Readiness REFUSING_TRAFFIC event to "
     "flip the probe; drain everything else in ContextClosedEvent.",
     "One SIGTERM flips readiness; after DRAIN_DELAY_SECONDS, System.exit(0) runs Spring's graceful "
     "shutdown, bounded at 20 s per phase.",
     "examples/21 spring-boot: Signal handler, drain delay, System.exit (9676f32)"),
    (480, "slide", "java · Spring Boot 4 + @Scheduled + ShedLock + Spring Data Redis + JPA",
     "java · Spring Boot 4 + @Scheduled + Spring Data Redis + JdbcClient",
     "examples/25 spring-boot: JdbcClient upserts, no ShedLock"),
    (480, "slide", "The dirty set is the key idea — it tells the flusher what to drain. ShedLock ensures "
     "only one Pod flushes at a time.", WB_CAPTION_NEW, "examples/25: 202 and bounded retry (ebca295)"),
    (504, "slide", "java · Spring Boot 4 + Actuator", "java · Spring Boot 4",
     "examples/21 spring-boot: hand-written /readyz"),
]

R["DotNet"] = [
    (270, "slide", "csharp · .NET 10 + ASP.NET Core + AspNetCore.HealthChecks",
     "csharp · .NET 10 + ASP.NET Core + Npgsql",
     "examples/01 dotnet maps /healthz and /readyz by hand"),
    (427, "slide", "HostOptions.ShutdownTimeout bounds the drain; each BackgroundService's StopAsync is "
     "your hook. Flip readiness DOWN first so Kubernetes stops routing.",
     "One SIGTERM flips readiness; after DRAIN_DELAY_SECONDS, StopApplication() lets Kestrel drain "
     "in-flight requests within ShutdownTimeout (20 s).",
     "examples/21 dotnet: PosixSignalRegistration, drain delay, StopApplication (9676f32)"),
    (489, "notes", "A BackgroundService drains the cache to the DB", "A background flusher drains the "
     "cache to the DB", "examples/25 dotnet: the flusher is a Task.Run loop"),
    (490, "slide", "Write-back with BackgroundService in ASP.NET Core",
     "Write-back with a background flusher in ASP.NET Core",
     "examples/25 dotnet: the flusher is a Task.Run loop, not a BackgroundService"),
    (490, "slide", "csharp · ASP.NET Core 10 + BackgroundService + StackExchange.Redis + EF Core",
     "csharp · ASP.NET Core 10 + StackExchange.Redis + Npgsql",
     "examples/25 dotnet: Npgsql upserts, no EF Core"),
    (490, "slide", WB_CAPTION_OLD, WB_CAPTION_NEW, "examples/25: 202 and bounded retry (ebca295)"),
]

# slide numbers of the current decks, for the _slide comments
SLIDE_NO = {
    ("Python", 269): 14, ("Python", 419): 164, ("Python", 476): 221, ("Python", 500): 245,
    ("Go", 269): 14, ("Go", 419): 164, ("Go", 476): 221, ("Go", 500): 245,
    ("Cpp", 269): 14, ("Cpp", 419): 164, ("Cpp", 476): 221, ("Cpp", 500): 245,
    ("Quarkus", 269): 14, ("Quarkus", 287): 32, ("Quarkus", 419): 164, ("Quarkus", 476): 221,
    ("Quarkus", 500): 245,
    ("Spring", 269): 14, ("Spring", 423): 168, ("Spring", 480): 225, ("Spring", 504): 249,
    ("DotNet", 270): 15, ("DotNet", 427): 172, ("DotNet", 489): 234, ("DotNet", 490): 235,
    ("DotNet", 514): 259,
}

WHY_CODE = {
    269: "examples/01: hand-written /healthz and /readyz; readiness answers 503 when the database is down",
    270: "examples/01: hand-written /healthz and /readyz; readiness answers 503 when the database is down",
    287: "examples/04 quarkus: plain JDBC inserts into orders and outbox in one @Transactional method",
    419: "examples/21: one SIGTERM -> readiness 503 -> DRAIN_DELAY_SECONDS -> stop accepting -> in-flight "
         "drain within 20 s -> cleanup -> exit 0",
    423: "examples/21: one SIGTERM -> readiness 503 -> DRAIN_DELAY_SECONDS -> stop accepting -> in-flight "
         "drain within 20 s -> cleanup -> exit 0",
    427: "examples/21: one SIGTERM -> readiness 503 -> DRAIN_DELAY_SECONDS -> stop accepting -> in-flight "
         "drain within 20 s -> cleanup -> exit 0",
    476: "examples/25: /write-back/metrics/{id} answers 202; upsert; bounded retry (metric:attempts, "
         "metric:failed, backoff)",
    480: "examples/25: /write-back/metrics/{id} answers 202; upsert; bounded retry (metric:attempts, "
         "metric:failed, backoff)",
    490: "examples/25: /write-back/metrics/{id} answers 202; upsert; bounded retry (metric:attempts, "
         "metric:failed, backoff)",
    500: "Appendix M recap follows examples/21 (one SIGTERM, drain delay, 20 s drain)",
    504: "Appendix M recap follows examples/21 (one SIGTERM, drain delay, 20 s drain)",
    514: "Appendix M recap follows examples/21 (one SIGTERM, drain delay, 20 s drain)",
}

ORDER = {  # sldIds in deck order, per deck
    "Python": [269, 419, 476, 500], "Go": [269, 419, 476, 500], "Cpp": [269, 419, 476, 500],
    "Quarkus": [269, 287, 419, 476, 500], "Spring": [269, 423, 480, 504],
    "DotNet": [270, 427, 489, 490, 514],
}


# line count of each box on the committed decks: set_code's limit is max(22, this)
NOW = {
    ("Python", 419): 21, ("Python", 476): 25, ("Python", 500): 21,
    ("Go", 269): 19, ("Go", 419): 16, ("Go", 476): 20, ("Go", 500): 20,
    ("Cpp", 269): 22, ("Cpp", 419): 22, ("Cpp", 476): 22, ("Cpp", 500): 16,
    ("Quarkus", 269): 16, ("Quarkus", 287): 16, ("Quarkus", 419): 17, ("Quarkus", 476): 25,
    ("Quarkus", 500): 21,
    ("Spring", 269): 25, ("Spring", 423): 25, ("Spring", 480): 24, ("Spring", 504): 19,
    ("DotNet", 270): 19, ("DotNet", 427): 24, ("DotNet", 490): 25, ("DotNet", 514): 17,
}
SHAPE = {("Spring", 480): 2493, ("DotNet", 490): 2598}  # the slide also has a one-line chip box


def check():
    bad = []
    for (deck, sid), lines in CODE.items():
        cap = min(CAP[deck, sid], max(22, NOW[deck, sid]))
        if len(lines) > cap:
            bad.append(f"{deck} {sid}: {len(lines)} lines > capacity {cap}")
        for i, ln in enumerate(lines, 1):
            if len(ln) > MAX_COLS:
                bad.append(f"{deck} {sid} line {i}: {len(ln)} cols: {ln}")
            if "\t" in ln:
                bad.append(f"{deck} {sid} line {i}: tab")
    return bad


def build(deck):
    ops = []
    for sid in ORDER[deck]:
        no = SLIDE_NO[deck, sid]
        for (s, scope, find, repl, why) in R.get(deck, []):
            if s == sid:
                ops.append({"op": "replace", "scope": scope, "sldIds": [sid], "find": find,
                            "repl": repl, "expect": 1, "cat": "code" if scope == "slide" else "notes",
                            "_slide": no, "_why": why, "_src": "align"})
        if (deck, sid) in CODE:
            op = {"op": "set_code", "sldId": sid, "lines": CODE[deck, sid], "cat": "code",
                  "_slide": no, "_why": WHY_CODE[sid], "_src": "align"}
            if (deck, sid) in SHAPE:
                op["shape_id"] = SHAPE[deck, sid]
            ops.append(op)
        if (deck, sid) in N:
            n = N[deck, sid]
            op = {"op": "set_notes", "sldId": sid, "cat": "notes", "_slide": no,
                  "_why": "notes follow the code", "_src": "align"}
            if isinstance(n, list):
                op["paragraphs"] = n
            else:
                op["text"] = n
            ops.append(op)
    return {"ops": ops}


def main(argv):
    bad = check()
    for b in bad:
        print("FAIL", b)
    if bad:
        return 1
    if "--check" in argv:
        print("ok")
        return 0
    for deck, name in OUT.items():
        path = EDITS / name
        path.write_text(json.dumps(build(deck), indent=1, ensure_ascii=False) + "\n")
        print(path.relative_to(REPO), len(build(deck)["ops"]), "ops")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
