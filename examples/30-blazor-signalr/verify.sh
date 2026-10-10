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
  bash -c "curl $CURL_OPTS -sf $BASE/healthz | grep -q ok"

# 2 — place an order via REST API
ORDER=$(curl $CURL_OPTS -sf -X POST "$BASE/orders" \
  -H "Content-Type: application/json" \
  -d '{"sku":"WIDGET-1","quantity":3}')
check "POST /orders returns 201 with id" \
  bash -c "echo '$ORDER' | grep -q id"

# 3 — list orders
check "GET /orders returns placed order" \
  bash -c "curl $CURL_OPTS -sf $BASE/orders | grep -q WIDGET-1"

# 4 — Blazor dashboard page is served
check "Dashboard page is served (HTML)" \
  bash -c "curl $CURL_OPTS -sf $BASE/dashboard | grep -q 'blazor.web.js'"

# 5 — SignalR negotiate endpoint exists
check "SignalR negotiate endpoint responds" \
  bash -c "curl $CURL_OPTS -sf -X POST '$BASE/hubs/orders/negotiate?negotiateVersion=1' -H 'Content-Type: application/json' | grep -q connectionToken"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
