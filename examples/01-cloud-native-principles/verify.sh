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

PASS=0
FAIL=0

check() {
    local desc="$1" cmd="$2" expected="$3"
    result=$(eval "$cmd" 2>/dev/null) || result=""
    if echo "$result" | grep -q "$expected"; then
        printf '  ✓ %s\n' "$desc"
        PASS=$((PASS + 1))
    else
        printf '  ✗ %s (expected "%s", got "%s")\n' "$desc" "$expected" "$result"
        FAIL=$((FAIL + 1))
    fi
}

printf '==> Verifying Example 01: Cloud-Native Principles\n\n'

# Factor III — config from environment
check "root returns service name from config" \
    "curl $CURL_OPTS -sf $BASE/" \
    '"service":"order-service"'

check "root returns version from SERVICE_VERSION env" \
    "curl $CURL_OPTS -sf $BASE/" \
    '"version":"1.0.0"'

check "root confirms config source is environment" \
    "curl $CURL_OPTS -sf $BASE/" \
    '"config_source":"environment"'

# Liveness probe
check "liveness probe returns ok" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status":"ok"'

# Readiness probe (DB is up)
check "readiness probe returns 200 when DB is up" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' $BASE/readyz" \
    '^200$'

check "readiness probe returns ready when DB is up" \
    "curl $CURL_OPTS -sf $BASE/readyz" \
    '"status":"ready"'

# CRUD — create and list
check "create order returns id" \
    "curl $CURL_OPTS -sf -X POST '$BASE/orders?customer=alice&total=42.50'" \
    '"id"'

check "list orders returns created order" \
    "curl $CURL_OPTS -sf $BASE/orders" \
    '"customer":"alice"'

# Readiness flips when DB goes down
printf '\n  → stopping postgres to test readiness flip...\n'
ctr_stop cndp-postgres >/dev/null 2>&1
sleep 2

check "readiness returns 503 when DB is stopped" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' $BASE/readyz" \
    '^503$'

check "readiness body reports down when DB is stopped" \
    "curl $CURL_OPTS -s $BASE/readyz" \
    '"status":"down"'

check "liveness still returns 200 when DB is stopped" \
    "curl $CURL_OPTS -s -o /dev/null -w '%{http_code}' $BASE/healthz" \
    '^200$'

check "liveness still returns ok when DB is stopped" \
    "curl $CURL_OPTS -sf $BASE/healthz" \
    '"status":"ok"'

# Restart DB
printf '  → restarting postgres...\n'
ctr_start cndp-postgres >/dev/null 2>&1
sleep 5

check "readiness recovers after DB restart" \
    "curl $CURL_OPTS -sf $BASE/readyz" \
    '"status":"ready"'

printf '\n==> Results: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]] && printf '==> PASS\n' || { printf '==> FAIL\n'; exit 1; }
