#!/usr/bin/env bash
# shellcheck disable=SC2086  # $CURL_OPTS is intentionally word-split
set -euo pipefail

RUNTIME="${RUNTIME:-docker}"
BASE="${BASE:-http://localhost:8080}"
EDGE="${EDGE:-$BASE}"
BACKEND="${BACKEND:-http://localhost:8081}"
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

check_not() {
    local desc="$1" cmd="$2" not_expected="$3"
    result=$(eval "$cmd" 2>/dev/null) || result=""
    if echo "$result" | grep -q "$not_expected"; then
        printf '  \xe2\x9c\x97 %s (should NOT contain "%s")\n' "$desc" "$not_expected"
        FAIL=$((FAIL + 1))
    else
        printf '  \xe2\x9c\x93 %s\n' "$desc"
        PASS=$((PASS + 1))
    fi
}

printf '==> Verifying Example 26: Failure Modes\n\n'

# --- Services healthy ---
check "edge healthz returns ok" \
    "curl $CURL_OPTS -sf $EDGE/healthz" \
    '"status": *"\(ok\|UP\)"'

check "backend healthz returns ok" \
    "curl $CURL_OPTS -sf $BACKEND/healthz" \
    '"status": *"\(ok\|UP\)"'

# ===================================================================
# 1. Timeout
# ===================================================================
printf '\n--- 1. Timeout ---\n'

curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "healthy backend returns ok via timeout endpoint" \
    "curl $CURL_OPTS -sf $EDGE/with-timeout" \
    '"status":200'

printf '  \xe2\x86\x92 setting backend to slow mode (5s delay)...\n'
curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"slow"}' "$BACKEND/mode" >/dev/null

check "slow backend triggers timeout (< 3s elapsed)" \
    "curl $CURL_OPTS -sf --max-time 10 $EDGE/with-timeout" \
    '"error":"timeout"'

# Verify it failed fast (< 3s, not 5s)
ELAPSED=$(curl $CURL_OPTS -sf --max-time 10 "$EDGE/with-timeout" | grep -o '"elapsed_s":[0-9.]*' | cut -d: -f2)
if [ -n "$ELAPSED" ] && [ "$(echo "$ELAPSED < 3" | bc -l)" = "1" ]; then
    printf '  \xe2\x9c\x93 timeout elapsed < 3s (was %ss)\n' "$ELAPSED"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 timeout should complete in < 3s (got %ss)\n' "${ELAPSED:-unknown}"
    FAIL=$((FAIL + 1))
fi

# ===================================================================
# 2. Retry with backoff
# ===================================================================
printf '\n--- 2. Retry with backoff ---\n'

curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "healthy backend succeeds in 1 attempt" \
    "curl $CURL_OPTS -sf $EDGE/with-retry" \
    '"attempts":1'

curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"failing"}' "$BACKEND/mode" >/dev/null

check "failing backend exhausts all 3 retry attempts" \
    "curl $CURL_OPTS -sf --max-time 15 $EDGE/with-retry" \
    '"attempts":3'

check "retry-exhausted response explains what happened" \
    "curl $CURL_OPTS -sf --max-time 15 $EDGE/with-retry" \
    '"pattern":"retry-exhausted"'

# Check backend call count shows retries happened
CALL_COUNT=$(curl $CURL_OPTS -sf "$BACKEND/mode" | grep -o '"call_count":[0-9]*' | cut -d: -f2)
if [ -n "$CALL_COUNT" ] && [ "$CALL_COUNT" -ge 6 ]; then
    printf '  \xe2\x9c\x93 backend received %d calls (retries happening)\n' "$CALL_COUNT"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 expected >= 6 backend calls (got %s)\n' "${CALL_COUNT:-0}"
    FAIL=$((FAIL + 1))
fi

# ===================================================================
# 3. Circuit breaker
# ===================================================================
printf '\n--- 3. Circuit breaker ---\n'

curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "breaker starts closed" \
    "curl $CURL_OPTS -sf $EDGE/breaker-state" \
    '"state":"closed"'

curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"failing"}' "$BACKEND/mode" >/dev/null

printf '  \xe2\x86\x92 sending 6 requests to trip the breaker...\n'
for _ in $(seq 1 6); do
    curl $CURL_OPTS -sf "$EDGE/with-breaker" >/dev/null 2>&1
