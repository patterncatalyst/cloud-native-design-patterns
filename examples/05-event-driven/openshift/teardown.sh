#!/usr/bin/env bash
# Return OpenShift Local to the state it had before Example 05, then stop it. CRC is never deleted.
#
#   openshift/teardown.sh                    # remove everything, revert the registry route, crc stop
#   openshift/teardown.sh --keep-running     # same, leave CRC running
#   openshift/teardown.sh --namespace-only   # only the cndp-05 project; operator and CRC stay (used between languages)
#
# Order matters. Custom resources go while their operator still runs, or their finalizers wait for an
# operator that is gone:
#   1. KafkaTopics and KafkaUsers, then Kafka and KafkaNodePool, then the cndp-05 project
#   2. the Subscription, the CSV, its InstallPlans, the OperatorGroup, the CRDs the CSV owns, then the
#      cndp-amq-streams namespace. The CRDs go only when our Subscription or CSV existed and nothing
#      foreign depends on them: another project's Subscription, CSV or Kafka custom resource keeps
#      them in place (reported, not removed). No other *.strimzi.io CRD is touched.
#   3. the registry default route, only if setup-crc.sh enabled it (annotation cndp-05/enabled-default-route)
#   4. a leftover check: items of ours still present fail the run; items that are not ours are listed
#      as left untouched
#   5. crc stop
# A step that fails or times out is reported and the script continues, so the registry route is
# reverted and CRC is stopped anyway (an EXIT trap runs crc stop in full mode). The exit code is
# non-zero when a step failed or something of ours was left behind. --keep-running and
# --namespace-only never stop CRC.
# Idempotent: a second run finds nothing to do and exits 0, also when CRC is already stopped.
set -uo pipefail
# shellcheck source=lib.sh
# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

mode=full
stop_crc=1
case "${1:-}" in
    "") ;;
    --keep-running) stop_crc=0 ;;
    --namespace-only) mode=namespace; stop_crc=0 ;;
    *) fail "usage: teardown.sh [--keep-running | --namespace-only]" ;;
esac

failed=0
problem() { warn "$*"; failed=1; }
# soft_wait <seconds> <description> <command...>: wait_for, but a timeout is a warning, not an exit.
soft_wait() { ( wait_for "$@" ) || problem "continuing after: $2"; }

require_tools
if ! crc_vm_running; then
    echo "OpenShift Local is not running; nothing to tear down."
    exit 0
fi

# Full mode: whatever happens from here, CRC is stopped on the way out.
finish() {
    local rc=$?
    (( failed )) && rc=1
    if (( stop_crc )) && crc_vm_running; then
        if crc stop >/dev/null 2>&1; then
            printf '    ok: OpenShift Local stopped (not deleted)\n'
        else
            printf 'ERROR: crc stop failed\n' >&2
            rc=1
        fi
    fi
    exit "$rc"
}
trap finish EXIT
require_crc

kafka_pods_gone() { [[ -z "$(ocx get pod -n "$NAMESPACE" -l strimzi.io/cluster=cndp -o name 2>/dev/null)" ]]; }

step "1/5 Project $NAMESPACE"
if ocx get namespace "$NAMESPACE" >/dev/null 2>&1; then
    if has_crd kafkas.kafka.strimzi.io; then
        # KafkaTopics first: their finalizer hangs the namespace once the operator is gone.
        ocn delete kafkatopics.kafka.strimzi.io,kafkausers.kafka.strimzi.io --all --wait=true --timeout=120s >/dev/null 2>&1 || true
        ocn delete kafka,kafkanodepool --all --wait=true --timeout=300s >/dev/null 2>&1 || warn "deleting Kafka did not finish; continuing"
        soft_wait 300 "Kafka pods gone" kafka_pods_gone
    fi
    ocx delete namespace "$NAMESPACE" --wait=false >/dev/null 2>&1 || problem "delete namespace $NAMESPACE failed"
    soft_wait 600 "namespace $NAMESPACE deleted" gone namespace "$NAMESPACE"
