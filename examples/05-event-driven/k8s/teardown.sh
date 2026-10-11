#!/usr/bin/env bash
# Remove Example 05 from the cluster. The profile itself is never deleted.
#
#   k8s/teardown.sh              # delete the cndp-05 namespace (Kafka, Postgres, LGTM, apps, volumes)
#   k8s/teardown.sh --operator   # also remove the Strimzi release, its CRDs and namespace
set -euo pipefail
# shellcheck source=lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

operator=0
case "${1:-}" in
    "") ;;
    --operator) operator=1 ;;
    *) fail "usage: teardown.sh [--operator]" ;;
esac
minikube status -p "$PROFILE" >/dev/null 2>&1 || fail "profile $PROFILE is not running; nothing to tear down"

log "deleting namespace $NAMESPACE"
kc delete namespace "$NAMESPACE" --ignore-not-found --wait=true --timeout=300s

if (( operator )); then
    if hm status strimzi -n "$STRIMZI_NAMESPACE" >/dev/null 2>&1; then
        log "uninstalling the Strimzi release"
        hm uninstall strimzi -n "$STRIMZI_NAMESPACE" --wait
    fi
    log "deleting Strimzi CRDs and namespace $STRIMZI_NAMESPACE"
    kc get crd -o name | grep -E '\.strimzi\.io$' | xargs -r kubectl --context "$PROFILE" delete --wait=true
    kc delete namespace "$STRIMZI_NAMESPACE" --ignore-not-found --wait=true --timeout=300s
fi

log "cluster now:"
kc get namespaces
cat <<EOT

The profile $PROFILE is still present. To free its memory, then optionally remove it:
  minikube stop -p $PROFILE
  minikube delete -p $PROFILE
EOT
