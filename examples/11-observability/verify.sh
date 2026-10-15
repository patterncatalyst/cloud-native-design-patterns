#!/usr/bin/env bash
# shellcheck disable=SC2086  # $CURL_OPTS is intentionally word-split
set -euo pipefail

RUNTIME="${RUNTIME:-docker}"
BASE="${BASE:-http://localhost:8080}"
TEMPO="${TEMPO:-http://localhost:3200}"
CURL_OPTS="${CURL_OPTS:-}"

# Container operations go through these helpers so the checks do not hard-code
# an engine. This example runs on Docker Compose only (RUNTIME=docker); Example 05's
# verify.sh shows the RUNTIME=kubernetes variant used on minikube and OpenShift Local.
case "$RUNTIME" in
    docker) ;;
    *) echo "RUNTIME=$RUNTIME not supported (docker)" >&2; exit 1 ;;
esac
ctr_exec()    { docker exec "$@"; }
ctr_logs()    { docker logs "$@"; }
ctr_stop()    { docker stop "$@"; }
ctr_start()   { docker start "$@"; }
ctr_rm()      { docker rm "$@"; }
ctr_kill()    { docker kill --signal "${2:-KILL}" "$1"; }  # ctr_kill <container> [signal]
ctr_pause()   { docker pause "$@"; }
ctr_unpause() { docker unpause "$@"; }
ctr_compose() { docker compose "$@"; }

PASS=0
FAIL=0

check() {
    local desc="$1" cmd="$2" expected="$3"
    result=$(eval "$cmd" 2>/dev/null) || result=""
    if echo "$result" | grep -q "$expected"; then
        printf '  \xe2\x9c\x93 %s\n' "$desc"
        PASS=$((PASS + 1))
    else
        printf '  \xe2\x9c\x97 %s (expected "%s", got "%s")\n' "$desc" "$expected" "$result"
        FAIL=$((FAIL + 1))
    fi
}

check_status() {
    local desc="$1" cmd="$2" expected_code="$3"
    status=$(eval "$cmd" 2>/dev/null) || status=""
    if [ "$status" = "$expected_code" ]; then
        printf '  \xe2\x9c\x93 %s\n' "$desc"
        PASS=$((PASS + 1))
    else
        printf '  \xe2\x9c\x97 %s (expected %s, got %s)\n' "$desc" "$expected_code" "$status"
        FAIL=$((FAIL + 1))
    fi
}

printf '==> Verifying Example 11: Observability\n\n'

# --- Services are up ---
check "order-service healthz" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status": *"\(ok\|UP\)"'

# --- Place an order (flows through REST → gRPC → Kafka → consumer) ---
printf '  \xe2\x86\x92 placing an order and waiting for traces to flush...\n'
ORDER_JSON=$(curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"widget-a","quantity":2}' "$BASE/orders")
ORDER_ID=$(echo "$ORDER_JSON" | jq -r '.id')

check_status "POST /orders returns 201" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget-b\",\"quantity\":1}' $BASE/orders" \
    "201"

check "order has status confirmed (stock reserved via gRPC)" \
    "echo '$ORDER_JSON'" \
    '"confirmed"'

# --- Correlated logs: trace_id in log output ---
sleep 5
TRACE_ID=$(ctr_logs cndp-order-service 2>&1 | grep "order placed" | grep "$ORDER_ID" | grep -oP 'trace_id=\K[0-9a-f]{32}' | head -1)

if [ -n "$TRACE_ID" ]; then
    printf '  \xe2\x9c\x93 trace_id found in correlated log line: %s\n' "$TRACE_ID"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 no trace_id found in order-service log lines\n'
    FAIL=$((FAIL + 1))
    TRACE_ID="00000000000000000000000000000000"
fi

# --- Wait for OTel to batch and export ---
sleep 10

# --- Traces in Tempo ---
printf '  \xe2\x86\x92 checking traces in Tempo...\n'

# Tempo 3 indexes new traces a little later than the trace-by-id path, and a search needs
# a time window. Retry for up to 60 s.
TEMPO_SEARCH=""
for _ in $(seq 1 12); do
    NOW=$(date +%s)
    TEMPO_SEARCH=$(curl $CURL_OPTS -sf "$TEMPO/api/search?tags=service.name%3Dorder-service&limit=20&start=$((NOW - 900))&end=$((NOW + 60))" 2>/dev/null || echo "")
    case "$TEMPO_SEARCH" in *traceID*) break ;; esac
    sleep 5
done
check "Tempo search finds traces of service order-service" \
    "echo '$TEMPO_SEARCH'" \
    "traceID"

TRACE_DATA=$(curl $CURL_OPTS -sf "$TEMPO/api/traces/$TRACE_ID" 2>/dev/null || echo "")
if echo "$TRACE_DATA" | grep -q "order-service"; then
    printf '  \xe2\x9c\x93 trace found in Tempo with order-service spans\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 trace not found in Tempo for trace_id=%s\n' "$TRACE_ID"
    FAIL=$((FAIL + 1))
fi

# The inventory span must be part of THIS order's trace (traceparent carried over gRPC),
# not just any inventory trace that happens to exist in Tempo.
if echo "$TRACE_DATA" | tr -d ' \n' | grep -Eq '"key":"service.name","value":\{"stringValue":"inventory-service"'; then
    printf '  \xe2\x9c\x93 inventory-service span is inside the order trace %s\n' "$TRACE_ID"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 inventory-service span not found in the order trace %s\n' "$TRACE_ID"
    FAIL=$((FAIL + 1))
fi

# --- Metrics in Prometheus ---
# Metric exporters push on their own interval (60s by default for the Spring
# Boot and .NET SDKs), so poll instead of checking once.
prom_has() {
    local query="$1" label="$2" deadline=$((SECONDS + 90))
    while [ "$SECONDS" -lt "$deadline" ]; do
        curl $CURL_OPTS -sf "http://localhost:19090/api/v1/query?query=$query" 2>/dev/null | grep -q "$label" && return 0
        sleep 5
    done
    return 1
}

printf '  \xe2\x86\x92 checking metrics in Prometheus (up to 90s each)...\n'
if prom_has orders_placed_total order-service; then
    printf '  \xe2\x9c\x93 orders.placed metric found in Prometheus\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 orders.placed metric not found in Prometheus\n'
    FAIL=$((FAIL + 1))
fi

if prom_has stock_reservations_total inventory-service; then
    printf '  \xe2\x9c\x93 stock.reservations metric found in Prometheus\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 stock.reservations metric not found in Prometheus\n'
    FAIL=$((FAIL + 1))
fi

# --- Notification consumer processed (trace propagated across Kafka) ---
sleep 3
check "notification created (trace propagated across Kafka)" \
    "ctr_exec cndp-postgres psql -U appuser -d appdb -tAc \"SELECT count(*) FROM notifications WHERE order_id='$ORDER_ID'\"" \
    "1"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
