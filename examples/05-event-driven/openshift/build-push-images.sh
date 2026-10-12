#!/usr/bin/env bash
# Build the Example 05 images with docker (host BuildKit caches apply) and push them to the
# OpenShift internal registry through its default route. Names in the registry:
# <registry>/cndp-05/<lang>-<svc>:v1, which the overlays pull as
# image-registry.openshift-image-registry.svc:5000/cndp-05/<lang>-<svc>:v1.
#
#   openshift/build-push-images.sh go            # one language
#   openshift/build-push-images.sh go python     # several
#
# Why skopeo and not `docker push`: pushing to the default route needs the ingress CA trusted by
# the docker daemon (a root-owned /etc/docker/certs.d entry) or an insecure-registries setting, both
# permanent host changes. skopeo takes the CA from a user-owned directory instead.
set -euo pipefail
# shellcheck source=lib.sh
# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || fail "usage: build-push-images.sh <lang>... (${LANGS[*]})"
for lang in "$@"; do valid_lang "$lang" || fail "unknown language '$lang' (${LANGS[*]})"; done
require_crc
[[ -s "$INGRESS_CA" && -d "$REGISTRY_CA_DIR" ]] || fail "ingress CA missing in $STATE. Run openshift/setup-crc.sh first"
REGISTRY_ROUTE="$(registry_route)"
[[ -n "$REGISTRY_ROUTE" ]] || fail "the internal registry has no default route. Run openshift/setup-crc.sh first"

wait_for 1800 "cluster operators settled" cluster_settled

step "Namespace $NAMESPACE and the builder service account"
apply_retry -f "$K8S_DIR/namespace.yaml"
wait_for 120 "service account builder exists" ocn get serviceaccount builder

# push_image <lang> <svc> pushes one local image. The registry token is used once and never stored.
#
# Credentials, by design (S10 plan, decision 2): the short-lived token of the builder service
# account is held in a shell variable only. skopeo reads its credentials from an authfile, and
# the authfile here is a process substitution (a pipe), so no file with the token ever exists.
# printf is a bash builtin, so the token is not in any process's argument list either, which is
# what `--dest-creds` or `--dest-registry-token` would expose to `ps` and /proc/*/cmdline.
# `skopeo login` is not used because it writes an authfile to disk.
push_image() {
    local lang="$1" svc="$2" token
    token="$(oc --context "$OCP_CONTEXT" create token builder -n "$NAMESPACE" --duration=10m)" \
        || fail "cannot create a token for the builder service account"
    skopeo copy \
        --dest-cert-dir "$REGISTRY_CA_DIR" \
        --dest-authfile <(printf '{"auths":{"%s":{"auth":"%s"}}}' "$REGISTRY_ROUTE" "$(printf 'builder:%s' "$token" | base64 -w0)") \
        "docker-daemon:$(image_ref "$lang" "$svc")" \
        "docker://$REGISTRY_ROUTE/$NAMESPACE/${lang}-${svc}:${IMAGE_TAG}" >/dev/null \
        || { unset token; fail "push failed for ${lang}-${svc}"; }
    unset token
}

for lang in "$@"; do
    for svc in "${SERVICES[@]}"; do
        step "build $(image_ref "$lang" "$svc")"
        build_image "$lang" "$svc"
    done
    for svc in "${SERVICES[@]}"; do
        step "push ${lang}-${svc}:${IMAGE_TAG} to $REGISTRY_ROUTE/$NAMESPACE"
        push_image "$lang" "$svc"
    done
done

step "ImageStreams"
ocn get imagestream -o custom-columns=NAME:.metadata.name,TAGS:.status.tags[*].tag --no-headers
