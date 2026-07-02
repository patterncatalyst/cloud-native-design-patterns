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

printf '==> Verifying Example 18: API Error Handling\n\n'

# --- Service is up ---
check "order-service healthz" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# --- Happy path ---
check_status "POST /orders returns 201 (happy path)" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget\",\"quantity\":1}' $BASE/orders" \
    "201"

# --- Validation error (problem+json) ---
printf '  \xe2\x86\x92 testing validation error...\n'
VALIDATION=$(curl -sf -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"","quantity":0}' "$BASE/orders" 2>/dev/null || \
    curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"","quantity":0}' "$BASE/orders")

check_status "validation error returns 422" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"\",\"quantity\":0}' $BASE/orders" \
    "422"

check "validation error has code VALIDATION_ERROR" \
    "echo '$VALIDATION'" \
    '"VALIDATION_ERROR"'

check "validation error has traceId" \
    "echo '$VALIDATION'" \
    '"traceId"'

# --- Stock conflict (exhaust stock → 409) ---
printf '  \xe2\x86\x92 exhausting stock to trigger STOCK_UNAVAILABLE...\n'
for i in $(seq 1 5); do
    curl -sf -X POST -H 'Content-Type: application/json' \
        -d '{"sku":"limited","quantity":1}' "$BASE/orders" >/dev/null 2>&1
done

STOCK_ERR=$(curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"limited","quantity":1}' "$BASE/orders")

check_status "stock conflict returns 409" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"limited\",\"quantity\":1}' $BASE/orders" \
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
podman stop cndp-inventory >/dev/null 2>&1
sleep 3

UNAVAIL=$(curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"widget","quantity":1}' "$BASE/orders")

check_status "upstream unavailable returns 503" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget\",\"quantity\":1}' $BASE/orders" \
    "503"

check "unavailable error has retryable=true" \
    "echo '$UNAVAIL'" \
    '"retryable":true'

check "unavailable error has retryAfter" \
    "echo '$UNAVAIL'" \
    '"retryAfter"'

# Check Retry-After header
HEADER_FILE=$(mktemp)
curl -s -D "$HEADER_FILE" -o /dev/null -X POST -H 'Content-Type: application/json' \
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
podman start cndp-inventory >/dev/null 2>&1

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
