---
title: "Running Example 05 on OpenShift Local"
marker: "S"
label: "Appendix S"
order: 32
part: "Deep-dive appendices"
description: "Example 05 on OpenShift Local (CRC): AMQ Streams installed through OLM with a pinned, manually approved CSV, pods under the restricted-v2 SCC, a Red Hat Postgres image, edge-TLS Routes, images pushed to the internal registry without a token on disk, and the same verify.sh over HTTPS."
duration: 30 minutes
---

Appendix R ran Example 05 on minikube, where the platform accepts almost anything: root images,
host-built images loaded by name, a NodePort on loopback. OpenShift is stricter in four places, and
each one changes the deployment. Operators are installed through the Operator Lifecycle Manager
(OLM) from a catalog, not from a Helm chart. Pods run under a security context constraint (SCC)
that assigns an arbitrary non-root user ID. Traffic enters through a Route, not a NodePort. Images
come from a registry inside the cluster. This appendix runs the same three services and the same
`verify.sh` on **OpenShift Local** (CRC), and records what had to change and what did not.

The scope is the same as Appendix R: one example, one node, one Kafka broker, one Postgres
instance. What carries over is the contract between an application and its platform: the Service
names, the Secret, the environment variables and the health endpoint. The five language overlays
reuse the minikube overlays unchanged; the OpenShift directory adds only what the platform needs.
C++ is not part of this appendix: Appendix R covers it, and the other five languages are enough to
exercise every OpenShift-specific mechanism.

## The runtime

OpenShift Local runs a single-node OpenShift cluster in a virtual machine on the host, managed by
the `crc` command. The host needs KVM, and `crc setup` makes `api.crc.testing` and
`*.apps-crc.testing` resolve locally, which is what lets a Route work without a tunnel.

| Setting | Value | Reason |
|---------|-------|--------|
| OpenShift Local | crc 2.64.0, OpenShift 4.22.14, Kubernetes v1.35.6 | Newest release at the time of writing; the checksum is verified on install. `oc version` on the running cluster reported the OpenShift and Kubernetes versions |
| Resources | 12 vCPU, 32768 MiB, 80 GB disk | The cluster platform, Kafka, Postgres, LGTM and three services share one VM |
| Pull secret | a file path in `crc config`, never opened by the scripts | The secret stays in the file Red Hat issued |
| kubeconfig context | `crc-admin`, named on every call | No script runs `oc config use-context`, and no kubeadmin password is typed, stored or printed |
| Current-context | restored after `crc start` | `crc start` can change it; `setup-crc.sh` records it first, including the case where none is set, and restores it on exit |
| One cluster at a time | refuse if a minikube profile or a container is running | The VM and a minikube node compete for the same memory |

`crc start` prints the kubeadmin and developer passwords. `setup-crc.sh` discards its standard
output and filters its standard error, so neither reaches a terminal, a log or a file. If you want the
web console login, run `crc console --credentials` yourself.

## What changes from minikube

| Concern | minikube (Appendix R) | OpenShift Local | Why |
|---------|----------------------|-----------------|-----|
| Kafka operator | Strimzi 1.2.0 from a Helm chart | AMQ Streams 3.2 from OLM, pinned CSV, Manual approval | The supported Red Hat build of Strimzi, installed the OpenShift way |
| Kafka version | 4.3.1 | 4.2.0 (`metadataVersion: 4.2-IV1`) | The AMQ Streams 3.2 bundle ships broker images for Kafka 4.1 and 4.2 only |
| Postgres image | `docker.io/library/postgres:18.6-alpine`, root-capable | `registry.redhat.io/rhel10/postgresql-18`, arbitrary UID | The Red Hat image is built for an assigned user ID |
| Schema | mounted at `/docker-entrypoint-initdb.d` | a `postgresql-start` hook that runs the same SQL as appuser | The image has its own startup contract |
| Host access | NodePorts on loopback | edge-TLS Routes on `apps-crc.testing` | Routes are the platform's ingress |
| Images | `docker build`, then `minikube image load`, `pullPolicy: Never` | `docker build`, then `skopeo copy` to the internal registry, `pullPolicy: Always` | There is no node store to load into; a registry is the interface |
| Pod security | restricted-ready, not enforced | `restricted-v2` enforced, no fixed UID | The SCC assigns the user ID from the project's range |
| Grafana | NodePort 30300 | Route `lgtm-grafana` | Same reason as order-service |

