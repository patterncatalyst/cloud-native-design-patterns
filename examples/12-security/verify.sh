#!/usr/bin/env bash
# shellcheck disable=SC2086  # $CURL_OPTS is intentionally word-split
set -euo pipefail

RUNTIME="${RUNTIME:-docker}"
BASE="${BASE:-http://localhost:8080}"
CURL_OPTS="${CURL_OPTS:-}"

# Container operations go through these helpers so the checks do not hard-code
# an engine. This example runs on Docker Compose only (RUNTIME=docker); Example 05's
# verify.sh shows the RUNTIME=kubernetes variant used on minikube and OpenShift Local.
case "$RUNTIME" in
    docker) ;;
    *) echo "RUNTIME=$RUNTIME not supported (docker)" >&2; exit 1 ;;
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

# conftest is required (policy-as-code section). Fail up front rather than skip.
CONFTEST_VERSION=0.71.1
if ! command -v conftest &>/dev/null; then
    cat >&2 <<EOM
ERROR: conftest is required for example 12 but is not installed.
Pinned version: ${CONFTEST_VERSION}. Install it into ~/.local/bin (checksum-verified):

  V=${CONFTEST_VERSION}
  B=https://github.com/open-policy-agent/conftest/releases/download/v\$V
  cd "\$(mktemp -d)" && curl -fsSLO "\$B/conftest_\${V}_Linux_x86_64.tar.gz" -O "\$B/checksums.txt" \\
    && grep " conftest_\${V}_Linux_x86_64.tar.gz\$" checksums.txt | sha256sum -c - \\
    && mkdir -p ~/.local/bin && tar -xzf "conftest_\${V}_Linux_x86_64.tar.gz" -C ~/.local/bin conftest

See examples/PREREQUISITES.md.
EOM
    printf '==> FAIL\n'
    exit 1
fi

printf '==> Verifying Example 12: Security\n\n'

# ===================================================================
# 1. Sidecar trust — deny without identity header
# ===================================================================
printf -- '--- 1. Sidecar trust middleware ---\n'

check "healthz bypasses identity check" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status": *"\(ok\|UP\)"'

check "request without X-Forwarded-Client-Cert → 403" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST $BASE/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1,\"tenant\":\"t\"}'" \
    "403"

check "403 body says no validated identity" \
    "curl $CURL_OPTS -s -X POST $BASE/orders -H 'Content-Type: application/json' -d '{\"sku\":\"w\",\"quantity\":1,\"tenant\":\"t\"}'" \
    "no validated identity"

check "request with identity header → 201" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST $BASE/orders -H 'Content-Type: application/json' -H 'X-Forwarded-Client-Cert: spiffe://cluster.local/ns/orders/sa/order-service' -d '{\"sku\":\"widget-a\",\"quantity\":2,\"tenant\":\"acme\"}'" \
    "201"

ORDER_JSON=$(curl $CURL_OPTS -sf -X POST "$BASE/orders" \
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

VALET_JSON=$(curl $CURL_OPTS -sf -X POST "$BASE/valet-key?resource=exports/report.csv&operation=GET" \
    -H 'X-Forwarded-Client-Cert: spiffe://test' 2>/dev/null) || VALET_JSON=""

check "valet key minted for resource" \
    "echo '$VALET_JSON'" \
    "exports/report.csv"

VALET_TOKEN=$(echo "$VALET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null) || VALET_TOKEN=""
VALET_EXPIRES=$(echo "$VALET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['expires'])" 2>/dev/null) || VALET_EXPIRES=""

if [ -n "$VALET_TOKEN" ] && [ -n "$VALET_EXPIRES" ]; then
    check "valid valet key verifies successfully" \
        "curl $CURL_OPTS -sf '$BASE/verify-valet?resource=exports/report.csv&operation=GET&expires=$VALET_EXPIRES&token=$VALET_TOKEN' -H 'X-Forwarded-Client-Cert: spiffe://test'" \
        '"valid":true'
else
    printf '  \xe2\x9c\x97 valid valet key verifies successfully (no token minted)\n'
    FAIL=$((FAIL + 1))
fi

check "tampered valet key → 403" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' '$BASE/verify-valet?resource=exports/report.csv&operation=GET&expires=9999999999&token=tampered' -H 'X-Forwarded-Client-Cert: spiffe://test'" \
    "403"

check "wrong operation → 403" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' '$BASE/verify-valet?resource=exports/report.csv&operation=DELETE&expires=$VALET_EXPIRES&token=$VALET_TOKEN' -H 'X-Forwarded-Client-Cert: spiffe://test'" \
    "403"

# ===================================================================
# 3. Per-tenant bulkhead
# ===================================================================
printf '\n--- 3. Per-tenant bulkhead ---\n'

curl $CURL_OPTS -sf -X POST "$BASE/orders" \
    -H 'Content-Type: application/json' \
    -H 'X-Forwarded-Client-Cert: spiffe://test' \
    -d '{"sku":"x","quantity":1,"tenant":"beta"}' >/dev/null 2>&1

check "bulkhead state shows tenant pools" \
    "curl $CURL_OPTS -sf $BASE/bulkhead-state -H 'X-Forwarded-Client-Cert: spiffe://test'" \
    '"capacity":5'

check "tenant acme has independent pool" \
    "curl $CURL_OPTS -sf $BASE/bulkhead-state -H 'X-Forwarded-Client-Cert: spiffe://test'" \
    '"acme"'

check "tenant beta has independent pool" \
    "curl $CURL_OPTS -sf $BASE/bulkhead-state -H 'X-Forwarded-Client-Cert: spiffe://test'" \
    '"beta"'

# Fill tenant gamma's pool: 8 concurrent orders that each take 2 s (processing_ms simulates slow work), so 5 hold
# the permits and the rest are refused at once; meanwhile tenant delta, with its own pool, is still served.
printf '  \xe2\x86\x92 sending 8 concurrent slow orders for tenant gamma...\n'
CODES=$(mktemp)
for _ in $(seq 1 8); do
    curl $CURL_OPTS -s -o /dev/null -w '%{http_code}\n' --max-time 10 -X POST "$BASE/orders" \
        -H 'Content-Type: application/json' \
        -H 'X-Forwarded-Client-Cert: spiffe://test' \
        -d '{"sku":"x","quantity":1,"tenant":"gamma","processing_ms":2000}' >>"$CODES" &
done
sleep 0.5

check "another tenant is served while gamma's pool is full" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST $BASE/orders -H 'Content-Type: application/json' -H 'X-Forwarded-Client-Cert: spiffe://test' -d '{\"sku\":\"x\",\"quantity\":1,\"tenant\":\"delta\"}'" \
    "201"

wait
REJECTED=$(grep -c '^429$' "$CODES" || true)
rm -f "$CODES"

check "full tenant pool rejects the overflow with 429" \
    "echo $REJECTED" \
    '^[1-9]'

# ===================================================================
# 4. Policy-as-code (conftest)
# ===================================================================
printf '\n--- 4. Policy-as-code ---\n'

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

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
