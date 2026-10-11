#!/usr/bin/env bash
# Build, deploy, verify and tear down Example 05 on minikube, one language at a time.
# Results go to a TSV and per-language logs and evidence under $OUT (default
# outside the repository).
#
#   k8s/verify-matrix.sh                 # all six languages
#   k8s/verify-matrix.sh go python       # these languages
#   OUT=/path/to/dir k8s/verify-matrix.sh
#
# Requires k8s/setup-profile.sh to have run. Exit status is 1 if any language fails.
set -uo pipefail
# shellcheck source=lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

OUT="${OUT:-${TMPDIR:-/tmp}/cndp-k8s-matrix}"
mkdir -p "$OUT/logs" "$OUT/evidence"
RESULTS="$OUT/results.tsv"
: >"$RESULTS"

selected=("$@")
[[ ${#selected[@]} -gt 0 ]] || selected=("${LANGS[@]}")
for l in "${selected[@]}"; do valid_lang "$l" || fail "unknown language '$l' (${LANGS[*]})"; done
minikube status -p "$PROFILE" >/dev/null 2>&1 || fail "profile $PROFILE is not running. Run k8s/setup-profile.sh first."

foreign="$(docker ps --format '{{.Names}}' | grep -vx "$PROFILE" || true)"
[[ -z "$foreign" ]] || fail "containers are running (one workshop at a time): $(tr '\n' ' ' <<<"$foreign")"

evidence() {  # evidence <lang>
    local dir="$OUT/evidence/$1"
    mkdir -p "$dir"
    {
        kcn get pods,svc,pvc -o wide
        kcn get kafka,kafkanodepool
    } >"$dir/resources.txt" 2>&1
    kcn get kafka cndp -o jsonpath='{.status.conditions}' >"$dir/kafka-status.json" 2>&1
    kcn get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}' >"$dir/images.txt" 2>&1
    local d
    for d in order-service shipping-consumer notification-consumer; do
        kcn logs "deployment/$d" --tail=60 >"$dir/$d.log" 2>&1
    done
    curl -s http://127.0.0.1:30300/api/health >"$dir/grafana-health.json" 2>&1
    docker port "$PROFILE" >"$dir/docker-port.txt" 2>&1
}

failed=0
for lang in "${selected[@]}"; do
    log=$OUT/logs/$lang.log
    start=$(date +%s)
    printf '%-12s ' "$lang"
    status=PASS
    if ! "$K8S_DIR/build-images.sh" "$lang" >"$log" 2>&1; then
        status=BUILD-FAIL
    elif ! "$K8S_DIR/deploy.sh" "$lang" >>"$log" 2>&1; then
        status=DEPLOY-FAIL
    elif ! (cd "$EXAMPLE_DIR" && RUNTIME=kubernetes KUBE_CONTEXT="$PROFILE" KUBE_NAMESPACE="$NAMESPACE" \
            BASE=http://127.0.0.1:30080 timeout 900 ./verify.sh) >>"$log" 2>&1; then
        status=VERIFY-FAIL
    fi
    evidence "$lang"
    if [[ "$status" != PASS ]]; then failed=1; fi
    "$K8S_DIR/teardown.sh" >>"$log" 2>&1 || true
    secs=$(( $(date +%s) - start ))
    summary="$(grep -E '==> Results:' "$log" | tail -1 | sed 's/.*Results: //' || true)"
    printf '%s\t%s\t%s\t%ss\n' "$lang" "$status" "${summary:--}" "$secs" | tee -a "$RESULTS"
done

echo
column -t -s $'\t' "$RESULTS"
exit "$failed"
