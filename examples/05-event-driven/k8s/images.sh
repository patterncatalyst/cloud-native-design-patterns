#!/usr/bin/env bash
# The Example 05 image table, shared by k8s/build-images.sh (minikube) and
# openshift/build-push-images.sh (OpenShift Local). Source it; do not run it.
# Needs EXAMPLE_DIR (the 05-event-driven directory) and IMAGE_TAG from the caller.
#
# 6 languages x 3 services = 18 images, all built with docker so the host BuildKit caches apply.
# Names: localhost/cndp-05/<lang>-<svc>:<tag>.

# shellcheck disable=SC2034  # SERVICES is used by the scripts that source this file
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

# image_ref <lang> <svc> prints the local image name.
image_ref() { echo "localhost/cndp-05/${1}-${2}:${IMAGE_TAG}"; }

# build_image <lang> <svc> builds one image from its Containerfile.
build_image() {
    local lang="$1" svc="$2" ctx cf
    read -r ctx cf <<<"$(build_args "$lang" "$svc")"
    docker build -t "$(image_ref "$lang" "$svc")" -f "$EXAMPLE_DIR/$ctx/$cf" "$EXAMPLE_DIR/$ctx"
}
