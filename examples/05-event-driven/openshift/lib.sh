# shellcheck shell=bash
# Shared settings and helpers for the Example 05 OpenShift Local scripts. Source it; do not run it.
#
# Every oc call names the crc-admin context explicitly (ocx, ocn). Nothing runs
# `oc config use-context`: only setup-crc.sh touches the current-context, to restore
# the value it recorded before `crc start`. The kubeadmin password, tokens and the
# pull secret never appear in a file, a log or an argument list.

# shellcheck disable=SC2034  # variables are used by the scripts that source this file
OCP_CONTEXT="${OCP_CONTEXT:-crc-admin}"
NAMESPACE="${NAMESPACE:-cndp-05}"
OPERATOR_NAMESPACE="${OPERATOR_NAMESPACE:-cndp-amq-streams}"
IMAGE_TAG="v1"
LANGS=(spring-boot quarkus dotnet python go)
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/cndp-05-crc"
INGRESS_CA="$STATE/ingress-ca.crt"
REGISTRY_CA_DIR="$STATE/registry-ca"
ROUTE_ANNOTATION="cndp-05/enabled-default-route"

OPENSHIFT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_DIR="$(dirname "$OPENSHIFT_DIR")"
K8S_DIR="$EXAMPLE_DIR/k8s"

# The operator pin lives in one place, the Subscription manifest.
CSV="$(awk '$1 == "startingCSV:" {print $2}' "$OPENSHIFT_DIR/operators/subscription.yaml")"

# shellcheck source=../k8s/images.sh
# shellcheck source-path=SCRIPTDIR
source "$K8S_DIR/images.sh"

step() { printf '\n==> %s\n' "$*"; }
ok()   { printf '    ok: %s\n' "$*"; }
warn() { printf '    warning: %s\n' "$*" >&2; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

ocx() { oc --context "$OCP_CONTEXT" "$@"; }
ocn() { oc --context "$OCP_CONTEXT" -n "$NAMESPACE" "$@"; }

# Render a kustomization. infra reads ../../db/init and ../../k8s/infra, outside its directory.
render() { oc kustomize --load-restrictor LoadRestrictionsNone "$1"; }

valid_lang() {
    local l
    for l in "${LANGS[@]}"; do [[ "$l" == "$1" ]] && return 0; done
    return 1
}

# wait_for <seconds> <description> <command...>: poll every 5 s until the command succeeds.
wait_for() {
    local timeout="$1" what="$2" waited=0
    shift 2
    until "$@" >/dev/null 2>&1; do
        (( waited >= timeout )) && fail "timed out after ${timeout}s waiting for $what"
        sleep 5
        waited=$(( waited + 5 ))
    done
    ok "$what"
}

gone() { ! ocx get "$@" >/dev/null 2>&1; }
has_crd() { ocx get crd "$1" >/dev/null 2>&1; }

# Running minikube profiles, one per line (empty when minikube is absent or all are stopped).
running_minikube_profiles() {
    command -v minikube >/dev/null 2>&1 || return 0
    minikube profile list -o json 2>/dev/null \
        | jq -r '.valid[]? | select(.Status == "OK" or .Status == "Running") | .Name' 2>/dev/null || true
}

# One workshop at a time: no other cluster and no containers.
require_alone() {
    local running containers
    running="$(running_minikube_profiles)"
    [[ -z "$running" ]] || fail "minikube profile(s) running: $(tr '\n' ' ' <<<"$running"). Stop them first (minikube stop -p <profile>); run one cluster at a time"
    containers="$(docker ps --format '{{.Names}}' 2>/dev/null || true)"
    [[ -z "$containers" ]] || fail "containers are running (one workshop at a time): $(tr '\n' ' ' <<<"$containers")"
}

crc_running() { crc status 2>/dev/null | grep -q 'OpenShift:.*Running'; }
crc_vm_running() { crc status 2>/dev/null | grep -q 'CRC VM:.*Running'; }

# Every ClusterOperator Available, not Progressing, not Degraded. A configuration change such as
# enabling the registry's default route rolls the API servers, and crc status reports "Starting"
# until that finishes.
cluster_settled() {
    ocx get clusteroperators -o json 2>/dev/null | jq -e '[.items[].status.conditions
        | map({(.type): .status}) | add
        | select(.Available != "True" or .Progressing != "False" or .Degraded != "False")] | length == 0' >/dev/null
}

