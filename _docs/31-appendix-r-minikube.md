---
title: "Running Example 05 on minikube"
marker: "R"
label: "Appendix R"
order: 31
part: "Deep-dive appendices"
description: "Example 05 on a single-node Kubernetes cluster: minikube with the Docker driver, Strimzi for Kafka, kustomize overlays for six languages, loopback NodePorts instead of tunnels, and the same verify.sh against compose and the cluster."
duration: 25 minutes
---

Every example in this book runs on `docker compose`. Compose proves the code; it does not prove the
deployment. A cluster adds questions compose never asks: where the configuration and the credential
live, how a service finds Kafka when the broker is a managed resource, what restarts a process that
exits, and how a request from the host reaches a pod. This appendix runs **Example 05**
(event-driven fan-out) on minikube, with the same three services in all six languages and the same
`verify.sh`, and records what changed.

The scope is one example on one node. It is not a production topology: there is one Kafka broker,
one Postgres instance and no service mesh. High availability, network policy and
autoscaling are outside it. What this appendix
fixes is the contract between an application and its platform: the Service names, the Secret, the
environment variables and the health endpoint. Appendix S reuses that contract on OpenShift Local.

## The runtime

minikube runs the Kubernetes control plane and the workload in one container on Docker Engine.
The profile is named `cndp-k8s`: the Docker driver creates a Docker network named after the
profile, and the compose stack already owns a network called `cndp`.

| Setting | Value | Reason |
|---------|-------|--------|
| Driver | `docker`, context `default` | Same engine as compose; no desktop application |
| Container runtime | `containerd` | The runtime Kubernetes distributions ship |
| Kubernetes | v1.36.5 | Matches the pinned kubectl, so client and server are the same version |
| Resources | 8 GB, 4 CPUs, 40 GB disk | Kafka, Postgres, LGTM and three services |
| Published ports | `127.0.0.1:30080`, `127.0.0.1:30300` | order-service and Grafana, loopback only |
| kubectl context | unchanged after setup | Every command passes `--context cndp-k8s`; `minikube start` runs with `--keep-context`, and `setup-profile.sh` also restores the prior context because minikube's restart path overrides the flag |

Host access uses NodePorts published when the profile is created. `kubectl port-forward`,
`minikube tunnel` and `minikube service` are not used: forwarded connections drop under load and on
idle, and a drop looks like a broken service. Because the ports are fixed at creation,
`setup-profile.sh` checks with `docker port` that both bind to `127.0.0.1` and not to all interfaces.

{% include excalidraw.html
   file="31-minikube-topology"
   alt="The host runs Docker Engine. Inside the node container cndp-k8s there are two namespaces: strimzi holds the Strimzi operator, and cndp-05 holds order-service, the shipping and notification consumers, a Kafka cluster, Postgres, the LGTM stack and the Postgres Secret. The host reaches order-service on 127.0.0.1:30080 and Grafana on 127.0.0.1:30300, and runs kubectl exec against the Kafka and Postgres pods."
   caption="Figure R.1: The node container holds two namespaces; the host reaches two loopback NodePorts and uses kubectl exec for the Kafka and Postgres checks" %}

## From compose to Kubernetes

Each compose element has a Kubernetes counterpart, and each counterpart changes something.

| Compose | Kubernetes | What changes |
|---------|------------|--------------|
| `kafka` (apache/kafka, `kafka:9094`) | Strimzi `Kafka` + `KafkaNodePool`, `cndp-kafka-bootstrap:9092` | An operator owns the broker; the plain listener is in-cluster only |
| `postgres` + init volume | StatefulSet `cndp-postgres`, ConfigMap `postgres-init`, Service `cndp-postgres-rw` | The schema file is the same one compose mounts |
| `apppass` in each service's environment | Secret `cndp-postgres-app`, read through `secretKeyRef` | One place for the demo credential |
| `lgtm` | Deployment `lgtm`, Services `lgtm` (OTLP) and `lgtm-grafana` (NodePort) | Same image, same OTLP endpoint `http://lgtm:4318` |
| `build:` | `docker build` + `minikube image load` | Images are built outside the cluster |
| `depends_on`, `healthcheck` | readiness and startup probes, `rollout status` | The platform retries; ordering is by waiting, not by dependency |
| `ports: 8080:8080` | NodePort 30080 | The host port moves into the NodePort range |
| `docker exec cndp-kafka ...` | `kubectl exec pod/cndp-dual-role-0 -c kafka -- ...` | `verify.sh` maps container names to pods |

Only the order-service has a `/healthz` endpoint, so it alone has startup and readiness probes
(a 150-second startup window for the JVM and .NET images). The consumers have no HTTP surface; the
cluster restarts them if they exit, and a consumer that cannot reach Kafka retries until the broker
is ready. All twelve consumers start from the earliest offset, so a restart after the topic exists
loses nothing.

## The manifests

The manifests live in `examples/05-event-driven/k8s/` and use kustomize, which is built into
`kubectl`:

```
k8s/
  namespace.yaml
  infra/          Kafka, Postgres, LGTM, the Secret and the schema ConfigMap
  base/           three Deployments, the order-service Service
  overlays/
    spring-boot/  quarkus/  dotnet/  python/  cpp/  go/
```

