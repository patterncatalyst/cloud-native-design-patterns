#!/usr/bin/env bash
# shellcheck disable=SC2086  # $CURL_OPTS is intentionally word-split
set -euo pipefail

RUNTIME="${RUNTIME:-docker}"
BASE="${BASE:-http://localhost:8080}"
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

printf '==> Verifying Example 17: Saga State & Compensation\n\n'

# --- Service is up ---
check "saga-orchestrator healthz" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status": *"\(ok\|UP\)"'

# --- Happy path: all steps succeed ---
printf '  \xe2\x86\x92 testing happy path (all steps succeed)...\n'
HAPPY=$(curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' \
    -d '{"order_id":"order-1","sku":"widget-a","total":29.99}' \
    "$BASE/sagas")
HAPPY_ID=$(echo "$HAPPY" | jq -r '.id')

check "happy path saga status is COMPLETED" \
    "echo '$HAPPY'" \
    '"COMPLETED"'

HAPPY_LOG=$(curl $CURL_OPTS -sf "$BASE/sagas/$HAPPY_ID/log")
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
UNHAPPY=$(curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' \
    -d '{"order_id":"order-2","sku":"widget-b","total":49.99,"fail_shipping":true}' \
    "$BASE/sagas")
UNHAPPY_ID=$(echo "$UNHAPPY" | jq -r '.id')

check "unhappy path saga status is COMPENSATED" \
    "echo '$UNHAPPY'" \
    '"COMPENSATED"'

UNHAPPY_LOG=$(curl $CURL_OPTS -sf "$BASE/sagas/$UNHAPPY_ID/log")

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
ctr_exec cndp-postgres psql -U appuser -d appdb -c \
    "INSERT INTO sagas (id, status, step_index, context) VALUES ('resume-test', 'RUNNING', 1, '{\"order_id\":\"order-3\",\"sku\":\"widget-c\",\"total\":19.99,\"charge_payment\":{\"payment_id\":\"pay-test\",\"amount\":19.99}}')" \
    >/dev/null 2>&1

# Stop and start the same container, whichever language is running: the
# orchestrator must pick the RUNNING saga up from Postgres on startup.
ctr_stop cndp-saga >/dev/null 2>&1
ctr_start cndp-saga >/dev/null 2>&1
RESUMED=""
for _ in $(seq 1 30); do
    RESUMED=$(curl $CURL_OPTS -sf "$BASE/sagas/resume-test" 2>/dev/null) || RESUMED=""
    echo "$RESUMED" | grep -q '"COMPLETED"' && break
    sleep 2
done
check "resumed saga completed after restart" \
    "echo '$RESUMED'" \
    '"COMPLETED"'

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
