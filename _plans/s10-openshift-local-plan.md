# S10 plan — Example 05 on OpenShift Local, Appendix S

Approved by the user 2026-10-11. Opus plan; Sonnet executes on `feature/openshift-local-appendix`; Opus validates.

## User decisions (2026-10-11)

1. **.NET linked trace: fix it.** Add W3C trace-context inject/extract to the three .NET 05 services; re-verify .NET 05 on Docker (10/10, linked trace in Tempo).
2. **No registry token on disk, ever (not even tmpfs).** The token lives only in shell memory. `skopeo copy` reads credentials from a process-substitution pipe: `--dest-authfile <(printf '{"auths":{"%s":{"auth":"%s"}}}' "$REGISTRY_ROUTE" "$(printf 'builder:%s' "$token" | base64 -w0)")`. `printf` is a bash builtin, so the token never appears in any argv (`/proc/*/cmdline`). Never `skopeo login` (it writes a file), never `--dest-creds`/`--dest-registry-token` (argv). If skopeo cannot read the authfile from a pipe, stop and report; do not fall back to a file.
3. **otel-lgtm:** restricted-v2 with emptyDir mounts if the offline rehearsal passes; otherwise the scoped anyuid exception (ServiceAccount `lgtm`, namespaced RoleBinding to ClusterRole `system:openshift:scc:anyuid`, `runAsUser: 0` only), documented in the appendix. Never `oc adm policy add-scc-to-user`.

## Findings that shape the design

1. AMQ Streams on OCP 4.22: newest CSV `amqstreams.v3.2.1-14`, channel `amq-streams-3.2.x` (also `amq-streams-3.x`, `stable`), all install modes. Bundled broker images are Kafka 4.1 and 4.2 only, so OpenShift runs **Kafka 4.2.0** (`metadataVersion: 4.2-IV1`) while minikube runs 4.3.1. The appendix explains the difference.
2. Postgres: `registry.redhat.io/rhel10/postgresql-18:10.2-1791491063` (sclorg). Env `POSTGRESQL_USER/PASSWORD/DATABASE`; data `/var/lib/pgsql/data`; init via sourced `*.sh` hooks in `/opt/app-root/src/postgresql-init/`; extra config in `/opt/app-root/src/postgresql-cfg/`. `POSTGRESQL_USER` is not a superuser, so the schema runs as appuser. Offline rehearsal image: `quay.io/sclorg/postgresql-18-c10s` (scratch only, never committed).
3. `docker.io/grafana/otel-lgtm:0.36.0` runs as root (workdir `/otel-lgtm`, `run-all.sh`).
4. All five languages' 05 Containerfiles end in a numeric non-root `USER` with `--chown=<uid>:0 --chmod=g=u`; expected restricted-v2-ready with no change. Live gate: each pod's `openshift.io/scc` annotation.
5. .NET 05 does not propagate trace context through Kafka (decision 1). Spring Boot (OTel agent) and Quarkus propagate automatically; confirm live.
6. `~/.kube/config` has no current-context. `crc start` adds `crc-admin` and may set current-context, so restore must handle "unset".
7. `docker push` to the default route would need root-owned `/etc/docker/certs.d` or insecure-registries (permanent host change). Use skopeo 1.22.3 from `docker-daemon:` with `--dest-cert-dir` holding the ingress CA (public, user-owned dir).
8. CRDs-catalog commit `63669a570e231d4f1f8396d229a1de512bcf0a34` has `operators.coreos.com/subscription_v1alpha1.json`, `operatorgroup_v1.json`, `kafka.strimzi.io/*`, and OpenShift schemas only under `openshift/v4.15-strict/{{.ResourceKind}}_{{.Group}}_{{.ResourceAPIVersion}}.json` (route, imagestream).
9. CRC config is already 12 vCPU / 32768 MiB / 80 GB with a pull-secret-file. No change. Scripts never run `crc config set`.
10. crc 2.64.0 is newest (`crc-linux-amd64.tar.xz` sha256 `bd170b5c66b1c703f292168249408c95c3c1d101ea93e17ca0387ab3715d0c90`); `oc` 4.22.17 (kustomize 5.7.1).

## Approach

Layout `examples/05-event-driven/openshift/`, reusing `../k8s` via kustomize (no copies):

