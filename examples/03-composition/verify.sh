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
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# --- REST backend reachable ---
check "order-api returns seeded orders" \
    "curl -sf http://localhost:8081/orders" \
    '"widget-a"'

# --- GraphQL without stock field (no inventory call) ---
check "GraphQL query orders without stock field" \
    "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ orders { id sku status } }\"}' $BASE/graphql" \
    '"sku"'

check_absent "GraphQL without stock does not include stock field" \
    "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ orders { id sku status } }\"}' $BASE/graphql" \
    '"stock"'

# --- GraphQL with stock field (triggers inventory gRPC) ---
check "GraphQL query orders with stock field returns data" \
    "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ orders { id sku stock } }\"}' $BASE/graphql" \
    '"stock"'

check "stock for widget-a is 42" \
    "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ orders { sku stock } }\"}' $BASE/graphql" \
    '42'

# --- DataLoader batching ---
# The gateway logs "DataLoader batched N skus in one gRPC call" when batching works.
# With 5 seeded orders across 4 unique skus, a single batch call should appear.
check "DataLoader batches stock lookups into one gRPC call" \
    "podman logs cndp-gateway 2>&1" \
    "DataLoader batched"

# --- Single order by ID ---
check "GraphQL single order by id" \
    "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ order(id: \\\"ord-001\\\") { id sku quantity } }\"}' $BASE/graphql" \
    '"ord-001"'

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