# wait_cluster_stable <timeout> <window>: cluster_settled must hold continuously for <window> seconds
# (checked every 10 s; any check that is not settled restarts the window). A start from a stopped
# cluster settles once, then the API servers roll again a few minutes later; one passing check is
# not enough. Fails only when <timeout> seconds pass without a full window.
wait_cluster_stable() {
    local timeout="$1" window="$2" elapsed=0 stable=0
    while (( elapsed < timeout )); do
        if cluster_settled; then
            stable=$(( stable + 10 ))
            if (( stable >= window )); then
                ok "cluster operators stable for ${window}s"
                return 0
            fi
        else
            stable=0
        fi
        sleep 10
        elapsed=$(( elapsed + 10 ))
    done
    fail "cluster operators did not stay settled for ${window}s within ${timeout}s"
}

# apply_retry <oc apply args...>: oc apply through the crc-admin context, up to 5 attempts. After a
# failure (for example ServiceUnavailable while an API server rolls) it waits for the cluster to
# settle and tries again. Reads manifests from stdin when called with -f -; stdin is buffered once.
apply_retry() {
    local attempt err input="" has_stdin=0
    if [[ " $* " == *" -f - "* ]]; then has_stdin=1; input="$(cat)"; fi
    for attempt in 1 2 3 4 5; do
        if (( has_stdin )); then
            err="$(ocx apply "$@" <<<"$input" 2>&1 >/dev/null)" && return 0
        else
            err="$(ocx apply "$@" 2>&1 >/dev/null)" && return 0
        fi
        warn "oc apply failed (attempt $attempt of 5); waiting for the cluster to settle"
        wait_for 900 "cluster operators settled" cluster_settled
    done
    fail "oc apply failed after 5 attempts: ${err}"
}

# require_tools: the host tools every script needs.
require_tools() {
    local t
    for t in oc crc jq skopeo docker curl base64; do
        command -v "$t" >/dev/null 2>&1 || fail "$t not found on PATH"
    done
}

# require_crc: CRC is running, the crc-admin context exists and points at OpenShift Local's API.
# Nothing is switched: the context is used by name on every call.
require_crc() {
    require_tools
    crc_vm_running || fail "OpenShift Local is not running. Run openshift/setup-crc.sh first"
    crc_running || wait_for 1200 "OpenShift settled (crc status Running)" crc_running
    oc config get-contexts "$OCP_CONTEXT" -o name >/dev/null 2>&1 \
        || fail "kubeconfig context $OCP_CONTEXT not found (crc start writes it)"
    local api
    api="$(ocx whoami --show-server 2>/dev/null)" || fail "cannot reach the OpenShift API through context $OCP_CONTEXT"
    [[ "$api" == *api.crc.testing* ]] || fail "context $OCP_CONTEXT points at $api, not OpenShift Local"
}

# The kubeconfig's current-context, empty when unset.
current_context() { oc config view -o jsonpath='{.current-context}' 2>/dev/null || true; }

# The default route of the internal registry, empty when not enabled.
registry_route() {
    ocx get route default-route -n openshift-image-registry -o jsonpath='{.spec.host}' 2>/dev/null || true
}

# Subscriptions, ClusterServiceVersions and non-system namespaces on the cluster: what is here
# before and after, so items that belong to someone else are reported and never touched.
inventory() {
    echo "  subscriptions:"
    ocx get subscriptions.operators.coreos.com -A --no-headers 2>/dev/null | awk '{print "    " $1 "/" $2}'
    echo "  csvs (excluding packageserver):"
    ocx get csv -A -l '!olm.copiedFrom' --no-headers 2>/dev/null | awk '$2 !~ /^packageserver/ {print "    " $1 "/" $2}'
    echo "  namespaces (excluding platform):"
    ocx get ns -o name 2>/dev/null | grep -v -E '^namespace/(openshift|kube-|default$|hostpath-provisioner$)' | sed 's/^namespace\//    /' || true
    return 0
}