done

check "breaker is now open after failures" \
    "curl $CURL_OPTS -sf $EDGE/breaker-state" \
    '"state":"open"'

check "open breaker returns fallback without calling backend" \
    "curl $CURL_OPTS -sf $EDGE/with-breaker" \
    '"reason":"circuit_open"'

check "fallback response includes breaker state" \
    "curl $CURL_OPTS -sf $EDGE/with-breaker" \
    '"source":"fallback"'

# Record call count before fallback calls
BEFORE=$(curl $CURL_OPTS -sf "$BACKEND/mode" | grep -o '"call_count":[0-9]*' | cut -d: -f2)

# Make a few more calls — should NOT hit backend
for _ in $(seq 1 3); do
    curl $CURL_OPTS -sf "$EDGE/with-breaker" >/dev/null 2>&1
done

AFTER=$(curl $CURL_OPTS -sf "$BACKEND/mode" | grep -o '"call_count":[0-9]*' | cut -d: -f2)
if [ "$BEFORE" = "$AFTER" ]; then
    printf '  \xe2\x9c\x93 open breaker did not call backend (count stayed at %s)\n' "$BEFORE"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 open breaker should not call backend (count changed %s → %s)\n' "$BEFORE" "$AFTER"
    FAIL=$((FAIL + 1))
fi

# --- Breaker recovery ---
printf '  \xe2\x86\x92 restoring backend; the breaker stays open 10s, then trial calls close it...\n'
curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null
sleep 10

# Poll rather than wait a fixed time: the libraries end the open period at slightly different moments, and the
# first call after it is the half-open trial (Polly closes after one success, the others after two). A call made
# while the breaker is still open only gets the fallback, so polling is harmless. Give up after 20 s.
for _ in $(seq 1 20); do
    curl $CURL_OPTS -sf "$EDGE/with-breaker" >/dev/null 2>&1
    curl $CURL_OPTS -sf "$EDGE/breaker-state" 2>/dev/null | grep -q '"state":"closed"' && break
    sleep 1
done

check "breaker recovered to closed after successful trials" \
    "curl $CURL_OPTS -sf $EDGE/breaker-state" \
    '"state":"closed"'

# ===================================================================
# 4. Deadline propagation
# ===================================================================
printf '\n--- 4. Deadline propagation ---\n'

curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "ample budget (1000ms) succeeds" \
    "curl $CURL_OPTS -sf '$EDGE/with-deadline?budget_ms=1000'" \
    '"status":200'

check "tiny budget (120ms) rejected by backend (70ms remaining)" \
    "curl $CURL_OPTS -sf '$EDGE/with-deadline?budget_ms=120'" \
    '"deadline_too_small"'

check "very small budget (80ms) rejected at edge" \
    "curl $CURL_OPTS -sf '$EDGE/with-deadline?budget_ms=80'" \
    '"insufficient budget at edge"'

# ===================================================================
# 5. Bulkhead
# ===================================================================
printf '\n--- 5. Bulkhead ---\n'

curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "bulkhead allows normal request" \
    "curl $CURL_OPTS -sf $EDGE/with-bulkhead" \
    '"status":200'

check "bulkhead state shows max concurrent 5" \
    "curl $CURL_OPTS -sf $EDGE/bulkhead-state" \
    '"max_concurrent":5'

# Saturate it: 8 concurrent calls against a slow backend hold all 5 permits, so the rest are turned away at once.
printf '  \xe2\x86\x92 sending 8 concurrent requests against a slow backend...\n'
curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"slow"}' "$BACKEND/mode" >/dev/null
CODES=$(mktemp)
for _ in $(seq 1 8); do
    curl $CURL_OPTS -s -o /dev/null -w '%{http_code}\n' --max-time 10 "$EDGE/with-bulkhead" >>"$CODES" &
done
wait
REJECTED=$(grep -c '^429$' "$CODES" || true)
rm -f "$CODES"

check "full bulkhead rejects the overflow with 429" \
    "echo $REJECTED" \
    '^[1-9]'

curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "bulkhead admits requests again once the calls finish" \
    "curl $CURL_OPTS -sf $EDGE/with-bulkhead" \
    '"status":200'

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
