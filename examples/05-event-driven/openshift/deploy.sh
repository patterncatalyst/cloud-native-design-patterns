#!/usr/bin/env bash
# Deploy Example 05 for one language into the cndp-05 project on OpenShift Local.
#
# Order: inventory and foreign-operator check, the AMQ Streams operator (pinned CSV, Manual approval,
# one InstallPlan approved), namespace, infrastructure (Kafka, Postgres, LGTM) and wait for it, then the
# language overlay and a health poll through the Route. The images must already be pushed:
# openshift/build-push-images.sh <lang>.
#
#   openshift/deploy.sh go
set -euo pipefail
# shellcheck source=lib.sh
# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -eq 1 ]] || fail "usage: deploy.sh <lang> (${LANGS[*]})"
lang="$1"
valid_lang "$lang" || fail "unknown language '$lang' (${LANGS[*]})"
require_crc
[[ -s "$INGRESS_CA" ]] || fail "ingress CA missing in $STATE. Run openshift/setup-crc.sh first"

step "Waiting for the cluster to be stable"
wait_for 1800 "cluster operators settled" cluster_settled

step "Inventory before"
inventory
refuse_foreign_kafka_operator

step "AMQ Streams operator $CSV"
install_operator
wait_for 120 "Kafka CRD established" ocx wait --for=condition=Established crd/kafkas.kafka.strimzi.io --timeout=5s

step "Namespace $NAMESPACE and infrastructure"
apply_retry -f "$K8S_DIR/namespace.yaml"
render "$OPENSHIFT_DIR/infra" | apply_retry -f -
echo "    waiting for Kafka (up to 900 s)"
ocn wait kafka/cndp --for=condition=Ready --timeout=900s \
    || fail "Kafka cndp is not Ready (oc --context $OCP_CONTEXT -n $NAMESPACE describe kafka cndp)"
ocn rollout status statefulset/cndp-postgres --timeout=300s
ocn rollout status deployment/lgtm --timeout=300s

step "Overlay $lang"
# The images live in the project's ImageStreams, which go away with the project. Fail early
# rather than wait for a rollout that can only end in ImagePullBackOff.
for svc in "${SERVICES[@]}"; do
    ocn get istag "${lang}-${svc}:${IMAGE_TAG}" >/dev/null 2>&1 \
        || fail "image ${lang}-${svc}:${IMAGE_TAG} is not in project $NAMESPACE. Run openshift/build-push-images.sh $lang first"
done
render "$OPENSHIFT_DIR/overlays/$lang" | apply_retry -f -
for d in shipping-consumer notification-consumer order-service; do
    ocn rollout status "deployment/$d" --timeout=420s
done

host="$(ocn get route order-service -o jsonpath='{.spec.host}')"
step "Polling https://$host/healthz"
for _ in $(seq 1 60); do
    if curl -sf --cacert "$INGRESS_CA" "https://$host/healthz" | grep -q '"status": *"\(ok\|UP\)"'; then
        ok "order-service is healthy through the Route"
        exit 0
    fi
    sleep 2
done
ocn get pods -o wide >&2
fail "order-service did not answer /healthz through https://$host"
