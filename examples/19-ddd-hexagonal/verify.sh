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

check_empty() {
    local desc="$1" cmd="$2"
    result=$(eval "$cmd" 2>/dev/null) || result=""
    if [ -z "$result" ]; then
        printf '  \xe2\x9c\x93 %s\n' "$desc"
        PASS=$((PASS + 1))
    else
        printf '  \xe2\x9c\x97 %s (found: %s)\n' "$desc" "$result"
        FAIL=$((FAIL + 1))
    fi
}

printf '==> Verifying Example 19: DDD & Hexagonal Architecture\n\n'

# ===================================================================
# 1. Domain isolation — the core cross-check
# ===================================================================
printf -- '--- 1. Domain isolation (zero framework imports) ---\n'

LANG_DIR="${LANG_DIR:-python}"

if [ "$LANG_DIR" = "spring-boot" ]; then
    DOMAIN_DIR="$LANG_DIR/order-service/src/main/java/com/cndp/order/domain"

    check_empty "no Spring imports in domain/" \
        "grep -r 'import org\.springframework' $DOMAIN_DIR"

    check_empty "no Jakarta imports in domain/" \
        "grep -r 'import jakarta\.' $DOMAIN_DIR"

    check_empty "no JPA imports in domain/" \
        "grep -r 'import javax\.persistence\|import jakarta\.persistence' $DOMAIN_DIR"

    check_empty "no JDBC imports in domain/" \
        "grep -r 'import java\.sql\|import org\.springframework\.jdbc' $DOMAIN_DIR"

    check_empty "no Hibernate imports in domain/" \
        "grep -r 'import org\.hibernate' $DOMAIN_DIR"

    check "PlaceOrderUseCase.java imports only domain types" \
        "grep '^import' $DOMAIN_DIR/PlaceOrderUseCase.java | grep -v 'import com\.cndp\.order\.domain\.' | head -1" \
        "^$"
else
    DOMAIN_DIR="$LANG_DIR/order-service/domain"

    check_empty "no fastapi imports in domain/" \
        "grep -r 'import fastapi\|from fastapi' $DOMAIN_DIR"

    check_empty "no asyncpg imports in domain/" \
        "grep -r 'import asyncpg\|from asyncpg' $DOMAIN_DIR"

    check_empty "no pydantic imports in domain/" \
        "grep -r 'import pydantic\|from pydantic' $DOMAIN_DIR"

    check_empty "no uvicorn imports in domain/" \
        "grep -r 'import uvicorn\|from uvicorn' $DOMAIN_DIR"

    check_empty "no starlette imports in domain/" \
        "grep -r 'import starlette\|from starlette' $DOMAIN_DIR"

    check "domain/service.py imports only domain types" \
        "grep '^from\|^import' $DOMAIN_DIR/service.py | grep -v 'from \.' | head -1" \
        "^$"
fi

# ===================================================================
# 2. REST driving adapter — place and retrieve orders
# ===================================================================
printf '\n--- 2. REST driving adapter ---\n'

check "healthz returns ok" \
    "curl -sf $BASE/healthz" \
    '"status":"ok"'

ORDER_JSON=$(curl -sf -X POST "$BASE/orders" \
    -H 'Content-Type: application/json' \
    -d '{"sku":"widget-a","quantity":3}' 2>/dev/null) || ORDER_JSON=""

ORDER_ID=$(echo "$ORDER_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null) || ORDER_ID=""

if [ -n "$ORDER_ID" ]; then
    printf '  \xe2\x9c\x93 POST /orders returned order id\n'
    PASS=$((PASS + 1))
else
    printf '  \xe2\x9c\x97 POST /orders did not return an id\n'
    FAIL=$((FAIL + 1))
fi

check "POST /orders returns status=placed" \
    "echo '$ORDER_JSON'" \
    '"status":"placed"'

check "GET /orders/{id} returns the order" \
    "curl -sf $BASE/orders/$ORDER_ID" \
    "$ORDER_ID"

check "GET /orders lists at least one order" \
    "curl -sf $BASE/orders | python3 -c \"import sys,json; print(len(json.load(sys.stdin)))\"" \
    "^[1-9]"

check "POST /orders rejects invalid input (422)" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/orders -H 'Content-Type: application/json' -d '{\"sku\":\"\",\"quantity\":0}'" \
    "422"

# ===================================================================
# 3. CLI driving adapter — same use case, different entry point
# ===================================================================
printf '\n--- 3. CLI driving adapter (replaceability proof) ---\n'

CLI_OUTPUT=$(podman exec cndp-order-service python cli_place_order.py bolt-x 5 2>/dev/null) || CLI_OUTPUT=""

check "CLI adapter creates order via same use case" \
    "echo '$CLI_OUTPUT'" \
    "CLI_ORDER_CREATED"

check "CLI order has correct sku" \
    "echo '$CLI_OUTPUT'" \
    "sku=bolt-x"

check "CLI order has correct quantity" \
    "echo '$CLI_OUTPUT'" \
    "qty=5"

CLI_ORDER_ID=$(echo "$CLI_OUTPUT" | grep -oP '(?<= )id=\K[^ ]+' 2>/dev/null | head -1) || CLI_ORDER_ID=""

if [ -n "$CLI_ORDER_ID" ]; then
    check "CLI-created order visible via REST GET" \
        "curl -sf $BASE/orders/$CLI_ORDER_ID" \
        "$CLI_ORDER_ID"
else
    printf '  \xe2\x9c\x97 CLI-created order visible via REST GET (no CLI order id)\n'
    FAIL=$((FAIL + 1))
fi

# ===================================================================
# 4. Domain event published
# ===================================================================
printf '\n--- 4. Domain events ---\n'

check "OrderPlaced event logged for REST order" \
    "podman logs cndp-order-service 2>&1" \
    "EVENT OrderPlaced"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
