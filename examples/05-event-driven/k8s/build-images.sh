#!/usr/bin/env bash
# Build the Example 05 images with docker (host BuildKit caches apply) and load
# them into the minikube node's containerd. Names: localhost/cndp-05/<lang>-<svc>:v1.
#
#   k8s/build-images.sh go            # one language
#   k8s/build-images.sh go python     # several
set -euo pipefail
# shellcheck source=lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || fail "usage: build-images.sh <lang>... (${LANGS[*]})"
require_profile_running

SERVICES=(order-service shipping-consumer notification-consumer)

# build_args <lang> <svc> prints "<context> <containerfile>" relative to the example directory.
# .NET builds from one context with a Containerfile per service; the others have a
# directory per service.
build_args() {
    local lang="$1" svc="$2" short
    if [[ "$lang" == dotnet ]]; then
        short="${svc%%-*}"
        echo "dotnet Containerfile.${short}"
    else
        echo "${lang}/${svc} Containerfile"
    fi
}

for lang in "$@"; do
    valid_lang "$lang" || fail "unknown language '$lang' (${LANGS[*]})"
    for svc in "${SERVICES[@]}"; do
        read -r ctx cf <<<"$(build_args "$lang" "$svc")"
        image="localhost/cndp-05/${lang}-${svc}:${IMAGE_TAG}"
        log "build $image"
        docker build -t "$image" -f "$EXAMPLE_DIR/$ctx/$cf" "$EXAMPLE_DIR/$ctx"
        log "load $image into $PROFILE"
        minikube -p "$PROFILE" image load --overwrite=true "$image"
    done
done
log "images in the node:"
minikube -p "$PROFILE" image ls --format table | grep -E "cndp-05" || true