- `operators/`: `namespace.yaml` (`cndp-amq-streams`), `operatorgroup.yaml` (`spec: {}`, AllNamespaces), `subscription.yaml` (package `amq-streams`, source `redhat-operators`, channel `amq-streams-3.2.x`, `startingCSV: amqstreams.v3.2.1-14`, `installPlanApproval: Manual`), label `app.kubernetes.io/part-of: cndp-05`.
- `components/openshift/` (`kind: Component`): Route `order-service` (edge, `insecureEdgeTerminationPolicy: Redirect`, targetPort `http`); every Deployment `imagePullPolicy: Always`; Service `order-service` to ClusterIP without nodePort.
- `overlays/{spring-boot,quarkus,dotnet,python,go}`: `namespace: cndp-05`, `resources: [../../../k8s/overlays/<lang>]`, `components: [../../components/openshift]`, `images:` mapping `localhost/cndp-05/<lang>-<svc>` to `image-registry.openshift-image-registry.svc:5000/cndp-05/<lang>-<svc>` (tag `v1`). No cpp.
- `infra/`: reuse `../../k8s/infra/kafka.yaml` and `lgtm.yaml`; patch Kafka `version: 4.2.0` + `metadataVersion: 4.2-IV1`; patch Service `lgtm-grafana` to ClusterIP; lgtm restricted-v2 securityContext + emptyDir `/data`, `/tmp` (or the decision-3 fallback); own `postgres.yaml` (StatefulSet `cndp-postgres`, Service `cndp-postgres-rw:5432`, PVC at `/var/lib/pgsql/data`, readiness `pg_isready -U appuser -d appdb`, restricted-v2); secretGenerator `cndp-postgres-app` as in k8s; configMapGenerator `postgres-init` from `../../db/init/*.sql` (single-sourced schema); ConfigMap `postgres-openshift` with hook `10-cndp-schema.sh` (`psql -v ON_ERROR_STOP=1 -U "$POSTGRESQL_USER" -d "$POSTGRESQL_DATABASE" -f` each SQL) and `cndp.conf` (`log_statement = 'all'`); Route `lgtm-grafana` (edge, Redirect).
- Images: same docker builds and tags as S9 (`localhost/cndp-05/<lang>-<svc>:v1`); Containerfile table moves to sourced `k8s/images.sh` used by both build scripts; push with `skopeo copy docker-daemon:… docker://$REGISTRY_ROUTE/cndp-05/<lang>-<svc>:v1 --dest-cert-dir "$STATE/registry-ca"` and the decision-2 pipe authfile. Token: `token="$(oc --context crc-admin create token builder -n cndp-05 --duration=10m)"`, unset after use. ImageStreams auto-created on push.
- Registry default route: enable only if off, annotate `cndp-05/enabled-default-route=true`; teardown reverts only with that annotation.
- Ingress CA from configmap `default-ingress-cert` (openshift-config-managed) into `$STATE/ingress-ca.crt`; `$STATE=${XDG_STATE_HOME:-~/.local/state}/cndp-05-crc`.
- Context: every call `oc --context crc-admin` (`ocx`/`ocn` wrappers); never `use-context`. `setup-crc.sh` records current-context before `crc start` and restores it in an EXIT trap (`set current-context` or `unset current-context`), then asserts. `crc start` stdout to /dev/null, stderr filtered for password/kubeadmin.
- verify.sh reused unchanged: `RUNTIME=kubernetes KUBECTL=oc KUBE_CONTEXT=crc-admin KUBE_NAMESPACE=cndp-05 BASE=https://order-service-cndp-05.apps-crc.testing` with `--cacert` via the script's curl options (generalize minimally only if needed; docker path must still pass).
- Linked-trace evidence in verify-matrix (not verify.sh): Tempo search inside the lgtm pod for order-service plus a consumer in one trace; `linked-trace.json`.
- Operator in its own namespace `cndp-amq-streams` with its own OperatorGroup (AllNamespaces) so teardown removes it all.

Rejected: copying k8s manifests; Helm chart; `docker push`; in-cluster BuildConfigs; quarkus-openshift S2I; `openshift-operators`; SingleNamespace OperatorGroup; anyuid first; `docker.io/library/postgres` under anyuid; a dedicated KUBECONFIG for `crc start`; token in argv or in any file.