`base/` is language-neutral. Its Deployments set the image name to the service name, run with a
restricted security context (non-root, no privilege escalation, all capabilities dropped,
`RuntimeDefault` seccomp, no fixed user ID), read `PG_USER` and `PG_PASSWORD` from the Secret, and
point `OTEL_EXPORTER_OTLP_ENDPOINT` at the LGTM Service. Each overlay does two things: it maps the
service names to `localhost/cndp-05/<language>-<service>:v1`, and it appends the environment
variables that language reads. Kubernetes expands `$(PG_PASSWORD)` in a later variable only if
`PG_PASSWORD` is defined earlier in the list, which is why the credential variables sit in the base.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```yaml
# overlays/spring-boot — appended to each Deployment's environment
- name: SPRING_DATASOURCE_URL
  value: "jdbc:postgresql://cndp-postgres-rw:5432/appdb"
- name: SPRING_DATASOURCE_USERNAME
  value: "$(PG_USER)"
- name: SPRING_DATASOURCE_PASSWORD
  value: "$(PG_PASSWORD)"
- name: SPRING_KAFKA_BOOTSTRAP_SERVERS
  value: "cndp-kafka-bootstrap:9092"
```

```yaml
# overlays/quarkus
- name: QUARKUS_DATASOURCE_JDBC_URL
  value: "jdbc:postgresql://cndp-postgres-rw:5432/appdb"
- name: QUARKUS_DATASOURCE_USERNAME
  value: "$(PG_USER)"
- name: QUARKUS_DATASOURCE_PASSWORD
  value: "$(PG_PASSWORD)"
- name: KAFKA_BOOTSTRAP_SERVERS
  value: "cndp-kafka-bootstrap:9092"
```

```yaml
# overlays/dotnet
- name: DATABASE_URL
  value: "Host=cndp-postgres-rw;Port=5432;Database=appdb;Username=$(PG_USER);Password=$(PG_PASSWORD)"
- name: KAFKA_BOOTSTRAP
  value: "cndp-kafka-bootstrap:9092"
- name: SERVICE_VERSION
  value: "1.0.0"
```

```yaml
# overlays/python — memory limit 256Mi
- name: DATABASE_URL
  value: "postgres://$(PG_USER):$(PG_PASSWORD)@cndp-postgres-rw:5432/appdb"
- name: KAFKA_BOOTSTRAP
  value: "cndp-kafka-bootstrap:9092"
```

```yaml
# overlays/cpp — memory limit 256Mi
- name: PG_CONNINFO
  value: "postgresql://$(PG_USER):$(PG_PASSWORD)@cndp-postgres-rw:5432/appdb"
- name: KAFKA_BOOTSTRAP
  value: "cndp-kafka-bootstrap:9092"
```

```yaml
# overlays/go — memory limit 256Mi
- name: DATABASE_URL
  value: "postgres://$(PG_USER):$(PG_PASSWORD)@cndp-postgres-rw:5432/appdb"
- name: KAFKA_BOOTSTRAP
  value: "cndp-kafka-bootstrap:9092"
```

The variable names are the ones the compose files already use, so the application code is
untouched. The infrastructure directory reads the schema from `../db/init`, which sits outside its
own directory, and kustomize refuses that by default. The scripts render it with the load
restrictor lifted, which keeps one copy of the schema:

```bash
kubectl kustomize --load-restrictor LoadRestrictionsNone k8s/infra | kubectl --context cndp-k8s apply -f -
```

Kafka is a `Kafka` resource, not a Deployment. The Strimzi operator (Helm chart 1.2.0, in its own
namespace and watching all namespaces) turns a single-node KRaft `KafkaNodePool` and a `Kafka`
resource into a broker with a 2 GiB volume that is deleted with the namespace. The plain listener
on port 9092 is the one the applications use, so the Kafka version (4.3.1) and the listener port
are the only Kafka settings the services depend on.

## Getting the images in

The cluster does not build images. Each service is built on the host with `docker build`, which
keeps the host's BuildKit caches (a cold C++ build takes half an hour), then copied into the
node's containerd store with `minikube image load`. The Deployments set `imagePullPolicy: Never`,
so a missing image fails fast instead of attempting a pull from a registry that does not have it.
Tags are always `v1`; nothing uses `latest`.

{% include excalidraw.html
   file="31-minikube-image-flow"
   alt="A Containerfile feeds docker build, which uses the host BuildKit cache and produces an image named localhost/cndp-05/language-service:v1 in the Docker image store. minikube image load copies it into containerd in the node container under the same name, and the pod runs it with imagePullPolicy Never."
   caption="Figure R.2: Images are built on the host and loaded into the node; pods never pull them" %}

## Run it

From `examples/05-event-driven/`, with no other minikube profile or container running:

```bash
k8s/setup-profile.sh        # create the profile; checks the published ports
k8s/build-images.sh go      # build and load the three Go images
k8s/deploy.sh go            # Strimzi, then Kafka, Postgres, LGTM, then the Go overlay
RUNTIME=kubernetes BASE=http://127.0.0.1:30080 ./verify.sh
```

