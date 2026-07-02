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

printf '==> Verifying Example 25: Caching Patterns\n\n'

# --- healthz ---
check "healthz returns ok" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# ===================================================================
# 1. Cache-aside
# ===================================================================
printf '\n--- 1. Cache-aside ---\n'

check "first read is a DB miss" \
    "curl -sf $BASE/cache-aside/products/p1" \
    '"source":"db"'

check "second read is a cache hit" \
    "curl -sf $BASE/cache-aside/products/p1" \
    '"source":"cache"'

check "returns correct product name" \
    "curl -sf $BASE/cache-aside/products/p1" \
    '"name":"Widget"'

check_status "update returns 200" \
    "curl -s -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/json' \
     -d '{\"name\":\"Widget Pro\",\"price_cents\":1299}' $BASE/cache-aside/products/p1" \
    "200"

check "read after update is a miss (cache invalidated)" \
    "curl -sf $BASE/cache-aside/products/p1" \
    '"source":"db"'

check "updated value is returned" \
    "curl -sf $BASE/cache-aside/products/p1" \
    '"name":"Widget Pro"'

# ===================================================================
# 2. Read-through
# ===================================================================
printf '\n--- 2. Read-through ---\n'

check "read-through returns product" \
    "curl -sf $BASE/read-through/products/p2" \
    '"name":"Gadget"'

check "read-through second read is cached" \
    "curl -sf $BASE/read-through/products/p2" \
    '"source":"cache"'

# ===================================================================
# 3. Write-through
# ===================================================================
printf '\n--- 3. Write-through ---\n'

check_status "write-through update returns 200" \
    "curl -s -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/json' \
     -d '{\"name\":\"Gizmo Deluxe\",\"price_cents\":2999}' $BASE/write-through/products/p3" \
    "200"

check "immediate read after write-through is a cache hit" \
    "curl -sf $BASE/write-through/products/p3" \
    '"source":"cache"'

check "write-through value is correct" \
    "curl -sf $BASE/write-through/products/p3" \
    '"name":"Gizmo Deluxe"'

# ===================================================================
# 4. Write-around
# ===================================================================
printf '\n--- 4. Write-around ---\n'

check_status "write-around POST writes DB only" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
     -d '{\"id\":\"evt-1\",\"type\":\"test\",\"payload\":{\"msg\":\"hello\"}}' $BASE/write-around/events" \
    "200"

check "first read after write-around is a DB miss" \
    "curl -sf $BASE/write-around/events/evt-1" \
    '"source":"db"'

check "second read is a cache hit" \
    "curl -sf $BASE/write-around/events/evt-1" \
    '"source":"cache"'

check "event payload is correct" \
    "curl -sf $BASE/write-around/events/evt-1" \
    '"msg":"hello"'

# ===================================================================
# 5. Write-back (write-behind)
# ===================================================================
printf '\n--- 5. Write-back ---\n'

check_status "write-back PUT returns 200" \
    "curl -s -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/json' \
     -d '{\"value\":42.5,\"tags\":{\"host\":\"node-1\"}}' $BASE/write-back/metrics/m1" \
    "200"

check "metric readable from cache immediately" \
    "curl -sf $BASE/write-back/metrics/m1" \
    '"source":"cache"'

printf '  \xe2\x86\x92 waiting for background flusher (3s)...\n'
sleep 3

check "metric flushed to DB" \
    "curl -sf $BASE/write-back/flush-status" \
    '"persisted_rows":1'

# ===================================================================
# 6. Refresh-ahead
# ===================================================================
printf '\n--- 6. Refresh-ahead ---\n'

check "refresh-ahead first read loads from DB" \
    "curl -sf $BASE/refresh-ahead/products/p1" \
    '"source":"db"'

check "refresh-ahead second read is cached" \
    "curl -sf $BASE/refresh-ahead/products/p1" \
    '"source":"cache"'

check "hot set contains the product" \
    "curl -sf $BASE/cache-keys" \
    'product:hot'

# ===================================================================
# 7. Cache outage resilience
# ===================================================================
printf '\n--- 7. Cache outage resilience ---\n'

printf '  \xe2\x86\x92 stopping Redis to test degradation...\n'
podman stop cndp-redis >/dev/null 2>&1

check_status "cache-aside still returns 200 with Redis down" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE/cache-aside/products/p1" \
    "200"

check "reads come from DB when cache is down" \
    "curl -sf $BASE/cache-aside/products/p1" \
    '"source":"db"'

check_status "write-through read still returns 200" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE/write-through/products/p3" \
    "200"

printf '  \xe2\x86\x92 restarting Redis...\n'
podman start cndp-redis >/dev/null 2>&1
sleep 3

check_status "cache-aside works again after Redis restart" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE/cache-aside/products/p1" \
    "200"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
