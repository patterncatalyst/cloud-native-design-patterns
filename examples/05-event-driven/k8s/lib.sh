#!/usr/bin/env bash
# Shared settings and helpers for the Example 05 minikube scripts. Source it; do not run it.
#
# Every kubectl and helm call names the profile explicitly. Only setup-profile.sh
# touches kubectl's current-context, to restore the value it recorded before
# `minikube start`; nothing runs `minikube config set`.

# shellcheck disable=SC2034  # variables are used by the scripts that source this file
PROFILE="${PROFILE:-cndp-k8s}"
NAMESPACE="${NAMESPACE:-cndp-05}"
STRIMZI_NAMESPACE="${STRIMZI_NAMESPACE:-strimzi}"
STRIMZI_VERSION="${STRIMZI_VERSION:-1.2.0}"
STRIMZI_CHART="oci://quay.io/strimzi-helm/strimzi-kafka-operator"
IMAGE_TAG="v1"
LANGS=(spring-boot quarkus dotnet python cpp go)

K8S_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_DIR="$(dirname "$K8S_DIR")"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
log()  { printf '==> %s\n' "$*"; }

kc()   { kubectl --context "$PROFILE" "$@"; }
kcn()  { kubectl --context "$PROFILE" -n "$NAMESPACE" "$@"; }
hm()   { helm --kube-context "$PROFILE" "$@"; }

# Render a kustomization. infra/ reads the schema from ../../db/init, which is
# outside its directory, so the load restrictor is lifted for rendering.
render() { kubectl kustomize --load-restrictor LoadRestrictionsNone "$1"; }

valid_lang() {
    local l
    for l in "${LANGS[@]}"; do [[ "$l" == "$1" ]] && return 0; done
    return 1
}

# Every profile except $PROFILE that is Running, one per line.
other_running_profiles() {
    minikube profile list -o json 2>/dev/null | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin) or {}
except Exception:
    data = {}
for p in data.get("valid") or []:
    if p.get("Name") != sys.argv[1] and p.get("Status") == "Running":
        print(p["Name"])
' "$PROFILE"
}

require_profile_running() {
    minikube status -p "$PROFILE" >/dev/null 2>&1 \
        || fail "profile $PROFILE is not running. Run k8s/setup-profile.sh first."
}
