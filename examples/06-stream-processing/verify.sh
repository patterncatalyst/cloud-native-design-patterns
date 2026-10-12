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

printf '==> Verifying Example 06: Stream Processing\n\n'

# --- order-service is up ---
check "order-service healthz" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status": *"\(ok\|UP\)"'

# --- Place orders for two merchants ---
for i in 1 2 3; do
    curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' \
        -d "{\"merchant_id\":\"merchant-a\",\"sku\":\"widget\",\"quantity\":$i,\"total\":$((i * 10)).00}" \
        "$BASE/orders" >/dev/null
done
for i in 1 2; do
    curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' \
        -d "{\"merchant_id\":\"merchant-b\",\"sku\":\"gadget\",\"quantity\":$i,\"total\":$((i * 25)).00}" \
        "$BASE/orders" >/dev/null
done

check_status "POST /orders returns 201" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"merchant_id\":\"merchant-a\",\"sku\":\"widget\",\"quantity\":1,\"total\":10.00}' $BASE/orders" \
    "201"

check "orders visible in GET /orders" \
    "curl $CURL_OPTS -sf $BASE/orders" \
    '"merchant-a"'

# --- Wait for stream processor to emit windowed results ---
printf '  \xe2\x86\x92 waiting for stream processor to emit windowed aggregations...\n'
sleep 20

# --- Check Kafka topics ---
check "order.placed topic exists" \
    "ctr_exec cndp-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "order.placed"

check "revenue.by-merchant topic exists (derived stream)" \
    "ctr_exec cndp-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "revenue.by-merchant"

# --- Read the derived stream ---
REVENUE=$(ctr_exec cndp-kafka /opt/kafka/bin/kafka-console-consumer.sh \
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
    "ctr_exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "stream-processor"

# --- Pause consumer, produce burst, observe lag ---
printf '  \xe2\x86\x92 pausing stream-processor to build consumer lag...\n'
ctr_pause cndp-stream-processor >/dev/null 2>&1

for i in $(seq 1 10); do
    curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' \
        -d "{\"merchant_id\":\"merchant-c\",\"sku\":\"burst-item\",\"quantity\":1,\"total\":5.00}" \
        "$BASE/orders" >/dev/null
done
sleep 3

# Lag on the input topic only (order.placed): stream frameworks also put their own
# internal topics in the group (Faust reads its changelog without committing).
# Per partition, lag is LOG-END-OFFSET minus CURRENT-OFFSET; a partition the group
# has not committed on yet shows CURRENT-OFFSET "-", so count its whole log rather
# than zero (a sticky partitioner can put the whole burst there).
group_lag() {
    ctr_exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 --describe --group stream-processor 2>/dev/null \
        | awk '$1 == "stream-processor" && $2 == "order.placed" && $5 ~ /^[0-9]+$/ {
                   cur = ($4 ~ /^[0-9]+$/) ? $4 : 0; sum += $5 - cur
               } END {print sum + 0}'
}
show_group() {
    ctr_exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 --describe --group stream-processor 2>/dev/null | sed 's/^/      /'
}

LAG=$(group_lag)
if [ "${LAG:-0}" -gt 0 ]; then
    printf '  \xe2\x9c\x93 consumer lag is %s (lag builds when processor paused)\n' "$LAG"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 consumer lag should be > 0 when processor paused (got %s)\n' "${LAG:-0}"
    show_group
    FAIL=$((FAIL + 1))
fi

# --- Resume and watch lag drain ---
printf '  \xe2\x86\x92 resuming stream-processor to drain lag...\n'
ctr_unpause cndp-stream-processor >/dev/null 2>&1
sleep 10

LAG_AFTER=$(group_lag)
if [ "${LAG_AFTER:-0}" -lt "${LAG:-1}" ]; then
    printf '  \xe2\x9c\x93 consumer lag drained after resume (was %s, now %s)\n' "$LAG" "$LAG_AFTER"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 consumer lag did not drain (was %s, now %s)\n' "$LAG" "$LAG_AFTER"
    show_group
    FAIL=$((FAIL + 1))
fi

# --- The burst reaches the derived stream ---
# The lag checks cover the first sub-topology (order.placed). The revenue stream shows
# the re-keyed aggregation also processed the burst: merchant-c exists only in the burst.
printf '  \xe2\x86\x92 waiting for the burst to appear in revenue.by-merchant...\n'
REVENUE_C=""
for _ in $(seq 1 6); do
    REVENUE_C=$(ctr_exec cndp-kafka /opt/kafka/bin/kafka-console-consumer.sh \
        --bootstrap-server localhost:9092 --topic revenue.by-merchant \
        --from-beginning --timeout-ms 5000 2>/dev/null || true)
    if grep -q "merchant-c" <<<"$REVENUE_C"; then break; fi
done

check "revenue stream contains merchant-c aggregation (burst processed end to end)" \
    "echo '$REVENUE_C'" \
    "merchant-c"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
