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

printf '==> Verifying Example 21: Graceful Shutdown\n\n'

# --- Service is up ---
check "healthz returns ok" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

check_status "readyz returns 200 (ready)" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE/readyz" \
    "200"

# --- Place some orders to confirm service works ---
check_status "POST /orders returns 201" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget\",\"quantity\":1}' $BASE/orders" \
    "201"

# --- Send SIGTERM and verify readiness flips ---
printf '  \xe2\x86\x92 sending SIGTERM to order-service...\n'
podman exec cndp-order-service kill -SIGTERM 1
sleep 2

check "debug/state shows shutting_down=true" \
    "curl -sf $BASE/debug/state" \
    '"shutting_down":true'

check_status "readyz returns 503 after SIGTERM" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE/readyz" \
    "503"

check "readyz body says shutting down" \
    "curl -sf $BASE/readyz 2>/dev/null || curl -s $BASE/readyz" \
    '"shutting down"'

# --- Verify logs show the drain protocol ---
LOGS=$(podman logs cndp-order-service 2>&1)
check "logs show SIGTERM received" \
    "echo '$LOGS'" \
    "SIGTERM received"

# --- Restart and verify recovery ---
printf '  \xe2\x86\x92 restarting service and verifying recovery...\n'
podman restart cndp-order-service >/dev/null 2>&1
sleep 10

check_status "readyz returns 200 after restart" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE/readyz" \
    "200"

check_status "POST /orders works after restart" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget\",\"quantity\":1}' $BASE/orders" \
    "201"

# --- Verify previous orders survived the restart ---
check "orders from before restart are still present" \
    "curl -sf $BASE/orders" \
    '"widget"'

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
