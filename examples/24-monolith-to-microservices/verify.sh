#!/usr/bin/env bash
# shellcheck disable=SC2086  # $CURL_OPTS is intentionally word-split
set -euo pipefail

RUNTIME="${RUNTIME:-docker}"
BASE="${BASE:-http://localhost:8080}"
ROUTER="${ROUTER:-$BASE}"
DECORATOR="${DECORATOR:-http://localhost:8091}"
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

printf '==> Verifying Example 24: Monolith to Microservices\n\n'

# ===================================================================
# 1. Content-based router
# ===================================================================
printf -- '--- 1. Content-based routing ---\n'

check "router healthz" \
    "curl $CURL_OPTS -sf $ROUTER/healthz" \
    '"status": *"\(ok\|UP\)"'

check "tenant=acme routes to new-service" \
    "curl $CURL_OPTS -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1,\"tenant\":\"acme\"}'" \
    '"source":"new-service"'

check "no tenant routes to monolith" \
    "curl $CURL_OPTS -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1,\"tenant\":\"other\"}'" \
    '"source":"monolith"'

check "default (empty tenant) routes to monolith" \
    "curl $CURL_OPTS -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1}'" \
    '"source":"monolith"'

# ===================================================================
# 2. Reversibility — flip and flip back
# ===================================================================
printf '\n--- 2. Reversibility ---\n'

curl $CURL_OPTS -sf -X PUT "$ROUTER/rules" \
    -H 'Content-Type: application/json' \
    -d '{"tenant_routes":{"acme":"monolith","beta":"new-service"},"default":"monolith"}' >/dev/null 2>&1

check "after flip: acme now routes to monolith" \
    "curl $CURL_OPTS -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1,\"tenant\":\"acme\"}'" \
    '"source":"monolith"'

check "after flip: beta routes to new-service" \
    "curl $CURL_OPTS -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1,\"tenant\":\"beta\"}'" \
    '"source":"new-service"'

curl $CURL_OPTS -sf -X PUT "$ROUTER/rules" \
    -H 'Content-Type: application/json' \
    -d '{"tenant_routes":{"acme":"new-service"},"default":"monolith"}' >/dev/null 2>&1

check "after flip-back: acme returns to new-service" \
    "curl $CURL_OPTS -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1,\"tenant\":\"acme\"}'" \
    '"source":"new-service"'

check "after flip-back: beta returns to monolith" \
    "curl $CURL_OPTS -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1,\"tenant\":\"beta\"}'" \
    '"source":"monolith"'

# ===================================================================
# 3. Decorating collaborator — cache
# ===================================================================
printf '\n--- 3. Decorating collaborator (cache) ---\n'

check "decorator healthz" \
    "curl $CURL_OPTS -sf $DECORATOR/healthz" \
    '"status": *"\(ok\|UP\)"'

# Create an order through the decorator
DEC_ORDER=$(curl $CURL_OPTS -sf -X POST "$DECORATOR/orders" \
    -H 'Content-Type: application/json' \
    -d '{"sku":"cached-item","quantity":2,"tenant":"test"}' 2>/dev/null) || DEC_ORDER=""
DEC_ID=$(echo "$DEC_ORDER" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null) || DEC_ID=""

if [ -z "$DEC_ID" ]; then
    printf '  \xe2\x9c\x97 decorator POST /orders failed\n'
    FAIL=$((FAIL + 1))
else
    printf '  \xe2\x9c\x93 decorator POST created order id=%s\n' "$DEC_ID"
    PASS=$((PASS + 1))

    # First GET — cache miss, legacy sees the call
    curl $CURL_OPTS -sf "$DECORATOR/orders/$DEC_ID" >/dev/null 2>&1

    # Second GET — should be cache hit, legacy should NOT see another call
    curl $CURL_OPTS -sf "$DECORATOR/orders/$DEC_ID" >/dev/null 2>&1

    curl $CURL_OPTS -sf "$DECORATOR/orders/$DEC_ID" >/dev/null 2>&1 || true

    # Check legacy access count — should be 1 (first GET only)
    LEGACY_ACCESS=$(ctr_exec cndp-legacy curl $CURL_OPTS -sf "http://localhost:8080/access-count/$DEC_ID" 2>/dev/null) || LEGACY_ACCESS=""
    ACCESS_NUM=$(echo "$LEGACY_ACCESS" | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])" 2>/dev/null) || ACCESS_NUM=""

    if [ "$ACCESS_NUM" = "1" ]; then
        printf '  \xe2\x9c\x93 cache works: legacy saw 1 GET (second served from cache)\n'
        PASS=$((PASS + 1))
    else
        printf '  \xe2\x9c\x97 cache: legacy access count=%s (expected 1)\n' "${ACCESS_NUM:-unknown}"
        FAIL=$((FAIL + 1))
    fi
fi

check "decorator logs show CACHE_HIT" \
    "ctr_logs cndp-decorator 2>&1" \
    "CACHE_HIT"

check "decorator logs show CACHE_MISS" \
    "ctr_logs cndp-decorator 2>&1" \
    "CACHE_MISS"

# ===================================================================
# 4. Decorating collaborator — event emission
# ===================================================================
printf '\n--- 4. Event emission ---\n'

check "decorator published order.placed event" \
    "curl $CURL_OPTS -sf $DECORATOR/events" \
    "order.placed"

check "event contains order id" \
    "curl $CURL_OPTS -sf $DECORATOR/events" \
    "order_id"

check "decorator logs show Kafka event" \
    "ctr_logs cndp-decorator 2>&1" \
    "EVENT order.placed"

# Verify event landed on Kafka topic
KAFKA_MSG=$(ctr_exec cndp-kafka /opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic order.placed \
    --from-beginning \
    --timeout-ms 5000 2>/dev/null | head -1) || KAFKA_MSG=""

check "event on Kafka order.placed topic" \
    "echo '$KAFKA_MSG'" \
    "order.placed"

# ===================================================================
# 5. Legacy untouched — same API, new behavior
# ===================================================================
printf '\n--- 5. Legacy untouched ---\n'

check "legacy service still identifies as legacy" \
    "ctr_exec cndp-legacy curl $CURL_OPTS -sf http://localhost:8080/healthz" \
    '"source":"legacy"'

LEGACY_MENTIONS=$(ctr_logs cndp-legacy 2>&1 | grep -c 'CACHE\|EVENT' || true)
if [ "$LEGACY_MENTIONS" = "0" ]; then
    printf '  \xe2\x9c\x93 legacy has no knowledge of cache or events\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 legacy has no knowledge of cache or events (found %s mentions)\n' "$LEGACY_MENTIONS"
    FAIL=$((FAIL + 1))
fi

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
