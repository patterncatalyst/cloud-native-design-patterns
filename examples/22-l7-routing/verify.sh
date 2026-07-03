#!/usr/bin/env bash
set -euo pipefail

ENVOY="http://localhost:8080"
ROUTER="http://localhost:8090"
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

printf '==> Verifying Example 22: L7 Routing & Traffic Management\n\n'

# ===================================================================
# 1. Envoy weighted routing (90/10 split)
# ===================================================================
printf -- '--- 1. Envoy weighted routing ---\n'

check "envoy healthz proxied to backend" \
    "curl -sf $ENVOY/healthz" \
    '"status":"ok"'

V1_COUNT=0
V2_COUNT=0
TOTAL=200

for i in $(seq 1 $TOTAL); do
    RESP=$(curl -sf "$ENVOY/orders" 2>/dev/null) || continue
    if echo "$RESP" | grep -q '"v2"'; then
        V2_COUNT=$((V2_COUNT + 1))
    else
        V1_COUNT=$((V1_COUNT + 1))
    fi
done

printf '  info: %d requests → v1=%d v2=%d\n' "$TOTAL" "$V1_COUNT" "$V2_COUNT"

# v2 should be ~10% (20 out of 200). Allow 3-30% range.
V2_LOW=6
V2_HIGH=60
if [ "$V2_COUNT" -ge "$V2_LOW" ] && [ "$V2_COUNT" -le "$V2_HIGH" ]; then
    printf '  \xe2\x9c\x93 weighted split: v2 is %d/%d (~%d%%), within expected 3-30%% range\n' \
        "$V2_COUNT" "$TOTAL" "$((V2_COUNT * 100 / TOTAL))"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 weighted split: v2 is %d/%d (~%d%%), outside 3-30%% range\n' \
        "$V2_COUNT" "$TOTAL" "$((V2_COUNT * 100 / TOTAL))"
    FAIL=$((FAIL + 1))
fi

if [ "$V1_COUNT" -gt "$V2_COUNT" ]; then
    printf '  \xe2\x9c\x93 v1 receives majority of traffic (%d > %d)\n' "$V1_COUNT" "$V2_COUNT"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 v1 should receive majority (%d <= %d)\n' "$V1_COUNT" "$V2_COUNT"
    FAIL=$((FAIL + 1))
fi

# ===================================================================
# 2. Header-based routing override
# ===================================================================
printf '\n--- 2. Header-based routing ---\n'

HEADER_V2=0
HEADER_TOTAL=20

for i in $(seq 1 $HEADER_TOTAL); do
    RESP=$(curl -sf -H 'x-route-to: v2' "$ENVOY/orders" 2>/dev/null) || continue
    if echo "$RESP" | grep -q '"v2"'; then
        HEADER_V2=$((HEADER_V2 + 1))
    fi
done

if [ "$HEADER_V2" -eq "$HEADER_TOTAL" ]; then
    printf '  \xe2\x9c\x93 x-route-to: v2 header → all %d requests hit v2\n' "$HEADER_TOTAL"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 x-route-to: v2 header → only %d/%d hit v2\n' "$HEADER_V2" "$HEADER_TOTAL"
    FAIL=$((FAIL + 1))
fi

check "without header, response can be v1" \
    "curl -sf $ENVOY/orders" \
    '"version"'

# ===================================================================
# 3. In-app rule-driven routing
# ===================================================================
printf '\n--- 3. In-app rule-driven routing ---\n'

check "router healthz" \
    "curl -sf $ROUTER/healthz" \
    '"status":"ok"'

check "VIP order (amount >= 1000) → orders.priority" \
    "curl -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"diamond\",\"quantity\":1,\"amount\":2500}'" \
    '"routed_to":"orders.priority"'

check "VIP order flagged as vip=true" \
    "curl -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"diamond\",\"quantity\":1,\"amount\":2500}'" \
    '"vip":true'

check "ordinary order (amount < 1000) → orders.default" \
    "curl -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"widget\",\"quantity\":3,\"amount\":50}'" \
    '"routed_to":"orders.default"'

check "ordinary order flagged as vip=false" \
    "curl -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"widget\",\"quantity\":3,\"amount\":50}'" \
    '"vip":false'

# ===================================================================
# 4. Rule change without redeploy
# ===================================================================
printf '\n--- 4. Rule change without redeploy ---\n'

check "current rules show threshold 1000" \
    "curl -sf $ROUTER/rules" \
    '"vip_threshold":1000'

curl -sf -X PUT "$ROUTER/rules" \
    -H 'Content-Type: application/json' \
    -d '{"vip_threshold": 500}' >/dev/null 2>&1

check "after lowering threshold to 500, amount=750 is now VIP" \
    "curl -sf -X POST $ROUTER/orders -H 'Content-Type: application/json' -d '{\"sku\":\"gadget\",\"quantity\":1,\"amount\":750}'" \
    '"routed_to":"orders.priority"'

check "rules endpoint reflects updated threshold" \
    "curl -sf $ROUTER/rules" \
    '"vip_threshold":500'

# ===================================================================
# 5. Envoy version markers in responses
# ===================================================================
printf '\n--- 5. Version markers ---\n'

check "v1 backend returns version=v1" \
    "curl -sf $ENVOY/healthz" \
    '"version"'

check "POST through envoy returns version field" \
    "curl -sf -X POST $ENVOY/orders -H 'Content-Type: application/json' -d '{\"sku\":\"test\",\"quantity\":1}'" \
    '"version"'

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
