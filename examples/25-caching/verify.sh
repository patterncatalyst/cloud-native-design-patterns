#!/usr/bin/env bash
# shellcheck disable=SC2086  # $CURL_OPTS is intentionally word-split
set -euo pipefail

RUNTIME="${RUNTIME:-docker}"
BASE="${BASE:-http://localhost:8080}"
CURL_OPTS="${CURL_OPTS:-}"

# Container operations go through these helpers so the checks do not hard-code
# an engine. RUNTIME=openshift is added later: a ctr_target function will map
# a container name (cndp-kafka, cndp-postgres, ...) to its pod and each helper
# will call `oc exec` / `oc logs` instead.
case "$RUNTIME" in
    docker) ;;
    *) echo "RUNTIME=$RUNTIME not supported yet" >&2; exit 1 ;;
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

printf '==> Verifying Example 25: Caching Patterns\n\n'

# --- healthz ---
check "healthz returns ok" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status": *"\(ok\|UP\)"'

# ===================================================================
# 1. Cache-aside
# ===================================================================
printf '\n--- 1. Cache-aside ---\n'

check "first read is a DB miss" \
    "curl $CURL_OPTS -sf $BASE/cache-aside/products/p1" \
    '"source":"db"'

check "second read is a cache hit" \
    "curl $CURL_OPTS -sf $BASE/cache-aside/products/p1" \
    '"source":"cache"'

check "returns correct product name" \
    "curl $CURL_OPTS -sf $BASE/cache-aside/products/p1" \
    '"name":"Widget"'

check_status "update returns 200" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/json' \
     -d '{\"name\":\"Widget Pro\",\"price_cents\":1299}' $BASE/cache-aside/products/p1" \
    "200"

check "read after update is a miss (cache invalidated)" \
    "curl $CURL_OPTS -sf $BASE/cache-aside/products/p1" \
    '"source":"db"'

check "updated value is returned" \
    "curl $CURL_OPTS -sf $BASE/cache-aside/products/p1" \
    '"name":"Widget Pro"'

# ===================================================================
# 2. Read-through
# ===================================================================
printf '\n--- 2. Read-through ---\n'

check "read-through returns product" \
    "curl $CURL_OPTS -sf $BASE/read-through/products/p2" \
    '"name":"Gadget"'

check "read-through second read is cached" \
    "curl $CURL_OPTS -sf $BASE/read-through/products/p2" \
    '"source":"cache"'

# ===================================================================
# 3. Write-through
# ===================================================================
printf '\n--- 3. Write-through ---\n'

check_status "write-through update returns 200" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/json' \
     -d '{\"name\":\"Gizmo Deluxe\",\"price_cents\":2999}' $BASE/write-through/products/p3" \
    "200"

check "immediate read after write-through is a cache hit" \
    "curl $CURL_OPTS -sf $BASE/write-through/products/p3" \
    '"source":"cache"'

check "write-through value is correct" \
    "curl $CURL_OPTS -sf $BASE/write-through/products/p3" \
    '"name":"Gizmo Deluxe"'

# ===================================================================
# 4. Write-around
# ===================================================================
printf '\n--- 4. Write-around ---\n'

check_status "write-around POST writes DB only" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
     -d '{\"id\":\"evt-1\",\"type\":\"test\",\"payload\":{\"msg\":\"hello\"}}' $BASE/write-around/events" \
    "200"

check "first read after write-around is a DB miss" \
    "curl $CURL_OPTS -sf $BASE/write-around/events/evt-1" \
    '"source":"db"'

check "second read is a cache hit" \
    "curl $CURL_OPTS -sf $BASE/write-around/events/evt-1" \
    '"source":"cache"'

check "event payload is correct" \
    "curl $CURL_OPTS -sf $BASE/write-around/events/evt-1" \
    '"msg":"hello"'

# ===================================================================
# 5. Write-back (write-behind)
# ===================================================================
printf '\n--- 5. Write-back ---\n'

check_status "write-back PUT returns 202 (queued, not yet durable)" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/json' \
     -d '{\"value\":42.5,\"tags\":{\"host\":\"node-1\"}}' $BASE/write-back/metrics/m1" \
    "202"

check "metric readable from cache immediately" \
    "curl $CURL_OPTS -sf $BASE/write-back/metrics/m1" \
    '"source":"cache"'

printf '  \xe2\x86\x92 waiting for background flusher (3s)...\n'
sleep 3

check "metric flushed to DB" \
    "curl $CURL_OPTS -sf $BASE/write-back/flush-status" \
    '"persisted_rows":1'

# A failed flush is re-queued and retried, not dropped: write while Postgres is down,
# bring it back, and the entry reaches the table.
printf '  \xe2\x86\x92 stopping Postgres to test the flush retry...\n'
ctr_stop cndp-postgres >/dev/null 2>&1

check_status "write-back PUT returns 202 while the DB is down" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/json' \
     -d '{\"value\":7.5,\"tags\":{\"host\":\"node-2\"}}' $BASE/write-back/metrics/m2" \
    "202"

sleep 5
printf '  \xe2\x86\x92 restarting Postgres...\n'
ctr_start cndp-postgres >/dev/null 2>&1
for _ in $(seq 1 45); do
    curl $CURL_OPTS -s $BASE/write-back/flush-status 2>/dev/null | grep -q '"persisted_rows":2' && break
    sleep 2
done

check "failed flush is retried and persisted after the DB recovers" \
    "curl $CURL_OPTS -sf $BASE/write-back/flush-status" \
    '"persisted_rows":2'

check "logs show the failed flush" \
    "ctr_logs cndp-cache-service 2>&1" \
    'flush failed\|flusher error'

# ===================================================================
# 6. Refresh-ahead
# ===================================================================
printf '\n--- 6. Refresh-ahead ---\n'

check "refresh-ahead first read loads from DB" \
    "curl $CURL_OPTS -sf $BASE/refresh-ahead/products/p1" \
    '"source":"db"'

check "refresh-ahead second read is cached" \
    "curl $CURL_OPTS -sf $BASE/refresh-ahead/products/p1" \
    '"source":"cache"'

check "hot set contains the product" \
    "curl $CURL_OPTS -sf $BASE/cache-keys" \
    'product:hot'

# ===================================================================
# 7. Cache outage resilience
# ===================================================================
printf '\n--- 7. Cache outage resilience ---\n'

printf '  \xe2\x86\x92 stopping Redis to test degradation...\n'
ctr_stop cndp-redis >/dev/null 2>&1

check_status "cache-aside still returns 200 with Redis down" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' $BASE/cache-aside/products/p1" \
    "200"

check "reads come from DB when cache is down" \
    "curl $CURL_OPTS -sf $BASE/cache-aside/products/p1" \
    '"source":"db"'

check_status "write-through read still returns 200" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' $BASE/write-through/products/p3" \
    "200"

printf '  \xe2\x86\x92 restarting Redis...\n'
ctr_start cndp-redis >/dev/null 2>&1
sleep 3

check_status "cache-aside works again after Redis restart" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' $BASE/cache-aside/products/p1" \
    "200"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