else
    ok "no project $NAMESPACE"
fi

if [[ "$mode" == namespace ]]; then
    echo
    echo "Kept the operator in $OPERATOR_NAMESPACE and CRC running."
    exit 0
fi

step "2/5 AMQ Streams operator"
csv="$(ocx get subscriptions.operators.coreos.com amq-streams -n "$OPERATOR_NAMESPACE" -o jsonpath='{.status.installedCSV}' 2>/dev/null || true)"
[[ -n "$csv" ]] || csv="$CSV"
# OLM labels every CRD our Subscription installed with operators.coreos.com/<package>.<namespace>.
# The label names our operator namespace, so another project's install carries a different one, and
# it outlives the CSV: a CRD kept by an earlier run (because foreign items used it) is still found.
olm_crds() { ocx get crd -l "$OLM_CRD_LABEL" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null | grep -v '^$' || true; }
# What of ours exists: the Subscription or the CSV in our namespace, or CRDs carrying our label.
# Without any of them, no CRD is ours to remove.
ours_existed=0
if ocx get subscriptions.operators.coreos.com amq-streams -n "$OPERATOR_NAMESPACE" >/dev/null 2>&1 \
    || ocx get csv "$csv" -n "$OPERATOR_NAMESPACE" >/dev/null 2>&1 \
    || [[ -n "$(olm_crds)" ]]; then
    ours_existed=1
fi
# The CRDs the CSV owns (read before the CSV is gone) plus those carrying our label.
owned="$(
    { ocx get csv "$csv" -n "$OPERATOR_NAMESPACE" -o jsonpath='{range .spec.customresourcedefinitions.owned[*]}{.name}{"\n"}{end}' 2>/dev/null; olm_crds; } \
        | grep -v '^$' | sort -u || true
)"

# Foreign check, before any CRD goes: another project's Kafka operator or Kafka resources, or custom
# resources of the owned kinds outside our project (cndp-05 is already deleted at this point).
foreign="$(foreign_kafka_items)"
for crd in $owned; do
    has_crd "$crd" || continue
    instances="$(ocx get "$crd" -A --no-headers -o custom-columns=NS:.metadata.namespace,NAME:.metadata.name 2>/dev/null | awk -v k="${crd%%.*}" '{print k " " $1 "/" $2}')"
    [[ -z "$instances" ]] || foreign+=$'\n'"$instances"
done
foreign="$(grep -v '^$' <<<"$foreign" | sort -u || true)"

ocx delete subscriptions.operators.coreos.com amq-streams -n "$OPERATOR_NAMESPACE" --ignore-not-found >/dev/null 2>&1 || problem "delete Subscription failed"
ocx delete csv "$csv" -n "$OPERATOR_NAMESPACE" --ignore-not-found --wait=true --timeout=180s >/dev/null 2>&1 || problem "delete CSV $csv failed"
for plan in $(ocx get installplan -n "$OPERATOR_NAMESPACE" -o json 2>/dev/null | jq -r --arg c "$csv" '.items[] | select(.spec.clusterServiceVersionNames | index($c)) | .metadata.name'); do
    ocx delete installplan "$plan" -n "$OPERATOR_NAMESPACE" --ignore-not-found >/dev/null 2>&1 || problem "delete InstallPlan $plan failed"
done
ocx delete operatorgroup cndp-amq-streams -n "$OPERATOR_NAMESPACE" --ignore-not-found >/dev/null 2>&1 || problem "delete OperatorGroup failed"
ok "$csv, its InstallPlans and OperatorGroup removed"

kept_crds=""
if (( ! ours_existed )); then
    ok "no Subscription or CSV of ours in $OPERATOR_NAMESPACE: no CRD removed"
elif [[ -z "$owned" ]]; then
    warn "neither the CSV's owned CRD list nor CRDs labelled $OLM_CRD_LABEL were found: no CRD removed"
    failed=1