# foreign_kafka_items: print one line per AMQ Streams or Strimzi item that is not ours: a Subscription
# or CSV outside the operator namespace (OLM-copied CSVs are excluded) and any Kafka custom resource
# outside the example namespace. Ours (cndp-amq-streams/amq-streams, Kafka cndp in cndp-05) is not listed.
foreign_kafka_items() {
    ocx get subscriptions.operators.coreos.com -A -o json 2>/dev/null | jq -r --arg ns "$OPERATOR_NAMESPACE" \
        '.items[] | select((.spec.name == "amq-streams" or .spec.name == "strimzi-kafka-operator") and .metadata.namespace != $ns) | "subscription \(.metadata.namespace)/\(.metadata.name)"'
    ocx get csv -A -l '!olm.copiedFrom' --no-headers 2>/dev/null | awk -v ns="$OPERATOR_NAMESPACE" '$2 ~ /^(amqstreams|strimzi-cluster-operator)/ && $1 != ns {print "csv " $1 "/" $2}'
    if has_crd kafkas.kafka.strimzi.io; then
        ocx get kafka -A --no-headers 2>/dev/null | awk -v ns="$NAMESPACE" '$1 != ns {print "kafka " $1 "/" $2}'
    fi
}

# Fail when AMQ Streams or Strimzi is already installed by someone else: an AllNamespaces
# operator would also manage their Kafka clusters.
refuse_foreign_kafka_operator() {
    local foreign
    foreign="$(foreign_kafka_items)"
    [[ -z "$foreign" ]] || fail "another Kafka operator or cluster is installed; this run would share it: $(tr '\n' ';' <<<"$foreign"). Run that project's teardown first"
}

# approve_install_plan <csv>: approve only the InstallPlan in the operator namespace that lists <csv>.
# Any other plan (an upgrade OLM proposes later) stays unapproved.
install_plan_for() {
    ocx get installplan -n "$OPERATOR_NAMESPACE" -o json 2>/dev/null | jq -r --arg c "$1" \
        '.items[] | select(.spec.clusterServiceVersionNames | index($c)) | .metadata.name' | head -1
}
csv_succeeded() {
    [[ "$(ocx get csv "$1" -n "$OPERATOR_NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null)" == Succeeded ]]
}
plan_proposed() { [[ -n "$(install_plan_for "$1")" ]]; }

# install_operator: apply operators/ (namespace, OperatorGroup, Subscription with Manual approval and
# startingCSV), approve the one InstallPlan for $CSV, wait for the CSV. Idempotent.
install_operator() {
    local plan
    if csv_succeeded "$CSV"; then ok "$CSV already Succeeded"; return 0; fi
    # redhat-operators reports READY before it serves packages, so wait for the package itself.
    wait_for 300 "OperatorHub serves amq-streams" ocx get packagemanifest amq-streams -n openshift-marketplace
    render "$OPENSHIFT_DIR/operators" | apply_retry -f -
    wait_for 300 "InstallPlan for $CSV proposed" plan_proposed "$CSV"
    plan="$(install_plan_for "$CSV")"
    ocx patch installplan "$plan" -n "$OPERATOR_NAMESPACE" --type merge -p '{"spec":{"approved":true}}' >/dev/null \
        || fail "approve InstallPlan $plan"
    wait_for 600 "$CSV Succeeded" csv_succeeded "$CSV"
}

# Fail when text on stdin or files under a directory look like secret material. Patterns: OpenShift
# tokens, bound service account tokens (JWTs), private keys and registry auth JSON.
SECRET_PATTERN='sha256~[A-Za-z0-9_-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.|BEGIN [A-Z ]*PRIVATE KEY|"auths"|kubeadmin-password'
scrub_dir() {
    local dir="$1"
    if grep -rlE "$SECRET_PATTERN" "$dir" >&2; then
        echo "secret-like material found in the files above" >&2
        return 1
    fi
    return 0
}
