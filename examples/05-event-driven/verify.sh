#!/usr/bin/env bash
# shellcheck disable=SC2086  # $CURL_OPTS is intentionally word-split
set -euo pipefail

RUNTIME="${RUNTIME:-docker}"
BASE="${BASE:-http://localhost:8080}"
CURL_OPTS="${CURL_OPTS:-}"

# Container operations go through these helpers so the checks do not hard-code
# an engine. RUNTIME=docker (default) calls the docker CLI on compose containers.
# RUNTIME=kubernetes calls `$KUBECTL exec` against the pods that stand in for
# those containers: ctr_target maps a container name (cndp-kafka, cndp-postgres)
# to its pod. Set KUBECTL=oc for OpenShift.
KUBECTL="${KUBECTL:-kubectl}"
KUBE_CONTEXT="${KUBE_CONTEXT:-cndp-k8s}"
KUBE_NAMESPACE="${KUBE_NAMESPACE:-cndp-05}"
KAFKA_TARGET="${KAFKA_TARGET:-pod/cndp-dual-role-0 -c kafka}"
POSTGRES_TARGET="${POSTGRES_TARGET:-pod/cndp-postgres-0}"

unsupported() { echo "$1 is not supported on RUNTIME=$RUNTIME" >&2; return 1; }

case "$RUNTIME" in
    docker)
        ctr_exec()    { docker exec "$@"; }
        ctr_logs()    { docker logs "$@"; }
        ctr_stop()    { docker stop "$@"; }
        ctr_start()   { docker start "$@"; }
        ctr_rm()      { docker rm "$@"; }
        ctr_kill()    { docker kill --signal "${2:-KILL}" "$1"; }  # ctr_kill <container> [signal]
        ctr_pause()   { docker pause "$@"; }
        ctr_unpause() { docker unpause "$@"; }
        ctr_compose() { docker compose "$@"; }
        ;;
    kubernetes)
        ctr_target() {
            case "$1" in
                cndp-kafka)    echo "$KAFKA_TARGET" ;;
                cndp-postgres) echo "$POSTGRES_TARGET" ;;
                *) echo "no pod mapped to container $1 on RUNTIME=kubernetes" >&2; return 1 ;;
            esac
        }
        ctr_exec() {  # ctr_exec <container> <command...>
            local target
            local -a args
            target="$(ctr_target "$1")" || return 1
            shift
            read -r -a args <<<"$target"
            "$KUBECTL" --context "$KUBE_CONTEXT" -n "$KUBE_NAMESPACE" exec "${args[@]}" -- "$@"
        }
        ctr_logs()    { unsupported ctr_logs; }
        ctr_stop()    { unsupported ctr_stop; }
        ctr_start()   { unsupported ctr_start; }
        ctr_rm()      { unsupported ctr_rm; }
        ctr_kill()    { unsupported ctr_kill; }
        ctr_pause()   { unsupported ctr_pause; }
        ctr_unpause() { unsupported ctr_unpause; }
        ctr_compose() { unsupported ctr_compose; }
        ;;
    *) echo "RUNTIME=$RUNTIME not supported (docker, kubernetes)" >&2; exit 1 ;;
esac

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
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status":"ok"'

# --- Place an order ---
ORDER_JSON=$(curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"widget-a","quantity":5}' "$BASE/orders")
ORDER_ID=$(echo "$ORDER_JSON" | jq -r '.id')

check_status "POST /orders returns 201" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget-b\",\"quantity\":2}' $BASE/orders" \
    "201"

check "order visible in GET /orders" \
    "curl $CURL_OPTS -sf $BASE/orders" \
    '"widget-a"'

# --- Kafka topic exists ---
printf '  \xe2\x86\x92 waiting for consumers to process events...\n'
sleep 8

check "order.placed topic exists in Kafka" \
    "ctr_exec cndp-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "order.placed"

# --- Fan-out: shipping consumer processed ---
check "shipment created for order" \
    "ctr_exec cndp-postgres psql -U appuser -d appdb -tAc \"SELECT count(*) FROM shipments WHERE order_id='$ORDER_ID'\"" \
    "1"

# --- Fan-out: notification consumer processed ---
check "notification created for order" \
    "ctr_exec cndp-postgres psql -U appuser -d appdb -tAc \"SELECT count(*) FROM notifications WHERE order_id='$ORDER_ID'\"" \
    "1"

# --- Two independent consumer groups ---
check "shipping-group consumer group exists" \
    "ctr_exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "shipping-group"

check "notification-group consumer group exists" \
    "ctr_exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list 2>/dev/null" \
    "notification-group"

# --- Idempotent consumers: re-deliver same event and verify no duplicates ---
printf '  \xe2\x86\x92 testing idempotent consumers (re-sending duplicate event)...\n'
DUPLICATE_EVENT="{\"id\":\"$ORDER_ID\",\"sku\":\"widget-a\",\"quantity\":5,\"status\":\"pending\"}"
ctr_exec cndp-kafka bash -c "echo '$DUPLICATE_EVENT' | /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic order.placed" >/dev/null 2>&1
sleep 8

check "shipping remains idempotent (still 1 row after duplicate)" \
    "ctr_exec cndp-postgres psql -U appuser -d appdb -tAc \"SELECT count(*) FROM shipments WHERE order_id='$ORDER_ID'\"" \
    "1"

check "notification remains idempotent (still 1 row after duplicate)" \
    "ctr_exec cndp-postgres psql -U appuser -d appdb -tAc \"SELECT count(*) FROM notifications WHERE order_id='$ORDER_ID'\"" \
    "1"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [[ $FAIL -eq 0 ]]; then
    printf '==> PASS\n'
else
    printf '==> FAIL\n'
    exit 1
fi
