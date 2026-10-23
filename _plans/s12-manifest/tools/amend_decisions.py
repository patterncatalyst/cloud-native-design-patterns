#!/usr/bin/env python3
"""Apply the 2026-10-12 manifest decisions (plan, user decision 6) to three deck edit files.

Spring: Appendix D presents the hand-rolled saga orchestrator of examples/17-sagas/spring-boot; Spring
Statemachine appears only as archived upstream. Go: valet key and claim-check follow examples/12-security/go
(golang-jwt ticket); minio-go is gone. C++: compendium and third-party library references verified upstream
(table in Designing-Cloud-Native-APIs-Cpp.md).

Idempotent: ops carrying "_amend" are removed and re-inserted; superseded ops are removed by their find text.
New ops go before the first agenda / Appendix R op (cat "new"), so they see the text after every voice edit.
C++ replace ops find their sldId in the post-edit text copy (M/verify/<deck>.md) by the find string.
Run with any python3; then verify_all.py.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EDITS = REPO / "lgtm-presentation" / "edits"
M = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
TAG = "S12 decision 6"
CS = "patterncatalyst.github.io/cpp-statelessness/docs/"


def load(deck):
    return json.loads((EDITS / f"{deck}.json").read_text())


def save(deck, data):
    (EDITS / f"{deck}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def insert(deck, new_ops, drop_finds=(), repl_patch=None):
    data = load(deck)
    ops = [o for o in data["ops"] if not o.get("_amend")]
    ops = [o for o in ops if not (o.get("op") == "replace" and o.get("find") in drop_finds)]
    for o in ops:
        if repl_patch and o.get("op") == "replace" and o.get("find") in repl_patch:
            o["repl"] = repl_patch[o["find"]]
            o["_amended"] = TAG
    at = next(i for i, o in enumerate(ops) if o.get("cat") == "new")
    for o in new_ops:
        o["_amend"] = TAG
    data["ops"] = ops[:at] + new_ops + ops[at:]
    save(deck, data)
    return len(new_ops)


def rep(sid, find, repl, cat, scope="both", expect=1, why=None):
    o = {"op": "replace", "scope": scope, "find": find, "repl": repl, "expect": expect, "sldIds": [sid], "cat": cat}
    if why:
        o["_why"] = why
    return o


def sid_of(md_lines, find):
    sid, hits = None, set()
    for line in md_lines:
        m = re.match(r"^## \[\d+\].*\(sldId (\d+)\)$", line)
        if m:
            sid = int(m.group(1))
        elif find in line:
            hits.add(sid)
    if len(hits) != 1:
        raise SystemExit(f"find string not unique to one slide ({hits}): {find[:80]}")
    return hits.pop()


# ---------------------------------------------------------------- Spring
SPRING = "Designing-Cloud-Native-APIs-Spring"
SM_FACT = ("Spring Statemachine is archived upstream: github.com/spring-projects/spring-statemachine is a "
           "read-only archive whose README says the project is no longer maintained (last release 4.0.2, "
           "June 2026), and the spring.io announcement of 21 April 2025 made 4.0.x the last open-source line, "
           "with later releases for commercial Tanzu Spring customers only.")
spring_code = [
    "// SagaService.java excerpt (examples/17-sagas); helper names stand for its JdbcClient calls",
    "private void advance(String sagaId) {",
    "    String[] statusHolder = new String[1];",
    "    txTemplate.executeWithoutResult(status -> {         // lock, run one step, commit",
    "        var row = lockRow(sagaId);          // SELECT ... FROM sagas WHERE id = :id FOR UPDATE",
    "        if (row == null || !\"RUNNING\".equals(row[0])) return;      // finished: no-op",
    "        int stepIndex = (int) row[1]; var context = fromJson((String) row[2]);",
    "        if (stepIndex >= STEPS.size()) { markStatus(sagaId, \"COMPLETED\"); return; }",
    "        SagaStep step = STEPS.get(stepIndex);               // (name, compensation)",
    "        try {",
    "            Map<String, Object> result = stepExecutor.execute(step.name(), context);",
    "            context.put(step.name(), result);                  // output flows forward",
    "            logStep(sagaId, step.name(), \"execute\", result);",
    "            saveProgress(sagaId, stepIndex + 1, context);      // step_index + JSONB context",
    "            statusHolder[0] = \"RUNNING\";",
    "        } catch (Exception e) {",
    "            markStatus(sagaId, \"COMPENSATING\"); statusHolder[0] = \"COMPENSATING\";",
    "        }",
    "    });",
    "    if (\"RUNNING\".equals(statusHolder[0])) advance(sagaId);    // next step, new transaction",
    "    else if (\"COMPENSATING\".equals(statusHolder[0])) compensate(sagaId);",
    "}",
]
spring_ops = [
    # 46 · section 07 divider notes
    rep(301, "For orchestration in this stack we feature Temporal (Java SDK + Spring Boot) for durable execution as "
             "the primary approach, with Spring State Machine as a lighter-weight alternative for state-driven flows. "
             "Appendix D shows both, side by side, against the saga from the data section.",
        "For orchestration, Appendix D sets two approaches against the saga from the data section: the hand-rolled, "
        "database-backed orchestrator that Example 17 runs, and Temporal (Java SDK + Spring Boot) for durable "
        "execution when the saga outgrows it.", "stack", "notes"),
    # 94 · references bullet
    rep(349, "Temporal Java SDK docs (docs.temporal.io/dev-guide/java), Spring State Machine, Spring for GraphQL",
        "Temporal Java SDK docs (docs.temporal.io/dev-guide/java), Spring for GraphQL", "stack"),
    # 121 · figure and notes
    {"op": "replace_picture", "sldId": 376, "shape_id": 1333, "png": "lgtm-presentation/edits/png/17-saga-state.png",
     "cat": "stack", "_slide": 121, "_why": "figure named 'Temporal / State Machine'; the site figure 17-saga-state"},
    rep(376, "Spring State Machine is a lighter in-process alternative we'll show side by side.",
        "Example 17 runs the first option, and this appendix sets its code beside Temporal.", "stack", "notes"),
    # 125 · notes
    rep(380, "Temporal does the same automatically through its workflow input/output passing; Spring State Machine "
             "does it via the extended state context.",
        "Temporal does the same through its workflow input/output passing, and Example 17 stores each step's "
        "result in the saga's JSONB context under the step name.", "stack", "notes"),
    # 126 · two durable paths
    {"op": "set_text", "sldId": 381, "shape_id": 1391, "paragraphs": ["Two ways to keep a saga durable"],
     "cat": "stack", "_slide": 126},
    {"op": "set_text", "sldId": 381, "shape_id": 1392, "cat": "stack", "_slide": 126, "paragraphs": [
        "Two open-source paths, both shown in this appendix with a diagram and code.",
        "The hand-rolled orchestrator (Example 17): one sagas row per instance (status, step_index, JSONB context) "
        "and a saga_log, written with JdbcClient inside a TransactionTemplate. No extra dependency, no extra cluster.",
        "Temporal: a durable execution engine (Temporal Server MIT, Java SDK Apache 2.0). Workflows and activities "
        "are plain Java; the Server persists every event and replays it on recovery. Most power, a separate "
        "cluster to run.",
        "Decision rule: keep the hand-rolled orchestrator while the saga is short and lives in one service; reach "
        "for Temporal when it is long, shared across services, or needs timers, retries and child workflows as "
        "first-class features.",
        "Spring Statemachine is not on the list: its repository is archived upstream and 4.0.x was its last "
        "open-source line.",
    ]},
    {"op": "set_notes", "sldId": 381, "cat": "stack", "_slide": 126, "paragraphs": [
        "Frame the choice as owning the transitions against buying durable execution. Both are open source and both "
        "survive a pod crash mid-flow.",
        "The hand-rolled orchestrator is what Example 17 runs: a sagas table with one row per saga holding status, "
        "step_index and a JSONB context, and a saga_log table that records every execute, failed and compensate "
        "action. Each step runs in its own transaction that locks the row, runs the step and commits the new "
        "context and step index together. On startup the service resumes every saga still marked RUNNING. "
        "Nothing new to operate.",
        "Temporal: founded by the original Cadence team, MIT-licensed Server and Apache-2.0 Java SDK, actively "
        "maintained. It adds durable execution, deterministic replay, automatic retries with backoff, timers, a "
        "Saga compensation utility, child workflows, and a CLI and UI to inspect runs. The cost is operating a "
        "Temporal cluster, which runs on your own Kubernetes with no SaaS required.",
        SM_FACT + " That conflicts with the open-source-only rule, so the deck does not offer it.",
        "The decision rule to leave with the audience: the question is how much engine this saga needs.",
    ]},
    # 129 · the orchestrator picture
    {"op": "set_text", "sldId": 384, "shape_id": 1425,
     "paragraphs": ["The hand-rolled orchestrator: one row, one log, no extra cluster"], "cat": "stack", "_slide": 129},
    {"op": "replace_picture", "sldId": 384, "shape_id": 1426,
     "png": "lgtm-presentation/edits/png/17-sagas-architecture.png", "cat": "stack", "_slide": 129,
     "_why": "Spring Statemachine figure replaced by examples/17-sagas/architecture.svg"},
    {"op": "set_text", "sldId": 384, "shape_id": 1427, "cat": "stack", "_slide": 129, "paragraphs": [
        "A sagas row locked FOR UPDATE, a saga_log of every action, and a resume pass at startup: Example 17."]},
    {"op": "set_notes", "sldId": 384, "cat": "stack", "_slide": 129, "paragraphs": [
        "Walk the picture: the saga-orchestrator service of Example 17. POST /sagas creates a sagas row (status "
        "RUNNING, step_index 0, the order in a JSONB context) and runs the steps in order: charge_payment, "
        "reserve_stock, book_shipping. Postgres holds two tables: sagas, one row per saga, and saga_log, one row "
        "per execute, failed or compensate action.",
        "Each step runs in its own transaction. The orchestrator locks the row with SELECT ... FOR UPDATE, returns "
        "at once unless the status is RUNNING (a repeated call is a no-op), runs the step, writes its output into "
        "the context and the log, and moves step_index forward, all in one commit. When the index passes the last "
        "step the status becomes COMPLETED.",
        "When a step throws, the same transaction logs the failure and sets COMPENSATING; the compensation pass "
        "then walks the completed steps in reverse (release_stock, then refund_payment) and ends in COMPENSATED. "
        "The dashed path in the picture is that unwind.",
        "Recovery is a StartupRunner: on boot it advances every saga still marked RUNNING. Everything runs "
        "in-process in the Spring Boot app, on the Postgres you already operate.",
    ]},
    # 130 · the code
    {"op": "set_text", "sldId": 385, "shape_id": 1436,
     "paragraphs": ["The hand-rolled orchestrator: one step per transaction"], "cat": "code", "_slide": 130},
    {"op": "set_text", "sldId": 385, "shape_id": 1438, "paragraphs": ["java · Spring Boot 4 + JdbcClient"],
     "cat": "code", "_slide": 130},
    {"op": "set_code", "sldId": 385, "shape_id": 1439, "lines": spring_code, "cat": "code", "_slide": 130,
     "_src": "examples/17-sagas/spring-boot/saga-orchestrator/src/main/java/com/example/saga/service/SagaService.java"},
    {"op": "set_text", "sldId": 385, "shape_id": 1440, "cat": "code", "_slide": 130, "paragraphs": [
        "The row lock, the step's output and the new state commit together; a failed step hands off to "
        "compensate()."]},
    {"op": "set_notes", "sldId": 385, "cat": "code", "_slide": 130, "paragraphs": [
        "The excerpt is advance() from SagaService in Example 17, condensed where it talks to Postgres: lockRow, "
        "saveProgress, logStep and markStatus stand for its JdbcClient calls, and the failed-step log row is "
        "left out.",
        "STEPS is a list of SagaStep records pairing each forward step with its compensation (charge_payment with "
        "refund_payment, reserve_stock with release_stock, book_shipping with cancel_shipping), so the unwind "
        "order is data. advance() opens a "
        "TransactionTemplate, locks the saga row with SELECT ... FOR UPDATE and returns at once unless the status "
        "is RUNNING, so a redelivered request or a second worker finds a finished saga and does nothing.",
        "Inside the transaction the step runs, its result goes into the JSONB context under the step's name (this "
        "is how book_shipping can read what reserve_stock produced), the log row is written, and step_index moves "
        "forward. The lock, the log and the new state commit together, the same rule as the outbox.",
        "After the commit, advance() calls itself for the next step in a new transaction. A crash rolls back at "
        "most the step in flight, which runs again on resume, so every step must be idempotent. A thrown "
        "exception marks the saga COMPENSATING, and compensate() runs the completed steps' compensations in "
        "reverse before setting COMPENSATED.",
        "Compared with Temporal: no extra server, but no built-in retries, timers or replay; the retry and resume "
        "logic is yours. The step executor in the example simulates the three services.",
    ]},
]
spring_drop = {
    "Temporal: founded by the original Cadence team, MIT-licensed Server and Apache-2.0 Java SDK, very actively "
    "maintained (recent Java SDK release 1.35 in April 2026).",
    "The top row IS the saga as a state machine: CREATED → PAID → RESERVED → SHIPPED → DONE, with each "
    "transition triggered by an event (PAY_OK, RESERVE_OK, SHIP_OK, DELIVERED).",
    "Below: three pieces of machinery.",
    "Spring State Machine — Spring's own framework (Apache 2.0).",
    "The whole thing runs in-process inside your Spring Boot app — no extra cluster, Apache-2.0 open source.",
}
spring_patch = {
    "If you want the managed alternative, the next few slides show Temporal and Spring State Machine — same "
    "problem, different point on the build-vs-buy spectrum.":
        "Temporal, in this appendix, solves the same problem at a different point on the build-vs-buy spectrum; "
        "Example 17 runs the hand-rolled version with JdbcClient.",
}

# ---------------------------------------------------------------- Go
GO = "Designing-Cloud-Native-APIs-Go"
go_valet = [
    "// main.go (excerpt), examples/12-security/go: the valet key is an HS256 JWT (golang-jwt v5)",
    "type valetClaims struct {",
    "   Resource  string `json:\"res\"`",
    "   Operation string `json:\"op\"`",
    "   jwt.RegisteredClaims",
    "}",
    "func mintValet(resource, operation string) map[string]any {",
    "   expires := time.Now().Add(5 * time.Minute)                    // time-bound",
    "   token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, valetClaims{",
    "      Resource: resource, Operation: operation,                  // one object, one operation",
    "      RegisteredClaims: jwt.RegisteredClaims{Issuer: \"order-service\",",
    "         ExpiresAt: jwt.NewNumericDate(expires), IssuedAt: jwt.NewNumericDate(time.Now())},",
    "   }).SignedString([]byte(valetSecret))",
    "   if err != nil { slog.Error(\"sign valet key\", \"err\", err) }",
    "   return map[string]any{\"resource\": resource, \"operation\": operation,",
    "      \"expires\": expires.Unix(), \"token\": token}",
    "}",
    "// verifyValet: HS256 only, exp required, issuer checked; then res, op and exp must match",
    "parsed, err := jwt.ParseWithClaims(token, &claims,",
    "   func(*jwt.Token) (any, error) { return []byte(valetSecret), nil },",
    "   jwt.WithValidMethods([]string{jwt.SigningMethodHS256.Alg()}),",
    "   jwt.WithExpirationRequired(), jwt.WithIssuer(\"order-service\"))",
]
go_claim = [
    "// claim-check sketch: store is any encrypted object store; the token is the valet-key JWT",
    "func publishWithClaim(ctx context.Context, cl *kgo.Client, orderID string, body []byte) error {",
    "   key := \"payloads/\" + orderID",
    "   if err := store.Put(ctx, key, body, true); err != nil { return err } // encrypted, ACL'd",
    "   claim, _ := json.Marshal(map[string]any{",
    "      \"order_id\": orderID,",
    "      \"uri\":      \"https://objects.internal/\" + key,",
    "      \"token\":    mintValet(key, \"GET\")[\"token\"],          // GET only, five minutes",
    "   })",
    "   return cl.ProduceSync(ctx,                               // only the claim goes on the topic",
    "      &kgo.Record{Topic: \"order.documents\", Key: []byte(orderID), Value: claim}).FirstErr()",
    "}",
    "func onClaim(ctx context.Context, r *kgo.Record) error {",
    "   var c Claim",
    "   if err := json.Unmarshal(r.Value, &c); err != nil { return err }",
    "   body, err := store.Get(ctx, c.URI, c.Token)              // the store verifies the ticket",
    "   if err != nil { return err }",
    "   return handle(ctx, body)                                 // PII never touched the topic",
    "}",
]
go_ops = [
    {"op": "set_text", "sldId": 333, "shape_id": 866, "paragraphs": ["Valet key  —  scoped, time-bound, op-restricted"],
     "cat": "stack", "_slide": 78},
    {"op": "set_text", "sldId": 333, "shape_id": 868, "paragraphs": ["go · net/http + golang-jwt v5"],
     "cat": "stack", "_slide": 78},
    {"op": "set_code", "sldId": 333, "shape_id": 869, "lines": go_valet, "cat": "code", "_slide": 78,
     "_src": "examples/12-security/go/cmd/server/main.go (valetClaims, mintValet, verifyValet)"},
    {"op": "set_notes", "sldId": 333, "cat": "stack", "_slide": 78, "paragraphs": [
        "The handler mints a ticket that authorises one operation (GET or PUT) on one resource for 300 seconds; "
        "after that it is worthless. In Example 12 the ticket is an HS256 JWT signed with golang-jwt v5: the res "
        "and op claims carry the scope, exp the expiry, iss the issuer. POST /valet-key returns the resource, the "
        "operation, the expiry and the token.",
        "The verifier (GET /verify-valet in the example, the storage gateway in a real system) parses with "
        "WithValidMethods so only HS256 is accepted (no alg=none, no algorithm swap), requires exp, checks the "
        "issuer, then compares res, op and exp with the request. Any mismatch is a 403.",
        "The application stays out of the data path: the client presents the ticket to the storage side directly. "
        "Most object stores, open-source ones included, accept signed URLs of the same shape: the method, the "
        "object key and the expiry signed into the URL. A user-scoped resource path "
        "also lets the store's policy restrict each user to their own prefix as defence in depth.",
    ]},
    {"op": "set_text", "sldId": 342, "shape_id": 968, "paragraphs": ["go · franz-go + golang-jwt v5"],
     "cat": "stack", "_slide": 87},
    {"op": "set_code", "sldId": 342, "shape_id": 969, "lines": go_claim, "cat": "code", "_slide": 87,
     "_src": "_docs/12-security.md claim-check Go tab; token from examples/12-security/go mintValet"},
    {"op": "set_notes", "sldId": 342, "cat": "stack", "_slide": 87, "paragraphs": [
        "Two halves. The producer writes the payload to an encrypted object store under payloads/<order id>, "
        "mints a ticket for that key (the golang-jwt valet key of Example 12: GET only, five minutes), and "
        "publishes only a small claim {order_id, uri, token} to order.documents with franz-go's ProduceSync. The "
        "PII is never on Kafka's wire.",
        "The consumer decodes the claim, fetches the payload with the token, processes it, then lets the offset "
        "commit (at-least-once delivery, so the handler must be idempotent). The store verifies the ticket before "
        "it serves the object and logs every fetch with the principal, an audit trail plain Kafka does not give.",
        "Size the ticket's lifetime to the consumer's worst-case lag: five minutes fits the demo, not a backlog. "
        "No runnable example covers claim-check; store stands for any encrypted object store. Set a "
        "lifecycle rule that expires claims after the retention period, so a replayed message points at nothing.",
    ]},
]

# ---------------------------------------------------------------- C++
CPP = "Designing-Cloud-Native-APIs-Cpp"
cpp_pairs = [
    # (find, repl, cat)
    ("scaffold C++ stubs via openapi-generator-cli (cpp-pistache-server template is most mature).",
     "scaffold C++ stubs with OpenAPI Generator (stable C++ server generators: cpp-pistache-server, "
     "cpp-httplib-server; none targets Drogon).", "stack"),
    ("The cpp-stateless compendium's 'budget-aware' rule applies — never retry past the inbound deadline.",
     f"Cap the retry budget at the inbound deadline and never retry past it (cpp-statelessness Doc 07, "
     f"{CS}07-state-externalization/).", "stack"),
    ("Dependencies injected by reference (OrdersClient&, InventoryClient&) — same DI pattern as the cpp-stateless "
     "composition root.",
     f"Dependencies are injected by reference (OrdersClient&, InventoryClient&) from a composition root in main(), "
     f"as in cpp-statelessness Doc 04 ({CS}04-process-scoped-state/).", "stack"),
    ("The cpp-stateless compendium's ScopedConnection pattern (RAII checkout, invalidate on broken) applies per "
     "service.",
     f"Each service checks connections out through an RAII guard that invalidates a broken connection instead of "
     f"returning it to the pool (ScopedConn in cpp-statelessness Doc 07, {CS}07-state-externalization/).", "stack"),
    ("Note the cpp-stateless idioms: PgTxn is an RAII transaction object (commit on success, rollback on "
     "destruction); the consumer is process-scoped;",
     "PgTxn stands for a small RAII wrapper over a libpq transaction (BEGIN on construction, ROLLBACK in the "
     "destructor unless commit() ran); Example 04 writes the same BEGIN, COMMIT and ROLLBACK with libpq calls "
     "directly. The consumer is process-scoped;", "stack"),
    ("cpp-httplib (header-only, MIT) is the lean HTTP client we picked back in §2; libcurl is the heavier "
     "alternative if you need richer auth or HTTP/2 multiplexing.",
     "cpp-httplib (header-only, MIT, github.com/yhirose/cpp-httplib) is the lean HTTP client; libcurl (curl "
     "license, curl.se) is the heavier alternative when you need richer auth or HTTP/2 multiplexing.", "stack"),
    ("the OpenTelemetry C++ SDK (BSL/Apache 2.0, well-maintained)",
     "the OpenTelemetry C++ SDK (opentelemetry-cpp, Apache 2.0, actively released)", "stack"),
    ("The cpp-stateless deck has the configuration in detail.",
     f"cpp-statelessness Doc 04 shows the BatchSpanProcessor setup ({CS}04-process-scoped-state/).", "stack"),
    ("the OpenTelemetry log appender bridges into the OTel pipeline. Never spdlog::basic_logger_mt — that's a file "
     "sink which dies on read-only rootfs (the cpp-stateless §11 'logs to stdout, not a file' rule).",
     "the spdlog sink in opentelemetry-cpp-contrib bridges into the OTel pipeline. Never spdlog::basic_logger_mt: "
     "that's a file sink which dies on a read-only root filesystem (the 'logs to stdout, not a file' rule of "
     f"cpp-statelessness Doc 08, {CS}08-ephemeral-filesystem/).", "stack"),
    ("For C++: opentelemetry-cpp-contrib has gRPC, libcurl, MySQL client instrumentations; for Drogon and "
     "librdkafka the instrumentation is manual middleware, not auto.",
     "For C++: opentelemetry-cpp-contrib ships log bridges (spdlog, glog, Boost.Log, log4cxx) and nginx and "
     "Apache httpd modules; gRPC, Drogon, librdkafka and libpq spans are written by hand.", "stack"),
    ("the C++ ecosystem covers gRPC, libcurl, MySQL well, but Drogon, librdkafka, libpq, and most C++ frameworks "
     "require you to write the boundary spans yourself.",
     "for C++, opentelemetry-cpp-contrib covers logging bridges and the nginx and httpd modules, while gRPC, "
     "Drogon, librdkafka, libpq and most C++ frameworks need the boundary spans written by hand (opentelemetry-cpp's "
     "examples/grpc shows the context propagation).", "stack"),
    ("Outbound calls (gRPC ClientContext, Kafka producer headers) pick up the trace_id from the active span "
     "automatically via the OTel context propagation API — you don't manually propagate, but you do need to ensure "
     "your gRPC stubs are wrapped with the OTel interceptor (opentelemetry-cpp-contrib provides this for gRPC).",
     "Outbound calls do not pick up the context on their own: inject it with the W3C trace-context propagator into "
     "a carrier (the gRPC ClientContext metadata, the Kafka message headers). opentelemetry-cpp's examples/grpc "
     "shows the carrier; opentelemetry-cpp-contrib has no gRPC interceptor.", "stack"),
    ("The cpp-stateless §6 covers PMR per-request arenas which bound memory per request; bulkheads bound "
     "CONCURRENCY per tenant.",
     f"PMR per-request arenas bound memory per request (cpp-statelessness Doc 03, {CS}03-pmr/); bulkheads bound "
     "concurrency per tenant.", "stack"),
    ("The cpp-stateless compendium covers the per-service in-process state patterns (PMR arenas, RAII connection "
     "pools);",
     "cpp-statelessness covers the per-service in-process state patterns, PMR arenas and RAII connection pools "
     f"({CS}04-process-scoped-state/);", "stack"),
    ("and the cpp-stateless / cpp-container compendiums that accompany this deck.",
     "and two Apache-2.0 companion projects: cpp-statelessness (patterncatalyst.github.io/cpp-statelessness/) on "
     "stateless C++ services in containers, and the C++ container optimization tutorial "
     "(patterncatalyst.github.io/cpp-container-optimization-tutorial/).", "stack"),
    ("The cpp-stateless compendium's port/adapter pattern lets you write the business logic once and adapt to all "
     "three boundaries — but in practice most C++ services pick one or two protocols and commit.",
     "Ports and adapters (Appendix F, Example 19) let you write the business logic once and adapt it to all three "
     "boundaries, though in practice most C++ services pick one or two protocols and commit.", "stack"),
    ("The cpp-stateless port/adapter pattern keeps the business logic clean of any protocol concerns;",
     "The ports-and-adapters structure of Appendix F keeps the business logic clean of any protocol concerns;",
     "stack"),
    ("When you upgrade protobuf itself (e.g., 3.21 → 4.0), every consumer rebuilds against the new stubs "
     "simultaneously. The cpp-stateless §3 Conan lockfile pinning is exactly the mechanism that keeps this "
     "manageable.",
     "When you upgrade protobuf itself to a new major version, every consumer rebuilds against the new stubs at "
     "the same time. A committed Conan lockfile (conan.lock, as every C++ example here has) is the mechanism that "
     f"keeps this manageable; cpp-statelessness Doc 11 shows the profiles around it ({CS}11-build-tooling/).",
     "version"),
    ("for hot paths you can use protobuf arena allocators (Arena::CreateMessage<Envelope>) to amortise that cost. "
     "The cpp-stateless §5 PMR pattern integrates cleanly with protobuf arenas.",
     "for hot paths a protobuf arena (google::protobuf::Arena::Create<Envelope>(&arena); CreateMessage is no "
     "longer public in protobuf 6.33) amortises that cost. Keep the two allocators apart: protobuf messages on "
     "their arena or the default allocator, handler internals on the PMR request arena, with the boundary explicit "
     f"in code review (cpp-statelessness Doc 03, {CS}03-pmr/).", "stack"),
    ("Reuse the cpp-stateless §6 PMR arenas — per-connection allocations clear on disconnect.",
     "Give each connection its own PMR arena (the per-request arena of cpp-statelessness Doc 03, applied to a "
     "connection's lifetime) so its allocations are released on disconnect.", "stack"),
    ("Per-connection state in PMR arenas (cpp-stateless §6):",
     "Per-connection state in a PMR arena (the cpp-statelessness Doc 03 pattern):", "stack"),
    ("If you need in-process retries (a sidecar isn't deployed), library options include hedge-cpp or just "
     "std::this_thread::sleep_for + backoff math.",
     "If you need in-process retries (a sidecar isn't deployed), no widely adopted C++ retry library exists: write "
     "the loop with capped exponential backoff and jitter, as Example 26 does (retry_with_backoff in edge-service).",
     "stack"),
    ("C++ note: cpp-stateless §4 (composition root + adapter pattern) is exactly hexagonal.",
     "C++ note: a composition root in main() wiring adapters into ports (Example 19) is hexagonal architecture.",
     "stack"),
    ("This is the cpp-stateless §4 idiom.",
     f"cpp-statelessness Doc 04 describes the same composition-root idiom ({CS}04-process-scoped-state/).",
     "stack"),
    ("The cpp-stateless §6 PMR-arena pattern is what makes this affordable — you don't pay heap-allocation cost per "
     "aggregate, you pay arena cost per request.",
     "A PMR request arena makes this affordable: you pay arena cost per request instead of a heap allocation per "
     f"aggregate (cpp-statelessness Doc 03, {CS}03-pmr/).", "stack"),
    ("Hexagonal ports & adapters → cpp-stateless composition root + adapter pattern.",
     "Hexagonal ports & adapters → a composition root in main() plus adapters (Example 19).", "stack"),
    ("Conan + lockfile (cpp-stateless §3) pins versions;",
     "Conan + a committed conan.lock pins versions;", "stack"),
    ("The cpp-stateless §9 covers this in detail. This appendix is the architectural framing; the cpp-stateless "
     "deck is the implementation reference. Together they cover the whole discipline.",
     "This appendix is the architectural framing; Example 21 is the runnable C++ version, and cpp-statelessness "
     f"Doc 09 covers the readiness and signal-handling side ({CS}09-health-checks/).", "stack"),
    ("The cpp-stateless §9 covers a complete sequence: stop accepting → drain HTTP → stop Kafka poll → commit "
     "offsets → close DB pool → exit.",
     "A complete sequence: stop accepting → drain HTTP → stop Kafka poll → commit offsets → close DB pool → exit "
     f"(cpp-statelessness Doc 09 walks through the signal-handler side, {CS}09-health-checks/).", "stack"),
    ("The cpp-stateless §11 (and the cpp-statelessness compendium more broadly) addresses this directly:",
     f"cpp-statelessness addresses this directly ({CS}01-deployment-posture/):", "stack"),
    ("The script lives in a ConfigMap or a Git-versioned file; the C++ service watches for changes and re-loads.",
     "The script lives in a ConfigMap or a Git-versioned file (ROUTING_RULES_FILE in Example 22); the service "
     "compiles it once at startup, so a bad script stops the rollout instead of reaching traffic.", "stack"),
    ("Hot-reload story: the cpp-stateless §7 watcher pattern picks up file changes and atomically swaps the loaded "
     "Lua state on a per-request boundary. No restart.",
     "Example 22 changes the rule inputs (thresholds, topics) live through PUT /rules; a new script version ships "
     "as a rollout. A file watcher that swaps in a freshly compiled Lua state between requests is an extension, "
     "not part of the example.", "stack"),
    ("libpq via PgConn from the cpp-stateless §5 pool.",
     "libpq through a PgConn checked out from a process-scoped pool (ScopedConn in cpp-statelessness Doc 07, "
     f"{CS}07-state-externalization/).", "stack"),
    ("The cpp-stateless §9 graceful-shutdown discipline matters more here than anywhere:",
     "Graceful shutdown (Appendix H) matters more here than anywhere:", "stack"),
    ("The cpp-stateless idioms (RAII unwinds, std::stop_token cooperative shutdown) are what make recovery clean.",
     "RAII unwinding and cooperative cancellation with std::stop_token make recovery clean (cpp-statelessness "
     "Docs 02 and 05, patterncatalyst.github.io/cpp-statelessness/).", "stack"),
    ("C++ ecosystem: Hystrix-CPP and breaker-cpp exist but neither dominates.",
     "C++ has no widely adopted circuit-breaker library; Example 26 hand-rolls one (CircuitBreaker in "
     "edge-service).", "stack"),
    ("Unleash is a capable open-source alternative backend behind the same OpenFeature SDK.",
     "Unleash (AGPL-3.0) is an open-source alternative backend; OpenFeature's C++ contrib ships only a flagd "
     "provider, so a C++ service would call Unleash through its own API.", "stack"),
]


def main():
    # sldIds come from the previous run's ops when present (the verify text then already holds the rewrite)
    known = {o["find"]: o["sldIds"][0] for o in load(CPP)["ops"] if o.get("_amend") and o.get("op") == "replace"}
    md = (M / "verify" / f"{CPP}.md").read_text().split("\n")
    cpp_ops = [rep(known.get(f) or sid_of(md, f), f, r, c, why="C++ reference verification (Cpp manifest table)")
               for f, r, c in cpp_pairs]
    n = {
        SPRING: insert(SPRING, spring_ops, spring_drop, spring_patch),
        GO: insert(GO, go_ops),
        CPP: insert(CPP, cpp_ops),
    }
    print(json.dumps(n))


if __name__ == "__main__":
    main()
