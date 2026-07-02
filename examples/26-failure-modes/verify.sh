#!/usr/bin/env bash
set -euo pipefail

EDGE="http://localhost:8080"
BACKEND="http://localhost:8081"
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
    "curl -sf $EDGE/healthz" \
    '"status":"ok"'

check "backend healthz returns ok" \
    "curl -sf $BACKEND/healthz" \
    '"status":"ok"'

# ===================================================================
# 1. Timeout
# ===================================================================
printf '\n--- 1. Timeout ---\n'

curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "healthy backend returns ok via timeout endpoint" \
    "curl -sf $EDGE/with-timeout" \
    '"status":200'

printf '  \xe2\x86\x92 setting backend to slow mode (5s delay)...\n'
curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"slow"}' "$BACKEND/mode" >/dev/null

check "slow backend triggers timeout (< 3s elapsed)" \
    "curl -sf --max-time 10 $EDGE/with-timeout" \
    '"error":"timeout"'

# Verify it failed fast (< 3s, not 5s)
ELAPSED=$(curl -sf --max-time 10 "$EDGE/with-timeout" | grep -o '"elapsed_s":[0-9.]*' | cut -d: -f2)
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

curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "healthy backend succeeds in 1 attempt" \
    "curl -sf $EDGE/with-retry" \
    '"attempts":1'

curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"failing"}' "$BACKEND/mode" >/dev/null

check "failing backend exhausts all 3 retry attempts" \
    "curl -sf --max-time 15 $EDGE/with-retry" \
    '"attempts":3'

check "retry-exhausted response explains what happened" \
    "curl -sf --max-time 15 $EDGE/with-retry" \
    '"pattern":"retry-exhausted"'

# Check backend call count shows retries happened
CALL_COUNT=$(curl -sf "$BACKEND/mode" | grep -o '"call_count":[0-9]*' | cut -d: -f2)
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

curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "breaker starts closed" \
    "curl -sf $EDGE/breaker-state" \
    '"state":"closed"'

curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"failing"}' "$BACKEND/mode" >/dev/null

printf '  \xe2\x86\x92 sending 6 requests to trip the breaker...\n'
for i in $(seq 1 6); do
    curl -sf "$EDGE/with-breaker" >/dev/null 2>&1
done

check "breaker is now open after failures" \
    "curl -sf $EDGE/breaker-state" \
    '"state":"open"'

check "open breaker returns fallback without calling backend" \
    "curl -sf $EDGE/with-breaker" \
    '"reason":"circuit_open"'

check "fallback response includes breaker state" \
    "curl -sf $EDGE/with-breaker" \
    '"source":"fallback"'

# Record call count before fallback calls
BEFORE=$(curl -sf "$BACKEND/mode" | grep -o '"call_count":[0-9]*' | cut -d: -f2)

# Make a few more calls — should NOT hit backend
for i in $(seq 1 3); do
    curl -sf "$EDGE/with-breaker" >/dev/null 2>&1
done

AFTER=$(curl -sf "$BACKEND/mode" | grep -o '"call_count":[0-9]*' | cut -d: -f2)
if [ "$BEFORE" = "$AFTER" ]; then
    printf '  \xe2\x9c\x93 open breaker did not call backend (count stayed at %s)\n' "$BEFORE"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 open breaker should not call backend (count changed %s → %s)\n' "$BEFORE" "$AFTER"
    FAIL=$((FAIL + 1))
fi

# --- Breaker recovery ---
printf '  \xe2\x86\x92 restoring backend and waiting for breaker reset (11s)...\n'
curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null
sleep 11

# First call after reset should trigger half-open → trial
curl -sf "$EDGE/with-breaker" >/dev/null 2>&1
curl -sf "$EDGE/with-breaker" >/dev/null 2>&1
curl -sf "$EDGE/with-breaker" >/dev/null 2>&1

check "breaker recovered to closed after successful trials" \
    "curl -sf $EDGE/breaker-state" \
    '"state":"closed"'

# ===================================================================
# 4. Deadline propagation
# ===================================================================
printf '\n--- 4. Deadline propagation ---\n'

curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "ample budget (1000ms) succeeds" \
    "curl -sf '$EDGE/with-deadline?budget_ms=1000'" \
    '"status":200'

check "tiny budget (120ms) rejected by backend (70ms remaining)" \
    "curl -sf '$EDGE/with-deadline?budget_ms=120'" \
    '"deadline_too_small"'

check "very small budget (80ms) rejected at edge" \
    "curl -sf '$EDGE/with-deadline?budget_ms=80'" \
    '"insufficient budget at edge"'

# ===================================================================
# 5. Bulkhead
# ===================================================================
printf '\n--- 5. Bulkhead ---\n'

curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"mode":"healthy"}' "$BACKEND/mode" >/dev/null

check "bulkhead allows normal request" \
    "curl -sf $EDGE/with-bulkhead" \
    '"status":200'

check "bulkhead state shows max concurrent 5" \
    "curl -sf $EDGE/bulkhead-state" \
    '"max_concurrent":5'

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
