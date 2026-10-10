#!/usr/bin/env bash
# shellcheck disable=SC2086  # $CURL_OPTS is intentionally word-split
set -euo pipefail

RUNTIME="${RUNTIME:-docker}"
BASE="${BASE:-http://localhost:8080}"
BASE2="${BASE2:-http://localhost:8081}"  # second dashboard instance, same Redis backplane
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

# The scale-out checks use a minimal SignalR (JSON protocol over WebSocket) client in
# Python. If the host python3 lacks `websockets`, install a pinned copy into a cached venv.
PY=python3
if ! python3 -c 'import websockets' 2>/dev/null; then
    VENV="${XDG_CACHE_HOME:-$HOME/.cache}/cndp-verify/venv"
    [ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
    "$VENV/bin/python" -c 'import websockets' 2>/dev/null \
        || "$VENV/bin/pip" install -q --disable-pip-version-check websockets==17.2
    PY="$VENV/bin/python"
fi

# relay_check <listen-base> <publish-base> <sku>
# Connects a SignalR client to the hub on <listen-base>, joins the dashboard group, then
# POSTs an order through <publish-base>. Prints "RECEIVED <sku>" when the client gets the
# OrderPlaced push (which, for two different instances, only the Redis backplane can deliver).
relay_check() {
  "$PY" - "$@" <<'PYEOF'
import asyncio, json, sys, urllib.request
import websockets

listen, publish, sku = sys.argv[1:4]
RS = "\x1e"

def post(url, body=b""):
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)

async def frames(ws):
    buf = ""
    while True:
        buf += await ws.recv()
        *done, buf = buf.split(RS)
        for f in done:
            if f:
                yield json.loads(f)

async def main():
    token = post(f"{listen}/hubs/orders/negotiate?negotiateVersion=1")["connectionToken"]
    uri = listen.replace("http", "ws", 1) + f"/hubs/orders?id={token}"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"protocol": "json", "version": 1}) + RS)
        got = frames(ws)
        await anext(got)  # handshake response {}
        await ws.send(json.dumps({"type": 1, "invocationId": "1",
                                  "target": "JoinDashboard", "arguments": []}) + RS)
        async for m in got:
            if m.get("type") == 3 and m.get("invocationId") == "1":
                break
        post(f"{publish}/orders",
             json.dumps({"sku": sku, "quantity": 1}).encode())
        async for m in got:
            if m.get("type") == 1 and m.get("target") == "OrderPlaced":
                if m["arguments"][0].get("sku") == sku:
                    print("RECEIVED " + sku)
                    return

try:
    asyncio.run(asyncio.wait_for(main(), 15))
except Exception as e:  # timeout or connection failure: no RECEIVED line
    print("ERROR", type(e).__name__, e, file=sys.stderr)
PYEOF
}

wait_healthy() {  # wait_healthy <base> : poll /healthz for up to 60 s
  for _ in $(seq 1 30); do
    curl $CURL_OPTS -sf "$1/healthz" >/dev/null 2>&1 && return 0
    sleep 2
  done
  return 1
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

# 6 — second instance is up
check "second dashboard instance healthz returns ok" \
  bash -c "curl $CURL_OPTS -sf $BASE2/healthz | grep -q ok"

# 7 — Redis backplane: client on instance 2, order published through instance 1
check "backplane: order posted to instance 1 reaches a SignalR client on instance 2" \
  bash -c "$(declare -f relay_check); PY='$PY'; CURL_OPTS='$CURL_OPTS'; relay_check '$BASE2' '$BASE' fanout-1-to-2 | grep -q 'RECEIVED fanout-1-to-2'"

# 8 — and the other direction
check "backplane: order posted to instance 2 reaches a SignalR client on instance 1" \
  bash -c "$(declare -f relay_check); PY='$PY'; relay_check '$BASE' '$BASE2' fanout-2-to-1 | grep -q 'RECEIVED fanout-2-to-1'"

# 9 — an order placed on one instance is visible from the other (shared Postgres)
check "order posted to instance 1 is listed by instance 2" \
  bash -c "curl $CURL_OPTS -sf $BASE2/orders | grep -q fanout-1-to-2"

# 10 — the backplane survives an instance restart: a fresh client on the restarted
# instance still receives a push published through the other one
restart_instance2() {  # fails unless the container really restarted and came back healthy
  local before after
  before=$(docker inspect -f '{{.State.StartedAt}}' cndp-order-service-2) || return 1
  ctr_stop cndp-order-service-2 >/dev/null 2>&1 || return 1
  ctr_start cndp-order-service-2 >/dev/null 2>&1 || return 1
  after=$(docker inspect -f '{{.State.StartedAt}}' cndp-order-service-2) || return 1
  [[ "$before" != "$after" ]] || return 1
  wait_healthy "$BASE2"
}

printf '  → restarting instance 2...\n'
check "backplane: restarted instance 2 (new start time, healthy again) still receives pushes published through instance 1" \
  bash -c "$(declare -f restart_instance2 wait_healthy ctr_stop ctr_start relay_check); PY='$PY'; CURL_OPTS='$CURL_OPTS'; BASE='$BASE'; BASE2='$BASE2'; restart_instance2 && relay_check '$BASE2' '$BASE' after-restart | grep -q 'RECEIVED after-restart'"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