`verify.sh` is the file compose uses. Its container operations go through helper functions, and
`RUNTIME=kubernetes` swaps the implementations: `ctr_exec cndp-kafka ...` becomes
`kubectl exec pod/cndp-dual-role-0 -c kafka -- ...` and `ctr_exec cndp-postgres ...` becomes
`kubectl exec pod/cndp-postgres-0 -- ...`. The ten checks are unchanged.

A Go run records:

```
==> Verifying Example 05: Event-Driven Architecture

  ✓ order-service healthz
  ✓ POST /orders returns 201
  ✓ order visible in GET /orders
  → waiting for consumers to process events...
  ✓ order.placed topic exists in Kafka
  ✓ shipment created for order
  ✓ notification created for order
  ✓ shipping-group consumer group exists
  ✓ notification-group consumer group exists
  → testing idempotent consumers (re-sending duplicate event)...
  ✓ shipping remains idempotent (still 1 row after duplicate)
  ✓ notification remains idempotent (still 1 row after duplicate)

==> Results: 10 passed, 0 failed
==> PASS
```

To run all six languages in sequence, with a fresh namespace for each:

```bash
OUT=/tmp/cndp-k8s-matrix k8s/verify-matrix.sh
```

Recorded run on a Fedora 44 host (Docker Engine 29.8.2, minikube v1.39.0, Helm v4.3.0, host build
caches warm). Time covers the image build and load, the deploy, the checks and the namespace teardown.

| Language | Result | Time |
|----------|--------|------|
| Spring Boot | 10 passed, 0 failed | 180 s |
| Quarkus | 10 passed, 0 failed | 146 s |
| .NET | 10 passed, 0 failed | 141 s |
| Python | 10 passed, 0 failed | 124 s |
| C++ | 10 passed, 0 failed | 111 s |
| Go | 10 passed, 0 failed | 107 s |

Grafana answers on `http://127.0.0.1:30300` with anonymous access, as in compose. After each
language's `verify.sh`, `verify-matrix.sh` asks Tempo, through the `lgtm` pod, which services it
has received traces from (`/api/search/tag/service.name/values`) and keeps the reply as evidence.
All six languages reported all three services (`order-service`, `shipping-consumer` and
`notification-consumer`).

## Clean up

```bash
k8s/teardown.sh --operator    # the namespace, the Strimzi release, its CRDs and namespace
minikube stop -p cndp-k8s     # free the memory; the profile and its images stay
```

`teardown.sh` never deletes the profile. `minikube delete -p cndp-k8s` removes it, and the next
`setup-profile.sh` recreates it. Stop the profile before you start a compose stack or another
minikube profile: the scripts refuse to start while anything else is running.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `setup-profile.sh` refuses to start | Another minikube profile or a container is running | Stop it yourself; the script never stops anything |
| Host port 30080 or 30300 is in use | Another process holds it | Free it, then run the script again; ports are fixed at creation |
| `docker port` shows `0.0.0.0` | The profile was created without a loopback address | `minikube delete -p cndp-k8s`, then run `setup-profile.sh` again |
| Pod `ErrImageNeverPull` | The image was not loaded into this profile | `k8s/build-images.sh <lang>` |
| Kafka never becomes Ready | Operator not running or the node is out of memory | `kubectl --context cndp-k8s -n strimzi get pods`; check node memory |
| `kubectl` talks to the wrong cluster | Commands without `--context` | Pass `--context cndp-k8s`; the scripts do |
| order-service restarts during startup | The startup probe window is shorter than the JVM start on a loaded host | Raise `failureThreshold` on the startup probe in `base/` |

## Build, run, observe

```bash
cd examples/05-event-driven
k8s/setup-profile.sh                 # create the profile cndp-k8s
k8s/build-images.sh go               # build and load a language's images
k8s/deploy.sh go                     # Strimzi, infrastructure, the overlay
RUNTIME=kubernetes BASE=http://127.0.0.1:30080 ./verify.sh
k8s/teardown.sh                      # remove the cndp-05 namespace
```

With `RUNTIME=kubernetes`, `verify.sh` maps the container names it uses on compose to
`kubectl exec` against the Kafka and Postgres pods, and confirms the order-service health
endpoint, an order visible in `GET /orders`, the `order.placed` topic and both consumer
groups in Kafka, the shipment and notification side effects, and that redelivering the same
event stays idempotent.

Place an order through `127.0.0.1:30080`, then run
`kubectl --context cndp-k8s -n cndp-05 exec pod/cndp-postgres-0 -- psql -U appuser -d appdb -c "SELECT * FROM shipments"`
and confirm one row for the order. Scale the shipping consumer to zero replicas with
`kubectl --context cndp-k8s -n cndp-05 scale deployment/shipping-consumer --replicas=0`, place another order
and query again: the count is 0. Scale it back to one replica and the count becomes 1, because the
consumer group resumes from its last committed offset.

The manifests and scripts are in [`examples/05-event-driven/k8s/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/05-event-driven/k8s/).
