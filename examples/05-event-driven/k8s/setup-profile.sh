#!/usr/bin/env bash
# Create or start the minikube profile for Example 05.
#
# Docker driver, containerd runtime, Kubernetes v1.36.5. The order-service and
# Grafana NodePorts are published on 127.0.0.1 when the profile is created, so
# the host reaches them without port-forward, tunnels or `minikube service`.
# Published ports are fixed at creation: changing them means recreating the profile.
#
# The script refuses to run while another minikube profile is Running or while
# containers other than this profile's node are running. It never stops anything
# and never deletes a profile. Every minikube start passes --keep-context, and the
# script also restores kubectl's prior current-context afterwards, because
# minikube's restart path overrides the flag (see the restore block below).
#
#   k8s/setup-profile.sh
set -euo pipefail
# shellcheck source=lib.sh
# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

MEMORY="${MINIKUBE_MEMORY:-8g}"
CPUS="${MINIKUBE_CPUS:-4}"
DISK="${MINIKUBE_DISK:-40g}"
K8S_VERSION="${KUBERNETES_VERSION:-v1.36.5}"
MINIKUBE_MIN="v1.39.0"
NODE_PORTS=(30080 30300)   # order-service, Grafana
PORTS_ARG=""
for p in "${NODE_PORTS[@]}"; do PORTS_ARG+="${PORTS_ARG:+,}127.0.0.1:${p}:${p}"; done

for tool in docker minikube kubectl helm python3 ss; do
    command -v "$tool" >/dev/null 2>&1 || fail "$tool is not in PATH (see the prerequisites page)"
done

# --- Docker Engine ---
ctx="$(docker context show 2>/dev/null || true)"
[[ "$ctx" == "default" ]] || fail "docker context is '${ctx:-unknown}', expected 'default'. Fix: docker context use default"
docker info >/dev/null 2>&1 || fail "cannot reach the Docker daemon. Fix: sudo systemctl enable --now docker"
log "Docker Engine reachable (context default)"

# --- minikube floor ---
mk_ver="$(minikube version --short 2>/dev/null || echo v0.0.0)"
[[ "$(printf '%s\n%s\n' "$MINIKUBE_MIN" "$mk_ver" | sort -V | head -1)" == "$MINIKUBE_MIN" ]] \
    || fail "minikube $mk_ver is older than $MINIKUBE_MIN"

# --- kernel limits ---
inotify="$(sysctl -n fs.inotify.max_user_instances 2>/dev/null || echo 0)"
if (( inotify < 256 )); then
    printf 'fs.inotify.max_user_instances is %d (need 256 or more). Fix:\n' "$inotify" >&2
    printf '  printf "fs.inotify.max_user_instances = 512\\nfs.inotify.max_user_watches = 524288\\n" | sudo tee /etc/sysctl.d/99-kubernetes.conf\n' >&2
    printf '  sudo sysctl -p /etc/sysctl.d/99-kubernetes.conf\n' >&2
    exit 1
fi

# --- one workshop at a time ---
others="$(other_running_profiles || true)"
if [[ -n "$others" ]]; then
    printf 'Other minikube profiles are running:\n' >&2
    while read -r n; do printf '  - %s\n' "$n" >&2; done <<<"$others"
    fail "stop them yourself (minikube stop -p <name>) and re-run; this script never stops another profile"
fi
foreign="$(docker ps --format '{{.Names}}' | grep -vx "$PROFILE" || true)"
if [[ -n "$foreign" ]]; then
    printf 'Containers are running:\n' >&2
    while read -r n; do printf '  - %s\n' "$n" >&2; done <<<"$foreign"
    fail "stop them yourself (for example docker compose down) and re-run"
fi

# Record kubectl's current-context (possibly empty) before any `minikube start`.
prev_context="$(kubectl config current-context 2>/dev/null || true)"
# set-context (not use-context) also restores a prior context whose entry no longer exists.
# With several KUBECONFIG files kubectl writes current-context into the first one; the
# merged value is what matters.
restore_context() {
    if [[ -n "$prev_context" ]]; then
        kubectl config set current-context "$prev_context" >/dev/null
    else
        kubectl config unset current-context >/dev/null
    fi
}
# Restore on every exit, including a failed start or Ctrl-C.
trap restore_context EXIT

