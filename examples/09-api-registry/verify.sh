#!/usr/bin/env bash
set -euo pipefail

REGISTRY="http://localhost:8081/apis/registry/v3"
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

printf '==> Verifying Example 09: API Registry\n\n'

# --- Apicurio is up ---
check "Apicurio health check" \
    "curl -sf http://localhost:8081/health/ready" \
    '"status"'

# --- Create a group ---
printf '  \xe2\x86\x92 creating group and registering initial schema...\n'

# --- Register the initial schema (v1) ---
REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "$REGISTRY/groups/orders/artifacts" \
    -H "Content-Type: application/json" \
    -d "{
        \"artifactId\": \"order-placed\",
        \"artifactType\": \"AVRO\",
        \"firstVersion\": {
            \"version\": \"1.0.0\",
            \"content\": {
                \"content\": $(jq -Rs '.' < schemas/order-placed-v1.avsc),
                \"contentType\": \"application/json\"
            }
        }
    }")
REGISTER_CODE=$(echo "$REGISTER_RESPONSE" | tail -1)

if [ "$REGISTER_CODE" = "200" ] || [ "$REGISTER_CODE" = "201" ]; then
    printf '  \xe2\x9c\x93 registered order-placed v1 schema (%s)\n' "$REGISTER_CODE"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 failed to register v1 schema (got %s)\n' "$REGISTER_CODE"
    printf '    response: %s\n' "$(echo "$REGISTER_RESPONSE" | head -5)"
    FAIL=$((FAIL + 1))
fi

# --- Set BACKWARD compatibility rule ---
RULE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "$REGISTRY/groups/orders/artifacts/order-placed/rules" \
    -H "Content-Type: application/json" \
    -d '{ "ruleType": "COMPATIBILITY", "config": "BACKWARD" }')
RULE_CODE=$(echo "$RULE_RESPONSE" | tail -1)

if [ "$RULE_CODE" = "200" ] || [ "$RULE_CODE" = "204" ]; then
    printf '  \xe2\x9c\x93 set BACKWARD compatibility rule (%s)\n' "$RULE_CODE"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 failed to set compatibility rule (got %s)\n' "$RULE_CODE"
    printf '    response: %s\n' "$(echo "$RULE_RESPONSE" | head -5)"
    FAIL=$((FAIL + 1))
fi

# --- Verify the rule is set ---
check "compatibility rule is BACKWARD" \
    "curl -sf '$REGISTRY/groups/orders/artifacts/order-placed/rules/COMPATIBILITY'" \
    "BACKWARD"

# --- Try a BREAKING change (rename required fields) → expect 409 ---
printf '  \xe2\x86\x92 attempting breaking schema change (renamed fields)...\n'
BREAKING_CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST \
    "$REGISTRY/groups/orders/artifacts/order-placed/versions" \
    -H "Content-Type: application/json" \
    -d "{
        \"version\": \"2.0.0-breaking\",
        \"content\": {
            \"content\": $(jq -Rs '.' < schemas/order-placed-v2-breaking.avsc),
            \"contentType\": \"application/json\"
        }
    }")

if [ "$BREAKING_CODE" = "409" ]; then
    printf '  \xe2\x9c\x93 breaking change rejected with 409 Conflict\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 breaking change should return 409 (got %s)\n' "$BREAKING_CODE"
    FAIL=$((FAIL + 1))
fi

# --- Try an ADDITIVE change (new optional field) → expect 200 ---
printf '  \xe2\x86\x92 attempting additive schema change (new optional field)...\n'
ADDITIVE_CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST \
    "$REGISTRY/groups/orders/artifacts/order-placed/versions" \
    -H "Content-Type: application/json" \
    -d "{
        \"version\": \"2.0.0\",
        \"content\": {
            \"content\": $(jq -Rs '.' < schemas/order-placed-v2-additive.avsc),
            \"contentType\": \"application/json\"
        }
    }")

if [ "$ADDITIVE_CODE" = "200" ]; then
    printf '  \xe2\x9c\x93 additive change accepted (200 OK)\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 additive change should return 200 (got %s)\n' "$ADDITIVE_CODE"
    FAIL=$((FAIL + 1))
fi

# --- Verify we now have 2 versions ---
check "artifact has 2 versions" \
    "curl -sf '$REGISTRY/groups/orders/artifacts/order-placed/versions' | jq '.count'" \
    "2"

# --- Fetch the latest version and verify it has the new field ---
check "latest version contains merchant_id field" \
    "curl -sf '$REGISTRY/groups/orders/artifacts/order-placed/versions/2.0.0/content'" \
    "merchant_id"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
