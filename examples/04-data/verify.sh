#!/usr/bin/env bash
# shellcheck disable=SC2086  # $CURL_OPTS is intentionally word-split
set -euo pipefail

RUNTIME="${RUNTIME:-docker}"
BASE="${BASE:-http://localhost:8080}"
CONNECT="${CONNECT:-http://localhost:8083}"
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

printf '==> Verifying Example 04: Data (Transactional Outbox + CDC)\n\n'

# --- Order service is up ---
check "order-service healthz" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status":"ok"'

# --- Register Debezium connector ---
printf '  \xe2\x86\x92 waiting for Kafka Connect to be ready...\n'
for _ in $(seq 1 30); do
    if curl $CURL_OPTS -sf "$CONNECT/" >/dev/null 2>&1; then break; fi
    sleep 2
done

check "Kafka Connect is reachable" \
    "curl $CURL_OPTS -sf $CONNECT/" \
    "version"

printf '  \xe2\x86\x92 registering Debezium outbox connector...\n'
./debezium/register-connector.sh "$CONNECT" >/dev/null 2>&1 || true
sleep 5

check "outbox-connector is running" \
    "curl $CURL_OPTS -sf $CONNECT/connectors/outbox-connector/status" \
    '"RUNNING"'

# --- Place an order (outbox pattern) ---
check_status "POST /orders returns 201" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget-a\",\"quantity\":3}' $BASE/orders" \
    "201"

check "order exists in orders table" \
    "curl $CURL_OPTS -sf $BASE/orders" \
    '"widget-a"'

check "outbox row exists for the order" \
    "curl $CURL_OPTS -sf $BASE/outbox" \
    '"order.placed"'

# --- Debezium publishes outbox to Kafka ---
printf '  \xe2\x86\x92 waiting for Debezium to publish outbox event...\n'
sleep 10

check "Kafka has order.placed topic from Debezium" \
    "ctr_exec cndp-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "order.placed"

# --- Verify the event content in Kafka ---
check "Kafka order.placed topic has the event payload" \
    "ctr_exec cndp-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic order.placed --from-beginning --max-messages 1 --timeout-ms 10000 2>/dev/null" \
    "widget-a"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
