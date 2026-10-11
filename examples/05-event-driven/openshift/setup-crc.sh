#!/usr/bin/env bash
# Start OpenShift Local for Example 05 and prepare it: the ingress CA for curl and skopeo, and the
# internal registry's default route (enabled only if it is off).
#
#   openshift/setup-crc.sh
#
# Preconditions it enforces: no minikube profile running, no containers running, CRC sized at
# least 12 vCPU and 32768 MiB (it never runs `crc config set`; change the size yourself while CRC
# is stopped). `crc start` can change kubectl's current-context; this script records the value
# first and restores it on exit, including "no current-context".
#
# crc start prints the kubeadmin and developer passwords. Its stdout is discarded and its stderr is
# filtered, so neither reaches a terminal, log or file. The pull secret is read by crc from the path
# in `crc config get pull-secret-file`; this script never opens it.
set -euo pipefail
# shellcheck source=lib.sh
# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tools
require_alone

step "Sizing"
cpus="$(crc config get cpus 2>/dev/null | awk '{print $NF}')"
memory="$(crc config get memory 2>/dev/null | awk '{print $NF}')"
[[ "$cpus" =~ ^[0-9]+$ && "$memory" =~ ^[0-9]+$ ]] || fail "cannot read crc cpus and memory (crc config get cpus)"
(( cpus >= 12 && memory >= 32768 )) \
    || fail "CRC is sized $cpus vCPU / $memory MiB; Example 05 needs 12 / 32768. While CRC is stopped: crc config set cpus 12; crc config set memory 32768"
ok "$cpus vCPU, $memory MiB"

step "Current-context"
had_context=0
prior_context="$(current_context)"
[[ -z "$prior_context" ]] || had_context=1
restore_context() {
    local now
    if (( had_context )); then
        oc config set current-context "$prior_context" >/dev/null 2>&1 || true
    else
        oc config unset current-context >/dev/null 2>&1 || true
    fi
    now="$(current_context)"
    if [[ "$now" != "$prior_context" ]]; then
        printf 'ERROR: current-context changed from "%s" to "%s" and could not be restored\n' "$prior_context" "$now" >&2
        return 1
    fi
}
trap restore_context EXIT
if (( had_context )); then ok "recorded: $prior_context"; else ok "recorded: none set"; fi

step "OpenShift Local"
if crc_vm_running; then
    ok "already running"
else
    status_text="$(crc status 2>&1 || true)"
    grep -q -i -E 'does not exist|crc setup' <<<"$status_text" && fail "CRC is not set up. Run crc setup, then re-run this script"
    echo "    crc start (this takes several minutes; credentials are not printed)"
    # stdout carries the credentials banner; stderr carries progress. Drop any line that names a secret.
    crc start 2> >(grep -v -i -E 'password|kubeadmin|developer|token|secret' >&2) >/dev/null \
        || fail "crc start failed. Run crc status; re-run crc start yourself to see its output"
    ok "started"
fi
wait_for 300 "API reachable through $OCP_CONTEXT" ocx get nodes
require_crc
wait_for 600 "node Ready" bash -c "oc --context '$OCP_CONTEXT' get nodes --no-headers | grep -q ' Ready'"
ok "server: $(ocx version -o json 2>/dev/null | jq -r '"Kubernetes " + .serverVersion.gitVersion' 2>/dev/null || echo unknown)"

step "Ingress CA"
mkdir -p "$STATE" "$REGISTRY_CA_DIR"
# The CA is public; the directories are owned by the current user.
ocx get configmap default-ingress-cert -n openshift-config-managed -o jsonpath='{.data.ca-bundle\.crt}' >"$INGRESS_CA" \
    || fail "cannot read the ingress CA (configmap default-ingress-cert)"
grep -q 'BEGIN CERTIFICATE' "$INGRESS_CA" || fail "$INGRESS_CA holds no certificate"
cp "$INGRESS_CA" "$REGISTRY_CA_DIR/ca.crt"
ok "$INGRESS_CA"

step "Internal registry route"
default_route="$(ocx get configs.imageregistry.operator.openshift.io/cluster -o jsonpath='{.spec.defaultRoute}')"
if [[ "$default_route" == true ]]; then
    ok "default route already enabled (left as found)"
else
    ocx patch configs.imageregistry.operator.openshift.io/cluster --type merge -p '{"spec":{"defaultRoute":true}}' >/dev/null
    ocx annotate configs.imageregistry.operator.openshift.io/cluster "$ROUTE_ANNOTATION=true" --overwrite >/dev/null
    ok "default route enabled (annotated so teardown reverts it)"
fi
wait_for 300 "registry route exists" bash -c "[[ -n \"\$(oc --context '$OCP_CONTEXT' get route default-route -n openshift-image-registry -o jsonpath='{.spec.host}' 2>/dev/null)\" ]]"
ok "registry: $(registry_route)"
wait_for 1200 "cluster operators settled" cluster_settled

step "Inventory"
inventory
echo
echo "next: openshift/verify-matrix.sh [lang...]   or   openshift/deploy.sh <lang>"