## Steps (checkpoint commit after each)

0. This file; `modernization-plan.md` S9 row done (PR #67), S10 in progress, pins (AMQ Streams CSV/channel, Kafka 4.2.0 on OCP, rhel10/postgresql-18 tag, skopeo 1.22.3, crc sha256, openshift CRDs-catalog location).
1. Re-check pins at execution start (crc releases, amq-streams bundles for 4.22, postgresql-18 tags, otel-lgtm tags, CRDs-catalog paths).
2. .NET 05 trace propagation (decision 1); compose verify 10/10 + linked trace; `docker compose down -v`.
3. `k8s/images.sh` extraction; same 18 (context, Containerfile) rows.
4. Manifests + offline checks: render with kubectl 1.36.5 and `oc kustomize` (identical); k8s/ renders byte-identical to main; kubeconform v0.8.0 strict locally; rehearsals (a) otel-lgtm as UID 1000700000:0 read-only root + tmpfs, (b) sclorg postgres-18 hook/ownership/uuid-ossp/trust/log_statement, (c) 15 app images numeric non-zero User.
5. Scripts in `openshift/`: `lib.sh`, `setup-crc.sh`, `build-push-images.sh`, `deploy.sh`, `verify-matrix.sh`, `teardown.sh [--namespace-only|--keep-running]`, `README.md`. shellcheck clean; never print secrets; inventory before/after (report foreign items, never delete them; refuse on a foreign AMQ Streams/Strimzi install); teardown order: KafkaTopics/KafkaUsers, Kafka/KafkaNodePool, namespace cndp-05, then Subscription, CSV, InstallPlans, OperatorGroup, owned + strimzi.io CRDs, namespace cndp-amq-streams, registry route revert, leftover check, `crc stop`; idempotent; never `crc delete`.
6. verify.sh: comments only unless live requires a minimal generalization.
7. CI: `ci_changed_projects.py` (`k8s` kind covers `k8s` and `openshift` dirs; k8s/ and db/ changes also select openshift; deleted manifests still select); `examples.yml` k8s job renamed "Kubernetes and OpenShift manifests", openshift branch with the extra schema location, kubernetes-version per `oc version`, grep assertions (5 overlays, internal-registry images, Always, no NodePort, edge+Redirect Routes, Manual + startingCSV, no runAsUser except lgtm fallback). actionlint clean.
8. Diagrams `scripts/gen_32_diagrams.py` → `assets/diagrams/32-openshift-topology` and `32-openshift-image-flow` (.svg + .excalidraw); QA-render.
9. Docs: `_docs/32-appendix-s-openshift-local.md` (marker S, order 32); index.html + README (A–S, nineteen); `_docs/05-event-driven.md` cross-check; example and k8s READMEs; both prerequisites files (OpenShift Local section, crc sha256 check, pull secret by path only, skopeo/jq, resource row); CLAUDE.md S10 rules. validate_site 0 errors, Jekyll build, voice scan 0 ban-tier.
10. Live run on CRC (main loop): preconditions (minikube stopped, docker ps empty, context recorded), setup, live pin confirmations, matrix for all 5, full teardown + `crc stop`, context unchanged, scrub clean, evidence into `modernization-plan.md`.
11. Fill recorded output into Appendix S.
12. Opus validator, up to two repair rounds, PR, CI green, squash-merge, S10 row done.

## Acceptance criteria

- `openshift/` renders (operators raw, infra, 5 overlays) identically with kubectl 1.36.5 and oc 4.22 kustomize; kubeconform v0.8.0 `-strict`: 0 invalid, 0 missing schemas.
- `k8s/` renders byte-identical to main; build table unchanged (18 rows).
- Exactly 5 overlays; 3 internal-registry `:v1` images each with `imagePullPolicy: Always`; no NodePort under `openshift/`; Routes `order-service` and `lgtm-grafana` edge + Redirect; no `:latest`; every pulled image fully qualified.
- Subscription Manual with `startingCSV` = live-confirmed newest CSV; only that InstallPlan approved.
- No `runAsUser`/`fsGroup`/anyuid except the documented lgtm fallback; no `oc adm policy`, no cluster-scoped binding created.
- Live: verify.sh 10/10 for spring-boot, quarkus, dotnet, python, go on CRC; each language has a linked trace (order-service + ≥1 consumer); every app pod SCC `restricted-v2`.
- Grafana `/api/health` 200 via Route with `--cacert`; HTTP redirects. No port-forward, tunnel, `-k`/`--insecure` in `openshift/`.
- Registry token never written to any file and never in argv; no `skopeo login`.
- After teardown: no `cndp-05`/`cndp-amq-streams` namespaces, amq-streams Subscription, `amqstreams.*` CSV/InstallPlan, `*.strimzi.io` CRD, our OperatorGroup, or cndp ClusterRoleBinding; registry route restored; CRC Stopped (not deleted); second teardown exits 0.
- current-context identical before and after; foreign items reported and untouched.
- Scrub finds nothing (tokens, `"auths"`, kubeadmin password, private keys) in evidence or `git diff main`.
- .NET 05 compose verify still 10/10 with a linked trace.
- Appendix S order 32 marker S; glossary order 99; figures S.1, S.2; index/README A–S; prerequisites and CLAUDE.md updated; validate_site 0 errors; Jekyll builds; voice scan 0 ban-tier.
- Selector: `k8s/base/x.yaml` selects 05/k8s and 05/openshift; `openshift/overlays/go/kustomization.yaml` only 05/openshift; `openshift/deploy.sh` only scripts; deleted `openshift/infra/route-grafana.yaml` selects 05/openshift. actionlint clean.
- PR checks site, content-ok, examples-ok green; squash-merged.

## Risks

- Kafka CR unsupported-version condition (check CSV `STRIMZI_KAFKA_IMAGES` first); Kafka CLI path in AMQ image (`/opt/kafka/bin`); sclorg hook ownership / uuid-ossp / socket auth (rehearsal b); otel-lgtm hidden write paths (rehearsal a, Tempo query fails loudly); nested `images:` not rewritten (render assertion); `crc start` context/password leak (trap + filter + scrub); builder SA timing (`wait_for`); route TLS not signed by ingress CA (loud x509; never disable TLS verify without asking); skopeo cannot read a pipe authfile (stop and report); AllNamespaces operator touching foreign Kafka (inventory refusal); KafkaTopic finalizer (delete topics while operator runs); TraceQL `&&` unsupported (intersect trace IDs); kubeconform kubernetes-version for OCP 4.22 (from `oc version`); full CI matrix on this PR (expected).

## Live pin confirmations

packagemanifest `amq-streams` channels/currentCSV; CSV `STRIMZI_KAFKA_IMAGES`; `/opt/kafka/bin` in broker pod; postgresql-18 pull via cluster pull secret; `oc version` server Kubernetes version; registry default-route initial state; `builder` SA in new projects; context name `crc-admin`; route host `<name>-cndp-05.apps-crc.testing`; pod SCC annotations; TraceQL `&&`.

## Status

| Step | Status |
|------|--------|
| 0 plan | done |
| 1 pins re-check | done (offline): crc 2.64.0 and kubeconform v0.8.0 still newest, otel-lgtm 0.36.0 newest tag, CRDs-catalog route/imagestream schemas present at the pinned commit; the AMQ Streams CSV and the registry.redhat.io postgresql-18 tag need a login or the cluster, so they stay in the live confirmations |
| 2 .NET trace propagation | done (a0f03c4): compose verify 10/10, one trace holds order-service, shipping-consumer and notification-consumer |
| 3 images.sh | done (8e2992a): `k8s/images.sh` sourced by both build scripts, 18 rows unchanged |
| 4 manifests and rehearsals | done (9b19ce3): see "Offline results" |
| 5 scripts | done (7646ef7): lib.sh, setup-crc.sh, build-push-images.sh, deploy.sh, verify-matrix.sh, teardown.sh, README.md; shellcheck 0.11.0 clean |
| 6 verify.sh | done (de36779): comments only |
| 7 CI | done (f62dc44): selector and `k8s` job; actionlint 1.7.12 clean |
| 8 diagrams | done (d059628): S.1 and S.2 |
| 9 docs | done: Appendix S, index, README, chapter 05, READMEs, prerequisites, CLAUDE.md |
| 10 live | done 2026-10-11: see "Live results" |
| 11 fill recorded output | done: every live-result placeholder replaced in Appendix S and the chapter 05 footer |
| 12 validator, PR, merge | pending |

## Offline results (steps 4 to 9)

- Renders: `operators`, `infra` and five overlays are identical with kubectl 1.36.5 and oc 4.22.17 kustomize; kubeconform v0.8.0 (checksum verified) `-strict -kubernetes-version 1.35.6`: 0 invalid, 0 errors, 0 skipped. The k8s overlays and infra render byte-identical to main. The Kubernetes version 1.35.6 is a to-confirm against `oc version` on the cluster.
- otel-lgtm 0.36.0 as `--user 1000700000:0 --read-only --cap-drop ALL --security-opt no-new-privileges`: writes `/data` (exec), `/tmp`, `/var/tempo`; needs `GF_PLUGINS_PREINSTALL_DISABLED=true` (otherwise Grafana removes the bundled data source plugins and fails to replace them on a read-only tree). Grafana `/api/health` ok, four data sources healthy, OTLP POST to 4318 accepted and the trace readable from Tempo. emptyDir path chosen; anyuid fallback not needed.
- sclorg postgresql-18-c10s (digest sha256:1da2e7d2f7ede454d37b73a874d78d307c4d776762206f887b586f0e9fa11549, rehearsal only): `postgresql-init` hooks run before the role and database exist, so the schema hook is `postgresql-start/10-cndp-schema.sh` (runs every start, SQL is idempotent). appuser owns the three tables, `uuid-ossp` loads, local socket auth is `trust` (no password), `log_statement` is `all`, restart is a no-op.
- All 15 app images report a numeric non-zero `User` (185 for Spring Boot and Quarkus, 1001 for .NET, Python and Go).
- skopeo 1.22.3 reads a process-substitution `--dest-authfile` (pushed to a local htpasswd registry; an unauthenticated read failed with 401).
- Not verifiable offline: the Red Hat `rhel10/postgresql-18:10.2-1791491063` tag (registry.redhat.io needs a login), the AMQ Streams CSV, and Kafka CR `kafka.strimzi.io/v1` acceptance by AMQ Streams 3.2.

## Live results (step 10, 2026-10-11)

Evidence (outside the repo): `/tmp/claude-1000/-home-rsedor-Dev/0dea024d-0bf0-4ae5-bddd-7dec0cf60b22/scratchpad/s10/live/` (`matrix/results.tsv`, `matrix/logs/`, `matrix/evidence/<lang>/`, `setup3.log`, `teardown.log`).

- crc 2.64.0, OpenShift 4.22.14, Kubernetes v1.35.6.
- AMQ Streams packagemanifest: default channel `stable`; `amq-streams-3.2.x` currentCSV `amqstreams.v3.2.1-14` (newest); CSV Succeeded; Kafka 4.2.0.
- All five languages: 10 passed, 0 failed (spring-boot 139 s, quarkus 123 s, dotnet 125 s, python 121 s, go 120 s).
- Every pod (Kafka, Postgres, lgtm, three app pods) on `restricted-v2`; the otel-lgtm anyuid fallback was not needed.
- Linked traces in Tempo with order-service, shipping-consumer and notification-consumer for every language.
- Plain HTTP on the Route answers 302 to https; Grafana `/api/health` ok (13.2.3).
- Teardown removed the operator, 10 CRDs, both namespaces and reverted the registry route; crc stopped, not deleted; a second teardown exited 0. current-context unset before and after; `~/.kube/config` sha256 identical.
- Not exercised live: the `runAsUser: 0` rejection; the appendix states only what `restricted-v2` documents (UID range).

Script bugs found and fixed during the live run (a379989, 1f77342, 82fdd88):

1. The inventory failed under `pipefail` on a clean cluster.
2. The scripts did not wait for cluster operators to settle after enabling the registry default route; `crc status` reports Starting during the API-server rollout.
3. The foreign-operator check counted OLM-copied CSVs (AllNamespaces copies the CSV into every namespace); now filtered with `-l '!olm.copiedFrom'`.

`matrix-run1/` exposed these bugs and is not the recorded output. Items 2 and 3 are rows in the Appendix S troubleshooting table.
