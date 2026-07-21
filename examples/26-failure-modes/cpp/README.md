# Example 26 — Failure Modes (C++)

Demonstrates five resilience patterns with two services:

1. **Timeout** — Edge service calls backend with 2-second timeout; slow backend (5s sleep) triggers timeout
2. **Retry with exponential backoff** — Up to 3 attempts with exponential backoff (100ms, 200ms, 400ms) and jitter
3. **Circuit breaker** — Tracks failures; opens after 5 consecutive failures; half-open after 10s timeout; requires 2 successful trials to close
4. **Deadline propagation** — Edge propagates `X-Deadline-Ms` header to backend; backend rejects if deadline < 100ms
5. **Bulkhead** — Limits concurrent backend calls to 5; additional requests rejected with 503

## Architecture

- **Edge service** (port 8080): Drogon + libcurl for HTTP client
- **Backend service** (port 8081): Drogon with controllable failure modes (healthy, slow, failing, flaky)

## Running

```bash
podman compose up --build
```

Services start on ports 8080 (edge) and 8081 (backend). Healthchecks confirm readiness.

## Testing

See `../verify.sh` for the full test suite. Quick manual tests:

```bash
# 1. Timeout — backend in slow mode (5s sleep)
curl -X POST http://localhost:8081/mode -H 'Content-Type: application/json' -d '{"mode":"slow"}'
curl http://localhost:8080/with-timeout
# → {"error":"timeout", "elapsed_s":<2.x, "pattern":"timeout"}

# 2. Retry — backend in failing mode
curl -X POST http://localhost:8081/mode -d '{"mode":"failing"}'
curl http://localhost:8080/with-retry
# → {"error":"http_error", "attempts":3, "pattern":"retry-exhausted"}

# 3. Circuit breaker — trip it with 5+ failures
curl -X POST http://localhost:8081/mode -d '{"mode":"failing"}'
for i in {1..6}; do curl http://localhost:8080/with-breaker; done
curl http://localhost:8080/breaker-state
# → {"state":"open", ...}

# Circuit recovers after 10s + 2 successful trials
curl -X POST http://localhost:8081/mode -d '{"mode":"healthy"}'
sleep 11
curl http://localhost:8080/with-breaker  # half-open, trial 1
curl http://localhost:8080/with-breaker  # trial 2 → closed

# 4. Deadline propagation
curl 'http://localhost:8080/with-deadline?budget_ms=1000'
# → {"status":200, ...}
curl 'http://localhost:8080/with-deadline?budget_ms=80'
# → {"error":"insufficient budget at edge"}
curl 'http://localhost:8080/with-deadline?budget_ms=120'
# → {"error":"backend_rejected_deadline", "body":{"reason":"deadline_too_small"}}

# 5. Bulkhead — saturate with concurrent requests
curl http://localhost:8080/bulkhead-state
# → {"max_concurrent":5, "active":0, "rejected":0}
```

## Observability

LGTM stack (Grafana, Tempo, Loki, Mimir) available at `http://localhost:3000` (admin/admin).
Services export traces to OTLP endpoint `http://lgtm:4318`.

## Cleanup

```bash
podman compose down -v
```
