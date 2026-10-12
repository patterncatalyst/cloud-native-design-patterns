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

check_absent() {
    local desc="$1" cmd="$2" absent="$3"
    result=$(eval "$cmd" 2>/dev/null) || result=""
    if echo "$result" | grep -q "$absent"; then
        printf '  \xe2\x9c\x97 %s (found "%s" but should not)\n' "$desc" "$absent"
        FAIL=$((FAIL + 1))
    else
        printf '  \xe2\x9c\x93 %s\n' "$desc"
        PASS=$((PASS + 1))
    fi
}

printf '==> Verifying Example 03: Composition\n\n'

# --- Gateway healthcheck ---
check "gateway healthz returns ok" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status": *"\(ok\|UP\)"'

# --- REST backend reachable ---
check "order-api returns seeded orders" \
    "curl $CURL_OPTS -sf http://localhost:8081/orders" \
    '"widget-a"'

# --- GraphQL without stock field (no inventory call) ---
check "GraphQL query orders without stock field" \
    "curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ orders { id sku status } }\"}' $BASE/graphql" \
    '"sku"'

check_absent "GraphQL without stock does not include stock field" \
    "curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ orders { id sku status } }\"}' $BASE/graphql" \
    '"stock"'

# --- GraphQL with stock field (triggers inventory gRPC) ---
check "GraphQL query orders with stock field returns data" \
    "curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ orders { id sku stock } }\"}' $BASE/graphql" \
    '"stock"'

check "stock for widget-a is 42" \
    "curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ orders { sku stock } }\"}' $BASE/graphql" \
    '42'

# --- DataLoader batching ---
# The gateway logs "DataLoader batched N skus in one gRPC call" when batching works.
# With 5 seeded orders across 4 unique skus, a single batch call should appear.
check "DataLoader batches stock lookups into one gRPC call" \
    "ctr_logs cndp-gateway 2>&1" \
    "DataLoader batched"

# --- Single order by ID ---
check "GraphQL single order by id" \
    "curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ order(id: \\\"ord-001\\\") { id sku quantity } }\"}' $BASE/graphql" \
    '"ord-001"'

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