profile_json="$(minikube profile list -o json 2>/dev/null || echo '{}')"
exists="$(python3 -c '
import json, sys
try:
    data = json.loads(sys.argv[2]) or {}
except Exception:
    data = {}
print("yes" if any(p.get("Name") == sys.argv[1] for p in (data.get("valid") or []) + (data.get("invalid") or [])) else "no")
' "$PROFILE" "$profile_json")"

running=no
if [[ "$exists" == "yes" ]] && minikube status -p "$PROFILE" >/dev/null 2>&1; then running=yes; fi

if [[ "$running" == "no" ]]; then
    for p in "${NODE_PORTS[@]}"; do
        if [[ -n "$(ss -ltnH "sport = :$p" 2>/dev/null)" ]]; then
            fail "host port $p is in use; free it and re-run"
        fi
    done
fi

if [[ "$exists" == "yes" ]]; then
    # An existing profile must match what this example needs; settings are fixed at creation.
    mismatch="$(python3 -c '
import json, sys
data = json.loads(sys.argv[2]) or {}
want = {"Driver": "docker", "ContainerRuntime": "containerd", "KubernetesVersion": sys.argv[3]}
for p in (data.get("valid") or []) + (data.get("invalid") or []):
    if p.get("Name") != sys.argv[1]:
        continue
    cfg = p.get("Config") or {}
    kcfg = cfg.get("KubernetesConfig") or {}
    have = {"Driver": cfg.get("Driver"), "ContainerRuntime": kcfg.get("ContainerRuntime"), "KubernetesVersion": kcfg.get("KubernetesVersion")}
    for k, v in want.items():
        if have[k] != v:
            print("%s is %s, expected %s" % (k, have[k] or "unknown", v))
' "$PROFILE" "$profile_json" "$K8S_VERSION")"
    [[ -z "$mismatch" ]] || fail "profile $PROFILE does not match this example: ${mismatch//$'\n'/; }. Settings are fixed at creation; recreate the profile."
    if [[ "$running" == "yes" ]]; then
        log "profile $PROFILE is already running"
    else
        log "starting profile $PROFILE (published ports persist)"
        minikube start -p "$PROFILE" --keep-context
    fi
else
    log "creating $PROFILE (Kubernetes $K8S_VERSION, $MEMORY RAM, $CPUS CPUs, $DISK disk, docker driver, containerd)"
    log "publishing NodePorts: $PORTS_ARG"
    minikube start -p "$PROFILE" \
        --driver=docker \
        --container-runtime=containerd \
        --kubernetes-version="$K8S_VERSION" \
        --memory="$MEMORY" --cpus="$CPUS" --disk-size="$DISK" \
        --ports="$PORTS_ARG" \
        --keep-context
fi

# The single sanctioned current-context restore. --keep-context is honoured when a
# profile is created, but when a stopped docker-driver profile restarts and its
# API-server host port changed, minikube v1.39.0 calls kubeconfig.UpdateEndpoint with
# KeepContext false and sets current-context to the profile anyway. Put back whatever
# was recorded before the start, then assert it.
restore_context
now_context="$(kubectl config current-context 2>/dev/null || true)"
[[ "$now_context" == "$prev_context" ]] \
    || fail "kubectl current-context is '${now_context:-unset}', expected '${prev_context:-unset}'"

# --- published ports must be loopback only ---
for p in "${NODE_PORTS[@]}"; do
    published="$(docker port "$PROFILE" "${p}/tcp" 2>/dev/null || true)"
    if ! grep -qF "127.0.0.1:${p}" <<<"$published" || grep -qF "0.0.0.0" <<<"$published"; then
        fail "profile $PROFILE does not publish $p on 127.0.0.1 only (docker port: ${published:-none}). Ports are fixed at creation; recreate the profile."
    fi
done
log "NodePorts ${NODE_PORTS[*]} are published on 127.0.0.1 only"

log "cluster health (context $PROFILE)"
kc wait --for=condition=Ready node --all --timeout=180s
kc get nodes
log "profile $PROFILE is ready; kubectl current-context is ${prev_context:-unset}, as before"
