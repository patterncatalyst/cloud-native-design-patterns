#!/usr/bin/env bash
# Deploy Example 05 for one language into the cndp-05 namespace.
#
# Order: Strimzi operator (Helm, once), namespace, infrastructure (Kafka, Postgres,
# LGTM) and wait for it, then the language overlay. The images must already be
# loaded: k8s/build-images.sh <lang>.
#
#   k8s/deploy.sh go
set -euo pipefail
# shellcheck source=lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -eq 1 ]] || fail "usage: deploy.sh <lang> (${LANGS[*]})"
lang="$1"
valid_lang "$lang" || fail "unknown language '$lang' (${LANGS[*]})"
require_profile_running

log "Strimzi operator $STRIMZI_VERSION in namespace $STRIMZI_NAMESPACE"
hm upgrade --install strimzi "$STRIMZI_CHART" \
    --version "$STRIMZI_VERSION" \
    --namespace "$STRIMZI_NAMESPACE" --create-namespace \
    --set watchAnyNamespace=true \
    --wait --timeout 5m

log "namespace $NAMESPACE and infrastructure"
kc apply -f "$K8S_DIR/namespace.yaml"
render "$K8S_DIR/infra" | kc apply -f -

log "waiting for Kafka (up to 600 s)"
kcn wait kafka/cndp --for=condition=Ready --timeout=600s
log "waiting for Postgres and LGTM"
kcn rollout status statefulset/cndp-postgres --timeout=300s
kcn rollout status deployment/lgtm --timeout=300s

log "overlay $lang"
render "$K8S_DIR/overlays/$lang" | kc apply -f -
for d in shipping-consumer notification-consumer order-service; do
    kcn rollout status "deployment/$d" --timeout=420s
done

log "polling http://127.0.0.1:30080/healthz"
for _ in $(seq 1 60); do
    if curl -sf http://127.0.0.1:30080/healthz | grep -q '"status":"ok"'; then
        log "order-service is healthy on 127.0.0.1:30080"
        exit 0
    fi
    sleep 2
done
kcn get pods -o wide >&2
fail "order-service did not answer /healthz on 127.0.0.1:30080"
