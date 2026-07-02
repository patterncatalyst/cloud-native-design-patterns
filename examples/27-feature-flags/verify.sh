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

check_not() {
    local desc="$1" cmd="$2" not_expected="$3"
    result=$(eval "$cmd" 2>/dev/null) || result=""
    if echo "$result" | grep -q "$not_expected"; then
        printf '  \xe2\x9c\x97 %s (should NOT contain "%s")\n' "$desc" "$not_expected"
        FAIL=$((FAIL + 1))
    else
        printf '  \xe2\x9c\x93 %s\n' "$desc"
        PASS=$((PASS + 1))
    fi
}

printf '==> Verifying Example 27: Feature Flags\n\n'

# --- Ensure clean state: restart flag-service so provider reconnects ---
printf '  \xe2\x86\x92 ensuring clean provider state...\n'
podman restart cndp-flag-service >/dev/null 2>&1
for i in $(seq 1 20); do
    sleep 2
    if curl -sf "$BASE/healthz" >/dev/null 2>&1; then break; fi
done
sleep 3

# --- Service healthy ---
check "healthz returns ok" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# ===================================================================
# 1. Release flag — new-checkout
# ===================================================================
printf '\n--- 1. Release flag (new-checkout) ---\n'

check "free-plan user gets legacy checkout (default off)" \
    "curl -sf -H 'X-User: user-1' -H 'X-Plan: free' -X POST $BASE/checkout" \
    '"path":"legacy"'

check "enterprise-plan user always gets new checkout" \
    "curl -sf -H 'X-User: user-1' -H 'X-Plan: enterprise' -X POST $BASE/checkout" \
    '"path":"new"'

# --- Sticky assignment: same user always gets same result ---
FIRST=$(curl -sf -H 'X-User: stable-user-42' -H 'X-Plan: free' -X POST "$BASE/checkout" | grep -o '"path":"[^"]*"')
SECOND=$(curl -sf -H 'X-User: stable-user-42' -H 'X-Plan: free' -X POST "$BASE/checkout" | grep -o '"path":"[^"]*"')
if [ "$FIRST" = "$SECOND" ]; then
    printf '  \xe2\x9c\x93 sticky assignment: same user gets same variant (%s)\n' "$FIRST"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 sticky assignment failed (%s vs %s)\n' "$FIRST" "$SECOND"
    FAIL=$((FAIL + 1))
fi

# --- Percentage rollout: sweep users, expect ~25% new ---
NEW_COUNT=0
TOTAL=100
for i in $(seq 1 $TOTAL); do
    path=$(curl -sf -H "X-User: sweep-user-$i" -H 'X-Plan: free' -X POST "$BASE/checkout" | grep -o '"path":"[^"]*"' | cut -d'"' -f4)
    if [ "$path" = "new" ]; then
        NEW_COUNT=$((NEW_COUNT + 1))
    fi
done

if [ "$NEW_COUNT" -ge 10 ] && [ "$NEW_COUNT" -le 40 ]; then
    printf '  \xe2\x9c\x93 percentage rollout: %d/%d got new (expected ~25%%)\n' "$NEW_COUNT" "$TOTAL"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 percentage rollout: %d/%d got new (expected 10-40)\n' "$NEW_COUNT" "$TOTAL"
    FAIL=$((FAIL + 1))
fi

# ===================================================================
# 2. Kill switch — recommendations-enabled
# ===================================================================
printf '\n--- 2. Kill switch (recommendations-enabled) ---\n'

check "recommendations are live when flag is on" \
    "curl -sf -H 'X-User: user-1' $BASE/recommendations" \
    '"reason":"live"'

check "recommendations include products" \
    "curl -sf -H 'X-User: user-1' $BASE/recommendations" \
    '"product-a"'

# ===================================================================
# 3. Simple flag — dark-mode
# ===================================================================
printf '\n--- 3. Simple flag (dark-mode, default off) ---\n'

check "dark-mode defaults to false" \
    "curl -sf -H 'X-User: user-1' $BASE/ui-config" \
    '"dark_mode":false'

# ===================================================================
# 4. Debug endpoint shows all flags
# ===================================================================
printf '\n--- 4. Debug endpoint ---\n'

check "flags endpoint returns new-checkout" \
    "curl -sf -H 'X-User: user-1' -H 'X-Plan: enterprise' $BASE/flags" \
    '"new-checkout":true'

check "flags endpoint returns recommendations-enabled" \
    "curl -sf -H 'X-User: user-1' $BASE/flags" \
    '"recommendations-enabled":true'

# ===================================================================
# 5. Fail-safe: flagd down → defaults
# ===================================================================
printf '\n--- 5. Fail-safe (flagd down) ---\n'

printf '  \xe2\x86\x92 stopping flagd...\n'
podman stop cndp-flagd >/dev/null 2>&1
sleep 3

check "checkout returns legacy (default false) with flagd down" \
    "curl -sf -H 'X-User: user-1' -H 'X-Plan: enterprise' -X POST $BASE/checkout" \
    '"path":"legacy"'

check "recommendations return live (default true) with flagd down" \
    "curl -sf -H 'X-User: user-1' $BASE/recommendations" \
    '"reason":"live"'

check "service still returns 200 with flagd down" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'X-User: user-1' $BASE/ui-config" \
    '200'

printf '  \xe2\x86\x92 restarting flagd and flag-service...\n'
podman start cndp-flagd >/dev/null 2>&1
sleep 5
podman restart cndp-flag-service >/dev/null 2>&1

RECOVERED=0
for i in $(seq 1 12); do
    sleep 3
    result=$(curl -sf -H 'X-User: user-1' -H 'X-Plan: enterprise' -X POST "$BASE/checkout" 2>/dev/null) || result=""
    if echo "$result" | grep -q '"path":"new"'; then
        RECOVERED=1
        break
    fi
done
if [ "$RECOVERED" = "1" ]; then
    printf '  \xe2\x9c\x93 service recovers after flagd restart\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 service did not recover after flagd restart\n'
    FAIL=$((FAIL + 1))
fi

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
