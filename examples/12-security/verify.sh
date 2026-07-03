#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:8080"
PASS=0
FAIL=0
SKIP=0

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

printf '==> Verifying Example 12: Security\n\n'

# ===================================================================
# 1. Sidecar trust — deny without identity header
# ===================================================================
printf -- '--- 1. Sidecar trust middleware ---\n'

check "healthz bypasses identity check" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

check "request without X-Forwarded-Client-Cert → 403" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1,\"tenant\":\"t\"}'" \
    "403"

check "403 body says no validated identity" \
    "curl -s -X POST $BASE/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1,\"tenant\":\"t\"}'" \
    "no validated identity"

check "request with identity header → 201" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/orders -H 'Content-Type: application/json' -H 'X-Forwarded-Client-Cert: spiffe://cluster.local/ns/orders/sa/order-service' -d '{\"sku\":\"widget-a\",\"quantity\":2,\"tenant\":\"acme\"}'" \
    "201"

ORDER_JSON=$(curl -sf -X POST "$BASE/orders" \
    -H 'Content-Type: application/json' \
    -H 'X-Forwarded-Client-Cert: spiffe://cluster.local/ns/orders/sa/order-service' \
    -H 'X-Jwt-Claim-Sub: user-42' \
    -d '{"sku":"gadget-b","quantity":1,"tenant":"acme"}' 2>/dev/null) || ORDER_JSON=""

check "response includes sidecar identity" \
    "echo '$ORDER_JSON'" \
    "spiffe://cluster.local"

check "response includes JWT subject claim" \
    "echo '$ORDER_JSON'" \
    "user-42"

# ===================================================================
# 2. Valet key — mint and verify scoped tokens
# ===================================================================
printf '\n--- 2. Valet key ---\n'

VALET_JSON=$(curl -sf -X POST "$BASE/valet-key?resource=exports/report.csv&operation=GET" \
    -H 'X-Forwarded-Client-Cert: spiffe://test' 2>/dev/null) || VALET_JSON=""

check "valet key minted for resource" \
    "echo '$VALET_JSON'" \
    "exports/report.csv"

VALET_TOKEN=$(echo "$VALET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null) || VALET_TOKEN=""
VALET_EXPIRES=$(echo "$VALET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['expires'])" 2>/dev/null) || VALET_EXPIRES=""

if [ -n "$VALET_TOKEN" ] && [ -n "$VALET_EXPIRES" ]; then
    check "valid valet key verifies successfully" \
        "curl -sf '$BASE/verify-valet?resource=exports/report.csv&operation=GET&expires=$VALET_EXPIRES&token=$VALET_TOKEN' -H 'X-Forwarded-Client-Cert: spiffe://test'" \
        '"valid":true'
else
    printf '  \xe2\x9c\x97 valid valet key verifies successfully (no token minted)\n'
    FAIL=$((FAIL + 1))
fi

check "tampered valet key → 403" \
    "curl -s -o /dev/null -w '%{http_code}' '$BASE/verify-valet?resource=exports/report.csv&operation=GET&expires=9999999999&token=tampered' -H 'X-Forwarded-Client-Cert: spiffe://test'" \
    "403"

check "wrong operation → 403" \
    "curl -s -o /dev/null -w '%{http_code}' '$BASE/verify-valet?resource=exports/report.csv&operation=DELETE&expires=$VALET_EXPIRES&token=$VALET_TOKEN' -H 'X-Forwarded-Client-Cert: spiffe://test'" \
    "403"

# ===================================================================
# 3. Per-tenant bulkhead
# ===================================================================
printf '\n--- 3. Per-tenant bulkhead ---\n'

curl -sf -X POST "$BASE/orders" \
    -H 'Content-Type: application/json' \
    -H 'X-Forwarded-Client-Cert: spiffe://test' \
    -d '{"sku":"x","quantity":1,"tenant":"beta"}' >/dev/null 2>&1

check "bulkhead state shows tenant pools" \
    "curl -sf $BASE/bulkhead-state -H 'X-Forwarded-Client-Cert: spiffe://test'" \
    '"capacity":5'

check "tenant acme has independent pool" \
    "curl -sf $BASE/bulkhead-state -H 'X-Forwarded-Client-Cert: spiffe://test'" \
    '"acme"'

check "tenant beta has independent pool" \
    "curl -sf $BASE/bulkhead-state -H 'X-Forwarded-Client-Cert: spiffe://test'" \
    '"beta"'

# ===================================================================
# 4. Policy-as-code (conftest)
# ===================================================================
printf '\n--- 4. Policy-as-code ---\n'

if command -v conftest &>/dev/null; then
    GOOD_RESULT=$(conftest test policy/good-deploy.yaml -p policy/signed_images.rego --no-color 2>&1) || true
    if echo "$GOOD_RESULT" | grep -q "0 failure"; then
        printf '  \xe2\x9c\x93 conftest: good manifest passes policy\n'
        PASS=$((PASS + 1))
    else
        printf '  \xe2\x9c\x97 conftest: good manifest passes policy (%s)\n' "$GOOD_RESULT"
        FAIL=$((FAIL + 1))
    fi

    BAD_RESULT=$(conftest test policy/bad-deploy.yaml -p policy/signed_images.rego --no-color 2>&1) || true
    if echo "$BAD_RESULT" | grep -q "FAIL\|failure"; then
        printf '  \xe2\x9c\x93 conftest: bad manifest rejected by policy\n'
        PASS=$((PASS + 1))
    else
        printf '  \xe2\x9c\x97 conftest: bad manifest rejected by policy (%s)\n' "$BAD_RESULT"
        FAIL=$((FAIL + 1))
    fi

    if echo "$BAD_RESULT" | grep -q "untrusted image"; then
        printf '  \xe2\x9c\x93 conftest: violation mentions untrusted image\n'
        PASS=$((PASS + 1))
    else
        printf '  \xe2\x9c\x97 conftest: violation mentions untrusted image\n'
        FAIL=$((FAIL + 1))
    fi
else
    printf '  - SKIP conftest not installed (install: https://www.conftest.dev/install/)\n'
    SKIP=$((SKIP + 3))
fi

printf '\n==> Results: %d passed, %d failed' "$PASS" "$FAIL"
if [ "$SKIP" -gt 0 ]; then printf ', %d skipped' "$SKIP"; fi
printf '\n'
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
