#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:8080"
PASS=0
FAIL=0

check() {
    local desc="$1" cmd="$2" expected="$3"
    result=$(eval "$cmd" 2>/dev/null) || result=""
    if echo "$result" | grep -q "$expected"; then
        printf '  ✓ %s\n' "$desc"
        PASS=$((PASS + 1))
    else
        printf '  ✗ %s (expected "%s", got "%s")\n' "$desc" "$expected" "$result"
        FAIL=$((FAIL + 1))
    fi
}

printf '==> Verifying Example 01: Cloud-Native Principles\n\n'

# Factor III — config from environment
check "root returns service name from config" \
    "curl -sf $BASE/" \
    '"service":"order-service"'

check "root returns version from SERVICE_VERSION env" \
    "curl -sf $BASE/" \
    '"version":"1.0.0"'

check "root confirms config source is environment" \
    "curl -sf $BASE/" \
    '"config_source":"environment"'

# Liveness probe
check "liveness probe returns ok" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# Readiness probe (DB is up)
check "readiness probe returns ready when DB is up" \
    "curl -sf $BASE/readyz" \
    '"status":"ready"'

# CRUD — create and list
check "create order returns id" \
    "curl -sf -X POST '$BASE/orders?customer=alice&total=42.50'" \
    '"id"'

check "list orders returns created order" \
    "curl -sf $BASE/orders" \
    '"customer":"alice"'

# Readiness flips when DB goes down
printf '\n  → stopping postgres to test readiness flip...\n'
podman stop cndp-postgres >/dev/null 2>&1 || docker stop cndp-postgres >/dev/null 2>&1
sleep 2

check "readiness returns down when DB is stopped" \
    "curl -sf $BASE/readyz" \
    '"status":"down"'

check "liveness still returns ok when DB is stopped" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# Restart DB
printf '  → restarting postgres...\n'
podman start cndp-postgres >/dev/null 2>&1 || docker start cndp-postgres >/dev/null 2>&1
sleep 5

check "readiness recovers after DB restart" \
    "curl -sf $BASE/readyz" \
    '"status":"ready"'

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
