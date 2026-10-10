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

printf '==> Verifying Example 18: API Error Handling\n\n'

# --- Service is up ---
# order-service has no compose healthcheck, so `up --wait` can return before it
# listens; give it up to 60s.
for _ in $(seq 1 30); do
    curl $CURL_OPTS -sf "$BASE/healthz" >/dev/null 2>&1 && break
    sleep 2
done
check "order-service healthz" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status":"ok"'

# warmup: give gRPC channel time to connect to inventory
for _ in 1 2 3 4 5; do
    CODE=$(curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d '{"sku":"warmup","quantity":1}' "$BASE/orders" 2>/dev/null) || CODE=""
    [ "$CODE" = "201" ] && break
    sleep 2
done

# --- Happy path ---
check_status "POST /orders returns 201 (happy path)" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget\",\"quantity\":1}' $BASE/orders" \
    "201"

# --- Validation error (problem+json) ---
printf '  \xe2\x86\x92 testing validation error...\n'
VALIDATION=$(curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"","quantity":0}' "$BASE/orders" 2>/dev/null || \
    curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"","quantity":0}' "$BASE/orders")

check_status "validation error returns 422" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"\",\"quantity\":0}' $BASE/orders" \
    "422"

check "validation error has code VALIDATION_ERROR" \
    "echo '$VALIDATION'" \
    '"VALIDATION_ERROR"'

check "validation error has traceId" \
    "echo '$VALIDATION'" \
    '"traceId"'

# --- Stock conflict (exhaust stock → 409) ---
printf '  \xe2\x86\x92 exhausting stock to trigger STOCK_UNAVAILABLE...\n'
for _ in $(seq 1 5); do
    curl $CURL_OPTS -sf -X POST -H 'Content-Type: application/json' \
        -d '{"sku":"limited","quantity":1}' "$BASE/orders" >/dev/null 2>&1
done

STOCK_ERR=$(curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"limited","quantity":1}' "$BASE/orders")

check_status "stock conflict returns 409" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"limited\",\"quantity\":1}' $BASE/orders" \
    "409"

check "stock error has code STOCK_UNAVAILABLE" \
    "echo '$STOCK_ERR'" \
    '"STOCK_UNAVAILABLE"'

check "stock error has retryable=false" \
    "echo '$STOCK_ERR'" \
    '"retryable":false'

check "stock error has traceId" \
    "echo '$STOCK_ERR'" \
    '"traceId"'

# --- Upstream unavailable (stop inventory → 503 with Retry-After) ---
printf '  \xe2\x86\x92 stopping inventory to trigger INVENTORY_UNAVAILABLE...\n'
ctr_stop cndp-inventory >/dev/null 2>&1
sleep 3

UNAVAIL=$(curl $CURL_OPTS -s -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"widget","quantity":1}' "$BASE/orders")

check_status "upstream unavailable returns 503" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget\",\"quantity\":1}' $BASE/orders" \
    "503"

check "unavailable error has retryable=true" \
    "echo '$UNAVAIL'" \
    '"retryable":true'

check "unavailable error has retryAfter" \
    "echo '$UNAVAIL'" \
    '"retryAfter"'

# Check Retry-After header
HEADER_FILE=$(mktemp)
curl $CURL_OPTS -s -D "$HEADER_FILE" -o /dev/null -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"widget","quantity":1}' "$BASE/orders" 2>/dev/null
RETRY_HEADER=$(grep -i "retry-after" "$HEADER_FILE" 2>/dev/null || echo "")
rm -f "$HEADER_FILE"
if echo "$RETRY_HEADER" | grep -qi "retry-after"; then
    printf '  \xe2\x9c\x93 Retry-After HTTP header present\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 Retry-After HTTP header missing\n'
    FAIL=$((FAIL + 1))
fi

# --- Restart inventory ---
ctr_start cndp-inventory >/dev/null 2>&1

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
