#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:8080"
TEMPO="http://localhost:3200"
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
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# --- Place an order (flows through REST → gRPC → Kafka → consumer) ---
printf '  \xe2\x86\x92 placing an order and waiting for traces to flush...\n'
ORDER_JSON=$(curl -sf -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"widget-a","quantity":2}' "$BASE/orders")
ORDER_ID=$(echo "$ORDER_JSON" | jq -r '.id')

check_status "POST /orders returns 201" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget-b\",\"quantity\":1}' $BASE/orders" \
    "201"

check "order has status confirmed (stock reserved via gRPC)" \
    "echo '$ORDER_JSON'" \
    '"confirmed"'

# --- Correlated logs: trace_id in log output ---
sleep 5
TRACE_ID=$(podman logs cndp-order-service 2>&1 | grep "order placed" | grep "$ORDER_ID" | grep -oP 'trace_id=\K[0-9a-f]{32}' | head -1)

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

TEMPO_SEARCH=$(curl -sf "$TEMPO/api/search" 2>/dev/null || echo "")
check "Tempo has traces" \
    "echo '$TEMPO_SEARCH'" \
    "traceID"

TRACE_DATA=$(curl -sf "$TEMPO/api/traces/$TRACE_ID" 2>/dev/null || echo "")
if echo "$TRACE_DATA" | grep -q "order-service"; then
    printf '  \xe2\x9c\x93 trace found in Tempo with order-service spans\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 trace not found in Tempo for trace_id=%s\n' "$TRACE_ID"
    FAIL=$((FAIL + 1))
fi

INVENTORY_TRACES=$(curl -sf "$TEMPO/api/search?tags=service.name%3Dinventory-service&limit=5" 2>/dev/null || echo "")
if echo "$INVENTORY_TRACES" | grep -q "traceID"; then
    printf '  \xe2\x9c\x93 inventory-service gRPC traces found in Tempo\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 inventory-service traces not found in Tempo\n'
    FAIL=$((FAIL + 1))
fi

# --- Metrics in Prometheus ---
printf '  \xe2\x86\x92 checking metrics in Prometheus...\n'
PROM_RESULT=$(curl -sf "http://localhost:9090/api/v1/query?query=orders_placed_total" 2>/dev/null || echo "")
if echo "$PROM_RESULT" | grep -q "order-service"; then
    printf '  \xe2\x9c\x93 orders.placed metric found in Prometheus\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 orders.placed metric not found in Prometheus\n'
    FAIL=$((FAIL + 1))
fi

STOCK_RESULT=$(curl -sf "http://localhost:9090/api/v1/query?query=stock_reservations_total" 2>/dev/null || echo "")
if echo "$STOCK_RESULT" | grep -q "inventory-service"; then
    printf '  \xe2\x9c\x93 stock.reservations metric found in Prometheus\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 stock.reservations metric not found in Prometheus\n'
    FAIL=$((FAIL + 1))
fi

# --- Notification consumer processed (trace propagated across Kafka) ---
sleep 3
check "notification created (trace propagated across Kafka)" \
    "podman exec cndp-postgres psql -U appuser -d appdb -tAc \"SELECT count(*) FROM notifications WHERE order_id='$ORDER_ID'\"" \
    "1"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
