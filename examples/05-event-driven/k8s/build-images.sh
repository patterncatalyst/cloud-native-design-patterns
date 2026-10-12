#!/usr/bin/env bash
# Build the Example 05 images with docker (host BuildKit caches apply) and load
# them into the minikube node's containerd. Names: localhost/cndp-05/<lang>-<svc>:v1.
#
#   k8s/build-images.sh go            # one language
#   k8s/build-images.sh go python     # several
set -euo pipefail
# shellcheck source=lib.sh
# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
# shellcheck source=images.sh
# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/images.sh"

[[ $# -ge 1 ]] || fail "usage: build-images.sh <lang>... (${LANGS[*]})"
require_profile_running

for lang in "$@"; do
    valid_lang "$lang" || fail "unknown language '$lang' (${LANGS[*]})"
    for svc in "${SERVICES[@]}"; do
        image="$(image_ref "$lang" "$svc")"
        log "build $image"
        build_image "$lang" "$svc"
        log "load $image into $PROFILE"
        minikube -p "$PROFILE" image load --overwrite=true "$image"
    done
done
log "images in the node:"
minikube -p "$PROFILE" image ls --format table | grep -E "cndp-05" || true
