#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:8080"
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

printf '==> Verifying Example 17: Saga State & Compensation\n\n'

# --- Service is up ---
check "saga-orchestrator healthz" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# --- Happy path: all steps succeed ---
printf '  \xe2\x86\x92 testing happy path (all steps succeed)...\n'
HAPPY=$(curl -sf -X POST -H 'Content-Type: application/json' \
    -d '{"order_id":"order-1","sku":"widget-a","total":29.99}' \
    "$BASE/sagas")
HAPPY_ID=$(echo "$HAPPY" | jq -r '.id')

check "happy path saga status is COMPLETED" \
    "echo '$HAPPY'" \
    '"COMPLETED"'

HAPPY_LOG=$(curl -sf "$BASE/sagas/$HAPPY_ID/log")
check "happy path: charge_payment executed" \
    "echo '$HAPPY_LOG'" \
    '"charge_payment"'

check "happy path: reserve_stock executed" \
    "echo '$HAPPY_LOG'" \
    '"reserve_stock"'

check "happy path: book_shipping executed" \
    "echo '$HAPPY_LOG'" \
    '"book_shipping"'

# Verify no compensations in happy path
if echo "$HAPPY_LOG" | grep -q '"compensate"'; then
    printf '  \xe2\x9c\x97 happy path should have no compensations\n'
    FAIL=$((FAIL + 1))
else
    printf '  \xe2\x9c\x93 happy path has no compensation steps\n'
    PASS=$((PASS + 1))
fi

# --- Unhappy path: book_shipping fails → compensate in reverse ---
printf '  \xe2\x86\x92 testing unhappy path (shipping fails, triggers compensation)...\n'
UNHAPPY=$(curl -sf -X POST -H 'Content-Type: application/json' \
    -d '{"order_id":"order-2","sku":"widget-b","total":49.99,"fail_shipping":true}' \
    "$BASE/sagas")
UNHAPPY_ID=$(echo "$UNHAPPY" | jq -r '.id')

check "unhappy path saga status is COMPENSATED" \
    "echo '$UNHAPPY'" \
    '"COMPENSATED"'

UNHAPPY_LOG=$(curl -sf "$BASE/sagas/$UNHAPPY_ID/log")

check "unhappy path: book_shipping failed" \
    "echo '$UNHAPPY_LOG'" \
    '"failed"'

# --- Verify compensation order: release_stock then refund_payment (reverse) ---
COMP_STEPS=$(echo "$UNHAPPY_LOG" | jq -r '[.[] | select(.action=="compensate") | .step] | join(",")')
if [ "$COMP_STEPS" = "release_stock,refund_payment" ]; then
    printf '  \xe2\x9c\x93 compensation ran in reverse order: release_stock → refund_payment\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 compensation order wrong (expected "release_stock,refund_payment", got "%s")\n' "$COMP_STEPS"
    FAIL=$((FAIL + 1))
fi

# --- Verify cancel_shipping did NOT run (shipping never completed) ---
if echo "$UNHAPPY_LOG" | jq -r '.[].step' | grep -q "cancel_shipping"; then
    printf '  \xe2\x9c\x97 cancel_shipping should not run (shipping never completed)\n'
    FAIL=$((FAIL + 1))
else
    printf '  \xe2\x9c\x93 cancel_shipping correctly skipped (shipping never completed)\n'
    PASS=$((PASS + 1))
fi

# --- Resume after crash: create a saga, kill orchestrator mid-flow, restart ---
printf '  \xe2\x86\x92 testing resume after crash...\n'
podman exec cndp-postgres psql -U appuser -d appdb -c \
    "INSERT INTO sagas (id, status, step_index, context) VALUES ('resume-test', 'RUNNING', 1, '{\"order_id\":\"order-3\",\"sku\":\"widget-c\",\"total\":19.99,\"charge_payment\":{\"payment_id\":\"pay-test\",\"amount\":19.99}}')" \
    >/dev/null 2>&1

podman restart cndp-saga >/dev/null 2>&1
sleep 10

RESUMED=$(curl -sf "$BASE/sagas/resume-test")
check "resumed saga completed after restart" \
    "echo '$RESUMED'" \
    '"COMPLETED"'

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
