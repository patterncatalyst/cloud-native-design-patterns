#!/usr/bin/env bash
# Build, push, deploy and verify Example 05 on OpenShift Local, one language at a time, and collect
# evidence. Results go to a TSV; logs and evidence go under $OUT (default outside the repository).
#
#   openshift/verify-matrix.sh                 # all five languages
#   openshift/verify-matrix.sh go python       # these languages
#   OUT=/path/to/dir openshift/verify-matrix.sh
#
# Per language the run must pass all of: verify.sh (10 checks, over HTTPS through the Route with the
# ingress CA), a linked trace in Tempo (order-service and a consumer in one trace, evidence file
# linked-trace.json), and the restricted-v2 SCC on every application pod. Between languages only the
# cndp-05 project is removed; the operator stays. Run openshift/setup-crc.sh first and
# openshift/teardown.sh when done. Exit status is 1 if any language fails or the evidence scrub finds a secret.
set -uo pipefail
# shellcheck source=lib.sh
# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

OUT="${OUT:-${TMPDIR:-/tmp}/cndp-ocp-matrix}"
mkdir -p "$OUT/logs" "$OUT/evidence"
RESULTS="$OUT/results.tsv"
: >"$RESULTS"

selected=("$@")
[[ ${#selected[@]} -gt 0 ]] || selected=("${LANGS[@]}")
for l in "${selected[@]}"; do valid_lang "$l" || fail "unknown language '$l' (${LANGS[*]})"; done
require_crc
require_alone
[[ -s "$INGRESS_CA" ]] || fail "ingress CA missing in $STATE. Run openshift/setup-crc.sh first"

# linked_trace <outfile>: poll Tempo (inside the lgtm pod) for up to 180 s for a trace that contains
# order-service and at least one consumer. Tempo indexes with a delay. TraceQL && is not relied on:
# the search finds traces by service.name and each trace is read to list its services.
linked_trace() {
    local out="$1" deadline end start ids id services
    deadline=$(( SECONDS + 180 ))
    while (( SECONDS < deadline )); do
        end="$(date +%s)"
        start=$(( end - 3600 ))
        ids="$(ocn exec deploy/lgtm -- curl -s -G 'http://localhost:3200/api/search' \
            --data-urlencode 'tags=service.name=order-service' \
            --data-urlencode "start=$start" --data-urlencode "end=$end" --data-urlencode limit=20 2>/dev/null \
            | jq -r '.traces[]?.traceID' 2>/dev/null)"
        for id in $ids; do
            services="$(ocn exec deploy/lgtm -- curl -s "http://localhost:3200/api/traces/$id" 2>/dev/null \
                | jq -r '[.batches[]?.resource.attributes[]? | select(.key == "service.name") | .value.stringValue] | unique | join(",")' 2>/dev/null)"
            if [[ "$services" == *order-service* && "$services" == *-consumer* ]]; then
                jq -n --arg id "$id" --arg s "$services" '{traceId: $id, services: ($s | split(","))}' >"$out"
                return 0
            fi
        done
        sleep 10
    done
    return 1
}

# scc_table <dir>: pod and SCC for every pod; succeeds when every application pod is restricted-v2.
scc_table() {
    local dir="$1"
    ocn get pods -o json | jq -r '.items[] | [.metadata.name, (.metadata.annotations["openshift.io/scc"] // "none")] | @tsv' >"$dir/scc.tsv"
    ! awk -F'\t' '$1 ~ /^(order-service|shipping-consumer|notification-consumer)-/ && $2 != "restricted-v2" {bad=1} END {exit !bad}' "$dir/scc.tsv"
}

evidence() {  # evidence <lang>
    local dir="$OUT/evidence/$1" host
    mkdir -p "$dir"
    {
        ocn get pods,svc,pvc,route -o wide
        ocn get kafka,kafkanodepool
    } >"$dir/resources.txt" 2>&1
    ocn get kafka cndp -o jsonpath='{.status.kafkaVersion}{"\n"}' >"$dir/kafka-version.txt" 2>&1
    ocn get kafka cndp -o jsonpath='{.status.conditions}' >"$dir/kafka-status.json" 2>&1
    ocn get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}' >"$dir/images.txt" 2>&1
    ocx get csv "$CSV" -n "$OPERATOR_NAMESPACE" -o jsonpath='{.metadata.name}{"\t"}{.status.phase}{"\n"}' >"$dir/csv.txt" 2>&1
    ocx version -o json 2>/dev/null | jq -r '"Kubernetes " + .serverVersion.gitVersion + " (OpenShift " + (.openshiftVersion // "unknown") + ")"' >"$dir/versions.txt" 2>&1
    local d
    for d in order-service shipping-consumer notification-consumer; do
        ocn logs "deployment/$d" --tail=60 >"$dir/$d.log" 2>&1
    done
    host="$(ocn get route lgtm-grafana -o jsonpath='{.spec.host}' 2>/dev/null)"
    curl -s --cacert "$INGRESS_CA" "https://$host/api/health" >"$dir/grafana-health.json" 2>&1
    host="$(ocn get route order-service -o jsonpath='{.spec.host}' 2>/dev/null)"
    # Plain HTTP must redirect to HTTPS (insecureEdgeTerminationPolicy: Redirect).
    curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "http://$host/healthz" >"$dir/http-redirect.txt" 2>&1
}

failed=0
for lang in "${selected[@]}"; do
    log="$OUT/logs/$lang.log"
    start=$(date +%s)
    status=PASS
    host="order-service-$NAMESPACE.apps-crc.testing"
    if ! "$OPENSHIFT_DIR/build-push-images.sh" "$lang" >"$log" 2>&1; then
        status=BUILD-FAIL
    elif ! "$OPENSHIFT_DIR/deploy.sh" "$lang" >>"$log" 2>&1; then
        status=DEPLOY-FAIL
    elif ! (cd "$EXAMPLE_DIR" && RUNTIME=kubernetes KUBECTL=oc KUBE_CONTEXT="$OCP_CONTEXT" KUBE_NAMESPACE="$NAMESPACE" \
            BASE="https://$host" CURL_OPTS="--cacert $INGRESS_CA" timeout 900 ./verify.sh) >>"$log" 2>&1; then
        status=VERIFY-FAIL
    fi
    mkdir -p "$OUT/evidence/$lang"
    scc=-
    trace=-
    if [[ "$status" == PASS || "$status" == VERIFY-FAIL ]]; then
        scc=ok
        trace=ok
        scc_table "$OUT/evidence/$lang" || scc=FAIL
        linked_trace "$OUT/evidence/$lang/linked-trace.json" || trace=FAIL
        evidence "$lang"
        if [[ "$status" == PASS && ( "$scc" != ok || "$trace" != ok ) ]]; then status=EVIDENCE-FAIL; fi
    fi
    if [[ "$status" != PASS ]]; then failed=1; fi
    "$OPENSHIFT_DIR/teardown.sh" --namespace-only >>"$log" 2>&1 || true
    secs=$(( $(date +%s) - start ))
    summary="$(grep -E '==> Results:' "$log" | tail -1 | sed 's/.*Results: //' || true)"
    printf '%-12s\t%s\t%s\ttrace %s\tscc %s\t%ss\n' "$lang" "$status" "${summary:--}" "$trace" "$scc" "$secs" | tee -a "$RESULTS"
done

echo
column -t -s $'\t' "$RESULTS"
if ! scrub_dir "$OUT"; then
    echo "ERROR: the scrub found secret-like material under $OUT" >&2
    failed=1
fi
exit "$failed"
