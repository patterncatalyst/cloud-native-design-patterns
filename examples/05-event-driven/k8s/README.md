# Example 05 on minikube

The same three services and the same `verify.sh`, on a single-node Kubernetes cluster:
minikube with the Docker driver and containerd, Kubernetes v1.36.5. Appendix R in the
site walks through the design; this page is the command reference.

## Layout

| Path | Purpose |
|------|---------|
| `namespace.yaml` | Namespace `cndp-05` |
| `infra/` | Kafka (Strimzi `Kafka` and `KafkaNodePool`), Postgres 18 StatefulSet, Grafana LGTM, the Secret `cndp-postgres-app` and the schema ConfigMap |
| `base/` | The three Deployments and the order-service NodePort Service |
| `overlays/<lang>/` | Image names and the environment variables that language reads |
| `setup-profile.sh` | Create or start the `cndp-k8s` profile with the NodePorts published on 127.0.0.1 |
| `build-images.sh` | `docker build` each image, then `minikube image load` it |
| `deploy.sh` | Strimzi operator, infrastructure, one language overlay |
| `verify-matrix.sh` | Build, deploy, verify and tear down each language in turn |
| `teardown.sh` | Remove the namespace, and with `--operator` the Strimzi release, CRDs and namespace |

## Prerequisites

Docker Engine with the `default` context, minikube v1.39.0, kubectl v1.36.5 and Helm 4
(see [Prerequisites](../../PREREQUISITES.md)). The profile needs 8 GB of RAM, 4 CPUs and 40 GB of
disk. Run one workshop at a time: the scripts refuse to start while another minikube profile or
any other container is running, and they never stop them for you.

## Run it

```bash
cd examples/05-event-driven
k8s/setup-profile.sh                 # create the profile cndp-k8s
k8s/build-images.sh go               # build and load the Go images
k8s/deploy.sh go                     # Strimzi, infrastructure, Go overlay
RUNTIME=kubernetes BASE=http://127.0.0.1:30080 ./verify.sh
k8s/teardown.sh                      # remove the cndp-05 namespace
```

For all six languages in sequence: `OUT=/tmp/cndp-k8s-matrix k8s/verify-matrix.sh`.

The scripts always name the profile (`--context cndp-k8s`, `--kube-context cndp-k8s`) and start
minikube with `--keep-context`, so kubectl's current-context is never changed. Use the same
flags in your own commands.

## Reach it from the host

Two NodePorts are published on 127.0.0.1 when the profile is created. There is no port-forward,
tunnel or `minikube service`.

| Port | Service |
|------|---------|
| 127.0.0.1:30080 | order-service |
| 127.0.0.1:30300 | Grafana (anonymous admin, as in compose) |

Published ports are fixed at creation. Changing them means recreating the profile.

## Clean up

```bash
k8s/teardown.sh --operator     # namespace, Strimzi release, CRDs, strimzi namespace
minikube stop -p cndp-k8s      # free the memory; the profile stays
minikube delete -p cndp-k8s    # optional: remove the profile
```

## Render without a cluster

`infra/` reads the schema from `../db/init`, outside its directory, so it needs the load
restrictor lifted:

```bash
kubectl kustomize --load-restrictor LoadRestrictionsNone k8s/infra
kubectl kustomize k8s/overlays/go
```

CI renders `infra/` and every overlay and checks them with kubeconform against the Kubernetes
1.36.5 schemas.
