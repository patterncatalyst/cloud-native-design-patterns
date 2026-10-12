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
ctr_inspect() { docker inspect "$@"; }

GRACE=30  # stop_grace_period in compose.yaml (terminationGracePeriodSeconds on Kubernetes)

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

printf '==> Verifying Example 21: Graceful Shutdown\n\n'

# --- Service is up ---
check "healthz returns ok" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status":"ok"'

check_status "readyz returns 200 (ready)" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' $BASE/readyz" \
    "200"

# --- Place some orders to confirm service works ---
check_status "POST /orders returns 201" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget-before-restart\",\"quantity\":1}' $BASE/orders" \
    "201"

# --- Send ONE SIGTERM (what the kubelet sends) and verify the whole drain ---
# The service flips readiness on that signal, keeps serving for DRAIN_DELAY_SECONDS so
# endpoints update, then stops the server, closes the pool and exits 0. No second signal.
printf '  \xe2\x86\x92 sending a single SIGTERM to order-service...\n'
t0=$(date +%s)
ctr_kill cndp-order-service SIGTERM >/dev/null 2>&1
sleep 2

check "debug/state shows shutting_down=true" \
    "curl $CURL_OPTS -sf $BASE/debug/state" \
    '"shutting_down":true'

check_status "readyz returns 503 after SIGTERM" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' $BASE/readyz" \
    "503"

check "readyz body says shutting down" \
    "curl $CURL_OPTS -sf $BASE/readyz 2>/dev/null || curl $CURL_OPTS -s $BASE/readyz" \
    '"shutting down"'

check_status "healthz still returns 200 while draining" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' $BASE/healthz" \
    "200"

# --- The container exits by itself, with code 0, inside the grace period ---
wait_exit() {
    for _ in $(seq 1 60); do
        [ "$(ctr_inspect -f '{{.State.Running}}' cndp-order-service 2>/dev/null)" = false ] && return 0
        sleep 1
    done
    return 1
}
wait_exit || true
elapsed=$(( $(date +%s) - t0 ))

check "container exited after one SIGTERM (no second signal)" \
    "ctr_inspect -f '{{.State.Running}}' cndp-order-service" \
    '^false$'

check "exit code is 0" \
    "ctr_inspect -f '{{.State.ExitCode}}' cndp-order-service" \
    '^0$'

check_status "drain finished within the 30s grace period (${elapsed}s)" \
    "[ $elapsed -lt $GRACE ] && echo ok" \
    "ok"

# --- Verify logs show the drain protocol (the container is stopped, logs remain) ---
check "logs show SIGTERM received" \
    "ctr_logs cndp-order-service 2>&1" \
    "SIGTERM received"

check "logs show the HTTP server stopping" \
    "ctr_logs cndp-order-service 2>&1" \
    "shutting down HTTP server"

# --- Restart and verify recovery ---
printf '  \xe2\x86\x92 restarting service and verifying recovery...\n'
ctr_start cndp-order-service >/dev/null 2>&1 || true
for _ in $(seq 1 30); do
    [ "$(curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' "$BASE/readyz" 2>/dev/null)" = 200 ] && break
    sleep 2
done

check_status "readyz returns 200 after restart" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' $BASE/readyz" \
    "200"

check_status "POST /orders works after restart" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"sku\":\"widget-after-restart\",\"quantity\":1}' $BASE/orders" \
    "201"

# --- Verify previous orders survived the restart ---
check "orders from before restart are still present" \
    "curl $CURL_OPTS -sf $BASE/orders" \
    'widget-before-restart'

# --- docker stop sends one SIGTERM, then SIGKILL at the timeout: exit 0 before the timeout ---
printf '  \xe2\x86\x92 docker stop (one SIGTERM, SIGKILL after %ss)...\n' "$GRACE"
t0=$(date +%s)
ctr_stop -t "$GRACE" cndp-order-service >/dev/null 2>&1 || true
elapsed=$(( $(date +%s) - t0 ))

check "docker stop: exit code is 0 (not 137 from SIGKILL)" \
    "ctr_inspect -f '{{.State.ExitCode}}' cndp-order-service" \
    '^0$'

check_status "docker stop: drained before the ${GRACE}s timeout (${elapsed}s)" \
    "[ $elapsed -lt $GRACE ] && echo ok" \
    "ok"

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
