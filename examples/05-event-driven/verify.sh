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

printf '==> Verifying Example 05: Event-Driven Architecture\n\n'

# --- order-service is up ---
check "order-service healthz" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# --- Place an order ---
ORDER_JSON=$(curl -sf -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"widget-a","quantity":5}' "$BASE/orders")
ORDER_ID=$(echo "$ORDER_JSON" | jq -r '.id')

check_status "POST /orders returns 201" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget-b\",\"quantity\":2}' $BASE/orders" \
    "201"

check "order visible in GET /orders" \
    "curl -sf $BASE/orders" \
    '"widget-a"'

# --- Kafka topic exists ---
printf '  \xe2\x86\x92 waiting for consumers to process events...\n'
sleep 8

check "order.placed topic exists in Kafka" \
    "podman exec cndp-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "order.placed"

# --- Fan-out: shipping consumer processed ---
check "shipment created for order" \
    "podman exec cndp-postgres psql -U appuser -d appdb -tAc \"SELECT count(*) FROM shipments WHERE order_id='$ORDER_ID'\"" \
    "1"

# --- Fan-out: notification consumer processed ---
check "notification created for order" \
    "podman exec cndp-postgres psql -U appuser -d appdb -tAc \"SELECT count(*) FROM notifications WHERE order_id='$ORDER_ID'\"" \
    "1"

# --- Two independent consumer groups ---
check "shipping-group consumer group exists" \
    "podman exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "shipping-group"

check "notification-group consumer group exists" \
    "podman exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "notification-group"

# --- Idempotent consumers: re-deliver and verify no duplicates ---
printf '  \xe2\x86\x92 testing idempotent consumers (restart to trigger redelivery)...\n'
podman restart cndp-shipping cndp-notification >/dev/null 2>&1
sleep 10

check "shipping remains idempotent (still 1 row after restart)" \
    "podman exec cndp-postgres psql -U appuser -d appdb -tAc \"SELECT count(*) FROM shipments WHERE order_id='$ORDER_ID'\"" \
    "1"

check "notification remains idempotent (still 1 row after restart)" \
    "podman exec cndp-postgres psql -U appuser -d appdb -tAc \"SELECT count(*) FROM notifications WHERE order_id='$ORDER_ID'\"" \
    "1"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
