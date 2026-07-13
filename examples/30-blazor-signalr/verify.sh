#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:8080"
PASS=0; FAIL=0

check() {
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  ✔ $label"; PASS=$((PASS+1))
  else
    echo "  ✘ $label"; FAIL=$((FAIL+1))
  fi
}

echo "▸ Blazor Server + SignalR checks"

# 1 — health
check "healthz returns ok" \
  bash -c "curl -sf $BASE/healthz | grep -q ok"

# 2 — place an order via REST API
ORDER=$(curl -sf -X POST "$BASE/orders" \
  -H "Content-Type: application/json" \
  -d '{"sku":"WIDGET-1","quantity":3}')
check "POST /orders returns 201 with id" \
  bash -c "echo '$ORDER' | grep -q id"

# 3 — list orders
check "GET /orders returns placed order" \
  bash -c "curl -sf $BASE/orders | grep -q WIDGET-1"

# 4 — Blazor dashboard page is served
check "Dashboard page is served (HTML)" \
  bash -c "curl -sf $BASE/dashboard | grep -q 'blazor.web.js'"

# 5 — SignalR negotiate endpoint exists
check "SignalR negotiate endpoint responds" \
  bash -c "curl -sf -X POST '$BASE/hubs/orders/negotiate?negotiateVersion=1' -H 'Content-Type: application/json' | grep -q connectionToken"

echo ""
echo "Result: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
