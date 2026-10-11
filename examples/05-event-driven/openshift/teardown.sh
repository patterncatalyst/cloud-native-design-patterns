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
#   2. the Subscription, the CSV, its InstallPlans, the OperatorGroup, the CRDs the CSV owns and
#      every *.strimzi.io CRD, then the cndp-amq-streams namespace
#   3. the registry default route, only if setup-crc.sh enabled it (annotation cndp-05/enabled-default-route)
#   4. a leftover check that reports, and never removes, items that are not ours
#   5. crc stop
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

require_tools
if ! crc_vm_running; then
    echo "OpenShift Local is not running; nothing to tear down."
    exit 0
fi
require_crc

kafka_pods_gone() { [[ -z "$(ocx get pod -n "$NAMESPACE" -l strimzi.io/cluster=cndp -o name 2>/dev/null)" ]]; }

step "1/5 Project $NAMESPACE"
if ocx get namespace "$NAMESPACE" >/dev/null 2>&1; then
    if has_crd kafkas.kafka.strimzi.io; then
        # KafkaTopics first: their finalizer hangs the namespace once the operator is gone.
        ocn delete kafkatopics.kafka.strimzi.io,kafkausers.kafka.strimzi.io --all --wait=true --timeout=120s >/dev/null 2>&1 || true
        ocn delete kafka,kafkanodepool --all --wait=true --timeout=300s >/dev/null 2>&1 || warn "deleting Kafka did not finish; continuing"
        wait_for 300 "Kafka pods gone" kafka_pods_gone
    fi
    ocx delete namespace "$NAMESPACE" --wait=false >/dev/null
    wait_for 600 "namespace $NAMESPACE deleted" gone namespace "$NAMESPACE"
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
# Read the CRDs the CSV owns before the CSV is gone.
owned="$(ocx get csv "$csv" -n "$OPERATOR_NAMESPACE" -o jsonpath='{range .spec.customresourcedefinitions.owned[*]}{.name}{"\n"}{end}' 2>/dev/null || true)"
ocx delete subscriptions.operators.coreos.com amq-streams -n "$OPERATOR_NAMESPACE" --ignore-not-found >/dev/null 2>&1
ocx delete csv "$csv" -n "$OPERATOR_NAMESPACE" --ignore-not-found --wait=true >/dev/null 2>&1
for plan in $(ocx get installplan -n "$OPERATOR_NAMESPACE" -o json 2>/dev/null | jq -r --arg c "$csv" '.items[] | select(.spec.clusterServiceVersionNames | index($c)) | .metadata.name'); do
    ocx delete installplan "$plan" -n "$OPERATOR_NAMESPACE" --ignore-not-found >/dev/null 2>&1
done
ocx delete operatorgroup cndp-amq-streams -n "$OPERATOR_NAMESPACE" --ignore-not-found >/dev/null 2>&1
crds="$( { printf '%s\n' "$owned"; ocx get crd -o name 2>/dev/null | sed 's#^customresourcedefinition.apiextensions.k8s.io/##' | grep -E '\.strimzi\.io$' || true; } | sort -u | grep -v '^$' || true)"
if [[ -n "$crds" ]]; then
    # shellcheck disable=SC2086  # one CRD name per word
    ocx delete crd $crds --ignore-not-found --wait=true >/dev/null 2>&1
fi
ok "$csv, its InstallPlans, OperatorGroup and $(wc -w <<<"$crds") CRD(s) removed"
if ocx get namespace "$OPERATOR_NAMESPACE" >/dev/null 2>&1; then
    ocx delete namespace "$OPERATOR_NAMESPACE" --wait=false >/dev/null
    wait_for 300 "namespace $OPERATOR_NAMESPACE deleted" gone namespace "$OPERATOR_NAMESPACE"
fi

step "3/5 Registry default route"
registry_config=configs.imageregistry.operator.openshift.io/cluster
if [[ "$(ocx get "$registry_config" -o json 2>/dev/null | jq -r --arg k "$ROUTE_ANNOTATION" '.metadata.annotations[$k] // ""')" == true ]]; then
    ocx patch "$registry_config" --type merge -p '{"spec":{"defaultRoute":false}}' >/dev/null
    ocx annotate "$registry_config" "${ROUTE_ANNOTATION}-" >/dev/null
    ok "default route disabled again"
else
    ok "default route left as found"
fi

step "4/5 Leftover check"
leftover="$(
    ocx get subscriptions.operators.coreos.com -A --no-headers 2>/dev/null
    ocx get csv -A --no-headers 2>/dev/null | awk '$2 !~ /^packageserver/'
    ocx get ns --no-headers -o name 2>/dev/null | grep -E "^namespace/($NAMESPACE|$OPERATOR_NAMESPACE)$"
    ocx get crd -o name 2>/dev/null | grep -E '\.strimzi\.io$'
    ocx get clusterrolebinding -o name 2>/dev/null | grep -E 'cndp'
)"
if [[ -z "$leftover" ]]; then
    ok "nothing of Example 05 is left"
else
    echo "    still present (reported, not removed):"
    while IFS= read -r line; do echo "      $line"; done <<<"$leftover"
fi
echo "  cluster inventory:"
inventory

# The state directory holds only the public ingress CA.
rm -rf "$STATE"

if (( stop_crc )); then
    step "5/5 crc stop"
    if crc stop >/dev/null 2>&1; then ok "OpenShift Local stopped (not deleted)"; else fail "crc stop failed"; fi
fi
