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

printf '==> Verifying Example 02: Communications\n\n'

# --- REST: correct status codes ---
check_status "POST /orders returns 201 Created" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget-a\",\"quantity\":5}' $BASE/orders" \
    "201"

check "POST /orders returns order with id and status" \
    "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget-b\",\"quantity\":3}' $BASE/orders" \
    '"status"'

# --- REST: input validation returns 400/422 ---
check_status "POST /orders with empty sku returns 422" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"\",\"quantity\":1}' $BASE/orders" \
    "422"

check_status "POST /orders with quantity=0 returns 422" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"x\",\"quantity\":0}' $BASE/orders" \
    "422"

# --- REST: cursor pagination ---
check "GET /orders returns items array" \
    "curl -sf $BASE/orders" \
    '"items"'

check "GET /orders?limit=1 returns one item with next_cursor" \
    "curl -sf '$BASE/orders?limit=1'" \
    '"next_cursor"'

# --- gRPC: inventory reserve reflected in order status ---
check "order with available stock is confirmed" \
    "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"grpc-test\",\"quantity\":1}' $BASE/orders" \
    '"confirmed"'

check "order exceeding stock is rejected" \
    "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"scarce\",\"quantity\":200}' $BASE/orders" \
    '"rejected"'

# --- GraphQL ---
check "GraphQL query returns orders" \
    "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"query\":\"{ orders(limit: 5) { id sku status } }\"}' $BASE/graphql" \
    '"data"'

# --- Async: Kafka event published ---
printf '\n  \xe2\x86\x92 checking Kafka for order.placed events...\n'
sleep 3

check "Kafka has order.placed topic" \
    "podman exec cndp-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "order.placed"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