elif [[ -n "$foreign" ]]; then
    kept_crds="$owned"
    warn "kept $(wc -w <<<"$owned") CRD(s) the CSV owns, because items that are not ours use them:"
    while IFS= read -r line; do echo "      $line" >&2; done <<<"$foreign"
    echo "    remove them with that project's teardown, then re-run this script" >&2
else
    before=0
    for crd in $owned; do has_crd "$crd" && before=$(( before + 1 )); done
    # shellcheck disable=SC2086  # one CRD name per word
    ocx delete crd $owned --ignore-not-found --wait=true --timeout=180s >/dev/null 2>&1 || true
    after=0
    for crd in $owned; do has_crd "$crd" && after=$(( after + 1 )); done
    ok "$(( before - after )) of $before owned CRD(s) removed"
    (( after == 0 )) || problem "$after owned CRD(s) still present"
fi
if ocx get namespace "$OPERATOR_NAMESPACE" >/dev/null 2>&1; then
    ocx delete namespace "$OPERATOR_NAMESPACE" --wait=false >/dev/null 2>&1 || problem "delete namespace $OPERATOR_NAMESPACE failed"
    soft_wait 300 "namespace $OPERATOR_NAMESPACE deleted" gone namespace "$OPERATOR_NAMESPACE"
fi

step "3/5 Registry default route"
registry_config=configs.imageregistry.operator.openshift.io/cluster
if [[ "$(ocx get "$registry_config" -o json 2>/dev/null | jq -r --arg k "$ROUTE_ANNOTATION" '.metadata.annotations[$k] // ""')" == true ]]; then
    if ocx patch "$registry_config" --type merge -p '{"spec":{"defaultRoute":false}}' >/dev/null 2>&1 \
        && ocx annotate "$registry_config" "${ROUTE_ANNOTATION}-" >/dev/null 2>&1; then
        ok "default route disabled again"
    else
        problem "could not revert the registry default route"
    fi
else
    ok "default route left as found"
fi

step "4/5 Leftover check"
ours="$(
    ocx get subscriptions.operators.coreos.com amq-streams -n "$OPERATOR_NAMESPACE" --no-headers -o name 2>/dev/null
    ocx get csv "$csv" -n "$OPERATOR_NAMESPACE" --no-headers -o name 2>/dev/null
    ocx get operatorgroup cndp-amq-streams -n "$OPERATOR_NAMESPACE" --no-headers -o name 2>/dev/null
    ocx get ns -o name 2>/dev/null | grep -E "^namespace/($NAMESPACE|$OPERATOR_NAMESPACE)$"
    for crd in $owned; do
        # CRDs kept on purpose because of foreign items are reported below, not counted as ours.
        grep -qxF "$crd" <<<"$kept_crds" && continue
        has_crd "$crd" && echo "crd/$crd"
    done
    ocx get clusterrolebinding -o name 2>/dev/null | grep -E 'cndp'
)"
ours="$(grep -v '^$' <<<"$ours" || true)"
not_ours="$(
    ocx get subscriptions.operators.coreos.com -A --no-headers 2>/dev/null | awk '{print "subscription " $1 "/" $2}'
    ocx get csv -A -l '!olm.copiedFrom' --no-headers 2>/dev/null | awk '$2 !~ /^packageserver/ {print "csv " $1 "/" $2}'
    for crd in $kept_crds; do echo "crd/$crd (kept: used by items that are not ours)"; done
)"
not_ours="$(grep -v '^$' <<<"$not_ours" || true)"
if [[ -z "$ours" ]]; then
    ok "nothing of Example 05 is left"
else
    failed=1
    echo "    of ours, still present:" >&2
    while IFS= read -r line; do echo "      $line" >&2; done <<<"$ours"
fi
if [[ -n "$not_ours" ]]; then
    echo "    not ours, left untouched:"
    while IFS= read -r line; do echo "      $line"; done <<<"$not_ours"
fi
echo "  cluster inventory:"
inventory

# The state directory holds only the public ingress CA.
rm -rf "$STATE"

if (( stop_crc )); then
    step "5/5 crc stop"
    # The EXIT trap runs crc stop and reports it.
fi
