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

printf '==> Verifying Example 06: Stream Processing\n\n'

# --- order-service is up ---
check "order-service healthz" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# --- Place orders for two merchants ---
for i in 1 2 3; do
    curl -sf -X POST -H 'Content-Type: application/json' \
        -d "{\"merchant_id\":\"merchant-a\",\"sku\":\"widget\",\"quantity\":$i,\"total\":$((i * 10)).00}" \
        "$BASE/orders" >/dev/null
done
for i in 1 2; do
    curl -sf -X POST -H 'Content-Type: application/json' \
        -d "{\"merchant_id\":\"merchant-b\",\"sku\":\"gadget\",\"quantity\":$i,\"total\":$((i * 25)).00}" \
        "$BASE/orders" >/dev/null
done

check_status "POST /orders returns 201" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"merchant_id\":\"merchant-a\",\"sku\":\"widget\",\"quantity\":1,\"total\":10.00}' $BASE/orders" \
    "201"

check "orders visible in GET /orders" \
    "curl -sf $BASE/orders" \
    '"merchant-a"'

# --- Wait for stream processor to emit windowed results ---
printf '  \xe2\x86\x92 waiting for stream processor to emit windowed aggregations...\n'
sleep 20

# --- Check Kafka topics ---
check "order.placed topic exists" \
    "podman exec cndp-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "order.placed"

check "revenue.by-merchant topic exists (derived stream)" \
    "podman exec cndp-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "revenue.by-merchant"

# --- Read the derived stream ---
REVENUE=$(podman exec cndp-kafka /opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 --topic revenue.by-merchant \
    --from-beginning --timeout-ms 10000 2>/dev/null || true)

check "revenue stream contains merchant-a aggregation" \
    "echo '$REVENUE'" \
    "merchant-a"

check "revenue stream contains merchant-b aggregation" \
    "echo '$REVENUE'" \
    "merchant-b"

# --- Consumer lag monitoring ---
check "stream-processor consumer group exists" \
    "podman exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "stream-processor"

# --- Pause consumer, produce burst, observe lag ---
printf '  \xe2\x86\x92 pausing stream-processor to build consumer lag...\n'
podman pause cndp-stream-processor >/dev/null 2>&1

for i in $(seq 1 10); do
    curl -sf -X POST -H 'Content-Type: application/json' \
        -d "{\"merchant_id\":\"merchant-c\",\"sku\":\"burst-item\",\"quantity\":1,\"total\":5.00}" \
        "$BASE/orders" >/dev/null
done
sleep 3

LAG=$(podman exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 --describe --group stream-processor 2>/dev/null \
    | awk 'NR>1 {sum+=$6} END {print sum}')
if [ "${LAG:-0}" -gt 0 ]; then
    printf '  \xe2\x9c\x93 consumer lag is %s (lag builds when processor paused)\n' "$LAG"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 consumer lag should be > 0 when processor paused (got %s)\n' "${LAG:-0}"
    FAIL=$((FAIL + 1))
fi

# --- Resume and watch lag drain ---
printf '  \xe2\x86\x92 resuming stream-processor to drain lag...\n'
podman unpause cndp-stream-processor >/dev/null 2>&1
sleep 10

LAG_AFTER=$(podman exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 --describe --group stream-processor 2>/dev/null \
    | awk 'NR>1 {sum+=$6} END {print sum}')
if [ "${LAG_AFTER:-0}" -lt "${LAG:-1}" ]; then
    printf '  \xe2\x9c\x93 consumer lag drained after resume (was %s, now %s)\n' "$LAG" "$LAG_AFTER"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 consumer lag did not drain (was %s, now %s)\n' "$LAG" "$LAG_AFTER"
    FAIL=$((FAIL + 1))
fi

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
