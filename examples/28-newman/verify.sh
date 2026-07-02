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

printf '==> Verifying Example 28: Newman API Testing\n\n'

# --- Service healthy ---
check "healthz returns ok" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

# ===================================================================
# 1. Newman collection run (green path)
# ===================================================================
printf '\n--- 1. Newman collection run ---\n'

if ! command -v newman &>/dev/null; then
    printf '  \xe2\x9c\x97 newman not installed (npm install -g newman)\n'
    FAIL=$((FAIL + 1))
    printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
    printf '==> FAIL\n'
    exit 1
fi

NEWMAN_OUTPUT=$(newman run collections/orders.postman_collection.json \
    --reporters cli \
    --timeout-request 5000 \
    --color off 2>&1)
NEWMAN_EXIT=$?

if [ "$NEWMAN_EXIT" -eq 0 ]; then
    printf '  \xe2\x9c\x93 newman run passed (all assertions green)\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 newman run failed (exit code %d)\n' "$NEWMAN_EXIT"
    echo "$NEWMAN_OUTPUT" | tail -20
    FAIL=$((FAIL + 1))
fi

# Parse assertions line: │ assertions │ NN │ NN │
ASSERTION_LINE=$(echo "$NEWMAN_OUTPUT" | grep 'assertions' | head -1)
TOTAL_ASSERTIONS=$(echo "$ASSERTION_LINE" | awk -F'│' '{gsub(/[^0-9]/,"",$3); print $3}')
FAILED_ASSERTIONS=$(echo "$ASSERTION_LINE" | awk -F'│' '{gsub(/[^0-9]/,"",$4); print $4}')
if [ -n "$TOTAL_ASSERTIONS" ] && [ "$TOTAL_ASSERTIONS" -gt 0 ] && [ "$FAILED_ASSERTIONS" = "0" ]; then
    printf '  \xe2\x9c\x93 %s assertions, 0 failures\n' "$TOTAL_ASSERTIONS"
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 assertion count: %s total, %s failures\n' "${TOTAL_ASSERTIONS:-0}" "${FAILED_ASSERTIONS:-0}"
    FAIL=$((FAIL + 1))
fi

# ===================================================================
# 2. Verify specific test results
# ===================================================================
printf '\n--- 2. Specific test assertions ---\n'

check "newman output shows 201 Created test" \
    "echo '$NEWMAN_OUTPUT'" \
    '201 Created'

check "newman output shows 422 Unprocessable test" \
    "echo '$NEWMAN_OUTPUT'" \
    '422 Unprocessable'

check "newman output shows 404 Not Found test" \
    "echo '$NEWMAN_OUTPUT'" \
    '404 Not Found'

check "newman output shows 204 No Content test" \
    "echo '$NEWMAN_OUTPUT'" \
    '204 No Content'

check "newman output shows status is cancelled test" \
    "echo '$NEWMAN_OUTPUT'" \
    'status is cancelled'

# ===================================================================
# 3. JUnit XML output for CI
# ===================================================================
printf '\n--- 3. JUnit XML output ---\n'

JUNIT_DIR=$(mktemp -d)
newman run collections/orders.postman_collection.json \
    --reporters junit \
    --reporter-junit-export "$JUNIT_DIR/newman.xml" \
    --timeout-request 5000 \
    --color off >/dev/null 2>&1

if [ -f "$JUNIT_DIR/newman.xml" ]; then
    printf '  \xe2\x9c\x93 JUnit XML report generated\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 JUnit XML report not generated\n'
    FAIL=$((FAIL + 1))
fi

check "JUnit XML contains testsuites" \
    "cat '$JUNIT_DIR/newman.xml'" \
    'testsuites'

check "JUnit XML contains testcase elements" \
    "cat '$JUNIT_DIR/newman.xml'" \
    'testcase'

rm -rf "$JUNIT_DIR"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