{% include excalidraw.html
   file="32-openshift-topology"
   alt="The host runs curl and verify.sh, a browser and oc with the crc-admin context. Inside OpenShift Local there are two namespaces. cndp-amq-streams holds an OLM Subscription with Manual approval and a pinned CSV, and the AMQ Streams operator, which manages the Kafka cluster. cndp-05 holds order-service behind an edge-TLS Route, the shipping and notification consumers, Kafka 4.2.0, Postgres 18 from the sclorg image, the LGTM stack behind a Grafana Route and the Postgres Secret."
   caption="Figure S.1: The operator lives in its own namespace and manages Kafka in cndp-05; the host reaches order-service and Grafana through Routes and uses oc exec for the Kafka and Postgres checks" %}

## Installing an operator with OLM

On minikube the Strimzi operator is a Helm release. On OpenShift an operator is a **Subscription**
to a package in a catalog, and OLM does the install. The Subscription pins the exact version:

```yaml
spec:
  name: amq-streams
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  channel: amq-streams-3.2.x
  startingCSV: amqstreams.v3.2.1-14
  installPlanApproval: Manual
```

`startingCSV` names the ClusterServiceVersion (CSV) to install, and `installPlanApproval: Manual`
makes OLM propose an InstallPlan and wait. `deploy.sh` approves only the InstallPlan that lists the
pinned CSV, then waits for the CSV to reach `Succeeded`. A later InstallPlan, such as an upgrade OLM
proposes afterwards, stays unapproved, so the version moves only when someone edits the pin.

The operator has its own namespace, `cndp-amq-streams`, and its own OperatorGroup with an empty
`spec`, which means AllNamespaces. The operator therefore watches `cndp-05` without a second
OperatorGroup there. Teardown removes the Subscription, the CSV, its InstallPlans and the OperatorGroup,
then the two namespaces, the CRDs the CSV owns and OLM's `Operator` object for the package, and
reverts the registry route if setup enabled it. A cluster-wide operator also manages any Kafka
cluster it can see, so `deploy.sh` first takes an inventory and refuses to continue if it finds
another project's AMQ Streams or Strimzi Subscription or CSV, a Kafka resource outside `cndp-05`,
Strimzi CRDs that our Subscription did not install, or a Strimzi cluster-operator Deployment in
another namespace.

The catalog is the authority on what is newest, and it can only be read from a running cluster.
On the recorded run, `oc --context crc-admin get packagemanifest amq-streams -n openshift-marketplace` reported:

| Field | Value |
|-------|-------|
| Default channel | `stable` |
| Channel used | `amq-streams-3.2.x`, the newest minor channel |
| `currentCSV` of that channel | `amqstreams.v3.2.1-14`, the pinned `startingCSV` |
| CSV phase after install | `Succeeded` |
| Kafka version in the bundle | 4.2.0 (the Kafka resource's `.status.kafkaVersion` reports `4.2.0`) |

The default channel `stable` follows the newest release the catalog offers. The pin names the
minor channel instead, so a new minor release in `stable` does not change what this appendix installs.

## restricted-v2 and the images

The `restricted-v2` SCC is the default for ordinary workloads. It requires `runAsNonRoot`, forbids
privilege escalation, drops all capabilities, applies the runtime-default seccomp profile and
assigns the container a user ID from the project's range, with group 0. The minikube base already
sets that security context and never names a user ID, so the OpenShift overlays add no `runAsUser`,
`fsGroup` or SCC binding. Nothing in `openshift/` runs `oc adm policy`.

The images were already compatible. Each Containerfile ends in a numeric non-root `USER` and
copies files with `--chown=<uid>:0 --chmod=g=u`, so the arbitrary user ID, which is always in group 0,
can read and write what the image owns. Before the run, `skopeo inspect --config` on each of the
fifteen local images (five languages, three services) reported a numeric, non-zero user:

| Languages | `USER` in the image |
|-----------|---------------------|
| Spring Boot, Quarkus | 185 |
| .NET, Python, Go | 1001 |

On the cluster, the check is the `openshift.io/scc` annotation on each pod: the matrix fails a language
unless every application pod reports `restricted-v2`. On the recorded run every pod in `cndp-05`
reported it, for all five languages. The Go run, as one example:

| Pod | SCC |
|-----|-----|
| `cndp-dual-role-0` (Kafka) | `restricted-v2` |
| `cndp-postgres-0` | `restricted-v2` |
| `lgtm-6dcf64f6ff-62xv5` | `restricted-v2` |
| `order-service-8545b6f5b5-6jf2j` | `restricted-v2` |
| `shipping-consumer-78bc8fb84-dglkn` | `restricted-v2` |
| `notification-consumer-854cb78476-zmqdf` | `restricted-v2` |

### Postgres

`quay.io/sclorg/postgresql-18-c10s` is the upstream of Red Hat's `rhel10/postgresql-18`, and was
used to rehearse the manifests offline with Docker, as an arbitrary user ID in group 0 with the
hook, SQL and configuration mounted read-only exactly as the StatefulSet mounts them. The cluster
pulls the Red Hat image from `registry.redhat.io` with the cluster's pull secret.

The image reads `POSTGRESQL_USER`, `POSTGRESQL_PASSWORD` and `POSTGRESQL_DATABASE`, keeps its data in
`/var/lib/pgsql/data`, and sources shell files from fixed directories. Two properties shaped the
manifest:

- `POSTGRESQL_USER` is not a superuser. The schema therefore runs as appuser, which also makes
  appuser the owner of the tables. The extension `uuid-ossp` is a trusted extension, so the database
  owner may create it.
- Files in `postgresql-init/` run before the role and the database exist, so the schema hook is
  `postgresql-start/10-cndp-schema.sh`, which runs after them on every start. The SQL uses
  `IF NOT EXISTS`, so a restart changes nothing. The same SQL files the compose stack mounts are
  mounted from one ConfigMap, so the schema has a single source.

The offline rehearsal confirmed that the hook runs, that appuser owns `orders`, `shipments` and
`notifications`, that `uuid-ossp` loads, that `log_statement` is `all`, and that a restart is a
no-op. The image's default access rule for local connections is `trust`, so
`psql -U appuser -d appdb` inside the pod works without a password, which is how `verify.sh`
queries the database; connections over the network use a password.

### The observability image

`docker.io/grafana/otel-lgtm:0.36.0` is built to run as root. Rather than reach for an SCC
exception first, the image was run as an arbitrary user ID in group 0 with a read-only root
filesystem, to find out what it writes. Three paths:

| Path | Used by | Mount |
|------|---------|-------|
| `/data` | Loki, Tempo, Prometheus, Pyroscope and Grafana state | emptyDir |
| `/tmp` | the readiness marker | emptyDir |
| `/var/tempo` | Tempo's shutdown marker | emptyDir |

One more change: Grafana tries to replace its bundled data source plugins from grafana.com at start,
which needs a writable `/otel-lgtm` tree. On a read-only root it removes the bundled plugin and then
fails, which leaves the Loki, Tempo and Prometheus data sources unregistered. Setting
`GF_PLUGINS_PREINSTALL_DISABLED=true` skips that update, and the bundled plugins stay. With those
four changes Grafana's `/api/health` answers, all four data sources report healthy, and an OTLP trace
posted to port 4318 is readable from Tempo. On the cluster the `lgtm` pod ran under `restricted-v2`
with no exception, and Grafana 13.2.3 answered `/api/health` through its Route.

An SCC exception was not needed. If a future image version needs root, the fallback is a scoped
exception, never a cluster-wide one: a ServiceAccount `lgtm` in the project, a namespaced RoleBinding
to the ClusterRole `system:openshift:scc:anyuid`, and `runAsUser: 0` on that one container. It was
not exercised in this run.

## The manifests

```
openshift/
  operators/     namespace, OperatorGroup, Subscription
  infra/         Kafka and LGTM from ../k8s/infra with patches, Postgres, the Grafana Route
  components/openshift/   the order-service Route, ClusterIP Service, pullPolicy Always
  overlays/
    spring-boot/  quarkus/  dotnet/  python/  go/
```

Nothing is copied from `k8s/`. `infra/` lists `../../k8s/infra/kafka.yaml` and `lgtm.yaml` as
resources and patches them: the Kafka version and `metadataVersion` for the AMQ Streams bundle, the
`lgtm-grafana` Service from NodePort to ClusterIP, and the restricted-v2 security context and
emptyDir volumes for the observability pod. Each overlay is the minikube overlay of the same language
plus a **Component**, a reusable kustomize fragment that adds the Route and rewrites the Service and
the pull policy, plus an `images:` block that points the three images at the internal registry.
Because the Postgres manifest is the only one that differs by image, it is the only manifest of
its own. The minikube directory renders byte for byte as before.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|Go" %}

```yaml
# openshift/overlays/spring-boot/kustomization.yaml (images)
- name: localhost/cndp-05/spring-boot-order-service
  newName: image-registry.openshift-image-registry.svc:5000/cndp-05/spring-boot-order-service
  newTag: v1
# ...the same mapping for shipping-consumer and notification-consumer
```

```yaml
# openshift/overlays/quarkus/kustomization.yaml (images)
- name: localhost/cndp-05/quarkus-order-service
  newName: image-registry.openshift-image-registry.svc:5000/cndp-05/quarkus-order-service
  newTag: v1
# ...the same mapping for shipping-consumer and notification-consumer
```

```yaml
# openshift/overlays/dotnet/kustomization.yaml (images)
- name: localhost/cndp-05/dotnet-order-service
  newName: image-registry.openshift-image-registry.svc:5000/cndp-05/dotnet-order-service
  newTag: v1
# ...the same mapping for shipping-consumer and notification-consumer
```

```yaml
# openshift/overlays/python/kustomization.yaml (images)
- name: localhost/cndp-05/python-order-service
  newName: image-registry.openshift-image-registry.svc:5000/cndp-05/python-order-service
  newTag: v1
# ...the same mapping for shipping-consumer and notification-consumer
```

```yaml
# openshift/overlays/go/kustomization.yaml (images)
- name: localhost/cndp-05/go-order-service
  newName: image-registry.openshift-image-registry.svc:5000/cndp-05/go-order-service
  newTag: v1
# ...the same mapping for shipping-consumer and notification-consumer
```

The environment variables each language reads come from the minikube overlay and are not repeated
here. `infra/` also reads the schema from `../../db/init`, so it renders with the load restrictor
lifted, like the minikube infrastructure:

```bash
oc kustomize --load-restrictor LoadRestrictionsNone openshift/infra | oc --context crc-admin apply -f -
```

The pull policy is `Always` because the tag stays `v1` across runs: with `IfNotPresent`, a node
that cached an earlier push would keep running the old image.

## Getting the images in

The Docker builds are the ones from Appendix R, with the same names and the same host BuildKit
caches. The Containerfile table moved into `k8s/images.sh`, which both build scripts source, so
the eighteen rows exist once. The difference is the destination. `docker push` to the registry's
default route needs the ingress CA trusted by the Docker daemon, which means a root-owned
`/etc/docker/certs.d` entry or an `insecure-registries` setting: a permanent change to the host.
`skopeo copy` reads the image straight from the Docker daemon with `docker-daemon:` and takes the CA
from a directory the user owns.

{% include excalidraw.html
   file="32-openshift-image-flow"
   alt="A Containerfile feeds docker build, which uses the host BuildKit cache and produces an image named localhost/cndp-05/language-service:v1 in the Docker image store. skopeo copy reads it from the docker daemon and pushes it over HTTPS to the internal registry, where it becomes an ImageStream tag v1. The pod pulls it with imagePullPolicy Always. The credential is a ten-minute token for the builder service account, held in a shell variable and passed through a pipe."
   caption="Figure S.2: skopeo pushes from the Docker image store to the internal registry; the credential never touches a file or an argument list" %}

The registry needs a credential, and the design keeps it out of every place a secret leaks to:

```bash
token="$(oc --context crc-admin create token builder -n cndp-05 --duration=10m)"
skopeo copy --dest-cert-dir "$STATE/registry-ca" \
  --dest-authfile <(printf '{"auths":{"%s":{"auth":"%s"}}}' "$REGISTRY_ROUTE" \
      "$(printf 'builder:%s' "$token" | base64 -w0)") \
  "docker-daemon:localhost/cndp-05/go-order-service:v1" \
  "docker://$REGISTRY_ROUTE/cndp-05/go-order-service:v1"
unset token
```

The token is the short-lived token of the project's `builder` service account, held only in a shell
variable. `skopeo` reads its credentials from an authfile, and the authfile here is a process
substitution, a pipe, so no file contains the token. `printf` is a Bash builtin, so the token is in no
process's argument list either, which is what `--dest-creds` and `--dest-registry-token` would
expose to `ps` and `/proc/*/cmdline`. `skopeo login` is not used because it writes an authfile to disk.
The ImageStreams are created by the first push.

The registry's default route is off in a fresh cluster. `setup-crc.sh` enables it only if it is off
and annotates the registry configuration, so `teardown.sh` reverts exactly what the run changed and
leaves a route that was already there alone.

## Traces across Kafka

The check that matters for an event-driven example is not that each service exports spans, but that
one trace crosses the topic. Spring Boot (through the OpenTelemetry agent), Quarkus, Python and
Go propagate the W3C trace context in the Kafka record headers. The .NET services did not:
`Confluent.Kafka` has no built-in tracing, so the order-service's span and the consumers' spans were
three unrelated traces. This appendix fixes that in the code, not in the check.

The order-service starts a producer span and injects the context into the record headers:

```csharp
Activity? publish = null;
try
{
    publish = orderSource.StartActivity("order.placed publish", ActivityKind.Producer);
    var message = new Message<Null, string> { Value = json, Headers = new Headers() };
    Propagators.DefaultTextMapPropagator.Inject(
        new PropagationContext(publish?.Context ?? Activity.Current?.Context ?? default, Baggage.Current),
        message.Headers,
        (headers, key, value) => headers.Add(key, Encoding.UTF8.GetBytes(value)));
    await producer.ProduceAsync("order.placed", message);
}
catch (Exception ex)
{
    publish?.SetStatus(ActivityStatusCode.Error, ex.Message);
}
finally
{
    publish?.Dispose();
}
```

Each consumer extracts it and starts its span as a child:

```csharp
var parent = Propagators.DefaultTextMapPropagator.Extract(
    default,
    cr.Message.Headers,
    (headers, key) => headers is null
        ? Array.Empty<string>()
        : headers.Where(h => h.Key == key)
                 .Select(h => h.GetValueBytes())
                 .Where(b => b is not null)
                 .Select(b => Encoding.UTF8.GetString(b!)));
using var span = source.StartActivity("process_shipment", ActivityKind.Consumer, parent.ActivityContext);
```

The service names stay `order-service`, `shipping-consumer` and `notification-consumer`. On compose,
the .NET example passes `verify.sh` 10 of 10 and Tempo holds a trace that contains all three
services.

On OpenShift, `verify-matrix.sh` keeps the evidence. After each language's `verify.sh` it asks Tempo,
through the `lgtm` pod, for traces whose `service.name` is `order-service`, reads each one and
keeps the first that also contains a consumer service in `linked-trace.json`. Tempo indexes with a
delay, so the query retries for up to three minutes.

On the recorded run, every language produced a trace that Tempo returned with all three services.
`linked-trace.json` for the Go run:

```json
{
  "traceId": "880f0a8a4840bccad3e06572ffd601a5",
  "services": [
    "notification-consumer",
    "order-service",
    "shipping-consumer"
  ]
}
```

The other four languages recorded the same three services, each under its own trace ID.

## Run it

Stop minikube and any compose stack first, then, from `examples/05-event-driven/`:

```bash
openshift/setup-crc.sh                  # crc start, ingress CA, registry route
openshift/build-push-images.sh go       # docker build, then skopeo copy
openshift/deploy.sh go                  # operator, infrastructure, Go overlay
RUNTIME=kubernetes KUBECTL=oc KUBE_CONTEXT=crc-admin KUBE_NAMESPACE=cndp-05 \
  BASE=https://order-service-cndp-05.apps-crc.testing \
  CURL_OPTS="--cacert $HOME/.local/state/cndp-05-crc/ingress-ca.crt" ./verify.sh
```

`verify.sh` is unchanged. `KUBECTL=oc` and `KUBE_CONTEXT=crc-admin` select the cluster, and the
Route's certificate is verified against the cluster's ingress CA, which `setup-crc.sh` reads from
the `default-ingress-cert` ConfigMap. Nothing in the OpenShift directory uses `curl -k`. Plain HTTP
on the Route answers with a redirect to HTTPS.

Recorded output for Go on OpenShift Local (the other four languages print the same ten checks and
the same result line):

```
==> Polling https://order-service-cndp-05.apps-crc.testing/healthz
    ok: order-service is healthy through the Route
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

To run all five languages in sequence, with a fresh project for each:

```bash
OUT=/tmp/cndp-ocp-matrix openshift/verify-matrix.sh
```

Each language must pass `verify.sh`, show a linked trace, and have every application pod under
`restricted-v2`. Between languages only the `cndp-05` project is removed; the operator stays, so
the second language skips the install.

Recorded results, 2026-10-13:

| Language | Result | Trace | SCC | Time |
|----------|--------|-------|-----|------|
| Spring Boot | 10 passed, 0 failed | linked | restricted-v2 | 169 s |
| Quarkus | 10 passed, 0 failed | linked | restricted-v2 | 119 s |
| .NET | 10 passed, 0 failed | linked | restricted-v2 | 121 s |
| Python | 10 passed, 0 failed | linked | restricted-v2 | 118 s |
| Go | 10 passed, 0 failed | linked | restricted-v2 | 115 s |

Plain HTTP on the order-service Route answered `302` with a `Location` of the HTTPS URL, and
Grafana's `/api/health` through its Route returned `"database": "ok"` with version 13.2.3.

## Clean up

```bash
openshift/teardown.sh                    # remove everything, then crc stop
openshift/teardown.sh --namespace-only   # only the cndp-05 project
```

Order matters because OLM-managed resources have finalizers that need their operator. The script
deletes KafkaTopics and KafkaUsers, then the Kafka and KafkaNodePool resources while the operator
still runs, then the project. It then removes the Subscription, the CSV, its InstallPlans, the
OperatorGroup, the CRDs the CSV owns (read from the CSV's `.spec.customresourcedefinitions.owned`)
and the operator namespace. OLM labels each CRD it installs for this Subscription with
`operators.coreos.com/amq-streams.cndp-amq-streams`, and the script also removes CRDs that carry that
label, so a CRD kept by an earlier run is still found after the CSV is gone. The CRDs go only when
something of ours exists, and only after a foreign check: another project's Subscription, CSV or
Kafka custom resource keeps them in place, the script prints what it kept and why, and carries on.
No other `*.strimzi.io` CRD is ever removed. It
reverts the registry route only if `setup-crc.sh` enabled it. A step that fails or times out is
reported and the script continues, so the route is reverted and CRC is stopped anyway; the exit code
is non-zero if a step failed or something of Example 05's is left. A leftover check lists those
items, and lists items that are not Example 05's as left untouched. The last step is
`crc stop`: CRC is stopped, never deleted, so the next start is quick. A second run finds nothing to do
and exits 0.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `setup-crc.sh` refuses to start | A minikube profile or a container is running | Stop it yourself; the script never stops anything |
| CRC is sized too small | The VM is below 12 vCPU or 32768 MiB | While CRC is stopped: `crc config set cpus 12`, `crc config set memory 32768` |
| `deploy.sh` stops at "another Kafka operator" | A different AMQ Streams or Strimzi installation is present | Run that project's teardown; this one would otherwise manage its clusters |
| InstallPlan never appears | `redhat-operators` reports ready before it serves packages | `deploy.sh` waits for the package; check `oc --context crc-admin get packagemanifest amq-streams -n openshift-marketplace` |
| `oc` calls fail with connection refused, timeouts or `ServiceUnavailable` for a few minutes after `crc start` or after `setup-crc.sh` enables the registry route | The API servers roll out again after the first settled check, and `crc status` reports Starting meanwhile | `setup-crc.sh` waits until the cluster operators stay settled for 300 s; `deploy.sh` waits for them and retries each `oc apply`; if you interrupt them, wait for `oc --context crc-admin get co` to show all Available and none Progressing |
| `deploy.sh` reports a foreign operator that is its own | The AllNamespaces install copies the CSV into every namespace | The check ignores copies with `-l '!olm.copiedFrom'`; use the same selector when you list CSVs yourself |
| `x509: certificate signed by unknown authority` | The ingress CA is missing or stale | Run `setup-crc.sh` again; it rewrites the CA file. Do not use `-k` |
| `skopeo` cannot push | The registry default route is off, or the token expired | `setup-crc.sh` enables the route; the token is created per image and lasts ten minutes |
| `ImagePullBackOff` on an app pod | The image was not pushed for this language | `openshift/build-push-images.sh <lang>` |
| Pod rejected by an SCC | A manifest added `runAsUser`, `fsGroup` or a privileged field outside the project's range | Remove it; the overlays set none and the assigned UID works |
| Kafka never becomes Ready | The operator is not running, or the Kafka version is not in the bundle | `oc --context crc-admin -n cndp-amq-streams get pods`; `oc --context crc-admin -n cndp-05 describe kafka cndp` |
| Namespace stuck terminating | A KafkaTopic finalizer outlived the operator | `teardown.sh` deletes the topics while the operator runs; do not remove the operator first |

### Cross-check it yourself

Place an order through the Route, then run
`oc --context crc-admin -n cndp-05 exec pod/cndp-postgres-0 -- psql -U appuser -d appdb -c "SELECT * FROM shipments"`
and confirm one row for the order. Then read the pod's SCC with
`oc --context crc-admin -n cndp-05 get pod -l app.kubernetes.io/name=order-service -o jsonpath='{.items[0].metadata.annotations.openshift\.io/scc}'`
and confirm `restricted-v2`. The `restricted-v2` SCC admits only a user ID inside the project's
assigned range (the `openshift.io/sa.scc.uid-range` annotation on the namespace), so a fixed
`runAsUser` outside that range is refused when the pod is admitted. That rejection was not exercised
on the recorded run; read the ReplicaSet's events if you try it.

The manifests and scripts are in [`examples/05-event-driven/openshift/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/05-event-driven/openshift/).

---
*Verification status: verified: [`examples/05-event-driven/openshift/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/05-event-driven/openshift/) passes 10/10 checks in each of the five languages on OpenShift Local 4.22.14 (crc 2.64.0, Kubernetes v1.35.6, AMQ Streams `amqstreams.v3.2.1-14`, Kafka 4.2.0, 2026-10-13, on the code after the S13 and S14 refactors), using the same `verify.sh` as compose with `RUNTIME=kubernetes` over HTTPS. Every pod ran under `restricted-v2`, Tempo held a trace with all three services for each language, and teardown left the cluster empty and stopped. The SCC rejection of a fixed root user ID was not exercised.*
