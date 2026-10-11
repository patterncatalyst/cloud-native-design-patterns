# Example 05 on OpenShift Local

The same three services and the same `verify.sh`, on OpenShift Local (CRC) with Red Hat's
operator, Postgres and registry model. Appendix S in the site walks through the design; this
page is the command reference. It reuses the minikube manifests in `../k8s` through kustomize
and changes only what OpenShift needs.

## Layout

| Path | Purpose |
|------|---------|
| `operators/` | Namespace `cndp-amq-streams`, an AllNamespaces OperatorGroup and the AMQ Streams Subscription (pinned CSV, Manual approval) |
| `infra/` | Kafka and LGTM from `../k8s/infra` with patches, a Postgres StatefulSet on the Red Hat sclorg image, the Grafana Route |
| `components/openshift/` | Kustomize component: the `order-service` Route, ClusterIP Service, `imagePullPolicy: Always` |
| `overlays/<lang>/` | The `../k8s` overlay plus the component, with images from the internal registry (five languages, no C++) |
| `lib.sh` | Shared settings and helpers: the `crc-admin` context, `wait_for`, operator install, inventory, secret scrub |
| `setup-crc.sh` | Start CRC, record and restore the current-context, fetch the ingress CA, enable the registry route if it is off |
| `build-push-images.sh` | `docker build`, then `skopeo copy` to the internal registry with the `builder` token |
| `deploy.sh` | Operator, infrastructure, one language overlay, health poll through the Route |
| `verify-matrix.sh` | Build, push, deploy, verify, collect evidence for each language; project removed between languages |
| `teardown.sh` | Remove everything, revert the registry route, `crc stop` |

## Prerequisites

Docker Engine, `oc`, `crc` 2.64.0 and `skopeo` (see [Prerequisites](../../PREREQUISITES.md)). CRC must
be sized 12 vCPU and 32768 MiB with a pull secret configured; the scripts never change the size and
never open the pull secret. Run one workshop at a time: the scripts refuse to start while a
minikube profile or any container is running, and they never stop them for you.

## Run it

```bash
cd examples/05-event-driven
openshift/setup-crc.sh                  # crc start, ingress CA, registry route
openshift/build-push-images.sh go       # docker build, skopeo copy
openshift/deploy.sh go                  # operator, infrastructure, Go overlay
RUNTIME=kubernetes KUBECTL=oc KUBE_CONTEXT=crc-admin KUBE_NAMESPACE=cndp-05 \
  BASE=https://order-service-cndp-05.apps-crc.testing \
  CURL_OPTS="--cacert $HOME/.local/state/cndp-05-crc/ingress-ca.crt" ./verify.sh
openshift/teardown.sh                   # remove everything, then crc stop
```

All five languages in sequence: `OUT=/tmp/cndp-ocp-matrix openshift/verify-matrix.sh`.

Every command names the `crc-admin` context (`oc --context crc-admin`). Nothing runs
`oc config use-context`. `setup-crc.sh` records the kubeconfig's current-context before
`crc start` and restores it afterwards, including the case where none was set.

## Credentials

No password, token or pull secret is written to a file or passed as an argument.

- `crc start` output is discarded or filtered, so the kubeadmin password never reaches a terminal or log.
  To log in to the web console yourself, run `crc console --credentials`.
- The registry token comes from `oc create token builder --duration=10m` into a shell variable.
  `skopeo copy` reads it through a process-substitution authfile, so it is neither on disk nor in
  any argument list. `skopeo login` is not used because it writes a file.

## Reach it from the host

Routes on the cluster's wildcard domain, TLS verified against the ingress CA:

| URL | Service |
|-----|---------|
| `https://order-service-cndp-05.apps-crc.testing` | order-service |
| `https://lgtm-grafana-cndp-05.apps-crc.testing` | Grafana (anonymous admin, as in compose) |

Plain HTTP is redirected to HTTPS. There is no port-forward and no tunnel.

## Clean up

```bash
openshift/teardown.sh                    # all of it, then crc stop
openshift/teardown.sh --keep-running     # leave CRC running
openshift/teardown.sh --namespace-only   # only the cndp-05 project
```

Items that are not Example 05's are reported and never removed. CRC is stopped, never deleted.

## Render without a cluster

```bash
oc kustomize openshift/operators
oc kustomize --load-restrictor LoadRestrictionsNone openshift/infra
oc kustomize openshift/overlays/go
```
