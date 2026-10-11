# S9 plan — Example 05 on minikube, Appendix R

Approved by the user 2026-10-11. Opus plan; Sonnet executes on `docs/minikube-docker-driver`; Opus validates.

## Findings that shape the design

1. Profile is **`cndp-k8s`**, not `cndp`: the docker driver creates a Docker network named after the profile, and `_infra/compose-lgtm.yaml` already names the compose network `cndp`.
2. `minikube start` switches kubectl's current-context unless `--keep-context` is passed. Always pass it; show current-context unchanged before and after.
3. Existing profiles (capstone, datamesh, eip, helm4dev (broken), istio, mea, minikube, mof-capstone) are never started, stopped or modified.
4. Ordering comes from the `order` front matter. minikube is **Appendix R** (`_docs/31-appendix-r-minikube.md`, `order: 31`, `marker: "R"`). S10 OpenShift Local becomes **Appendix S** (order 32). Glossary goes to `order: 99` (keep its filename).
5. S10 reuses the environment contract (Service, Secret, ConfigMap names), the Kafka CR shape and `verify.sh RUNTIME=kubernetes` with `KUBECTL=oc`; not the kustomize files as-is.
6. kustomize cannot read `../db/init/*.sql` under the default load restrictor: render with `kubectl kustomize --load-restrictor LoadRestrictionsNone … | kubectl apply -f -` (scripts and CI). Single source for the schema.
7. Files under `examples/05-event-driven/k8s/` would currently trigger the 05 fallback (all 18 projects). Add a `k8s` kind to the selector. This PR edits `EVERYTHING_TRIGGERS` files, so its own CI runs the full matrix once (expected).
8. All 18 consumers use `earliest`; only order-service has `/healthz`; 05 `verify.sh` only uses `ctr_exec` against Kafka and Postgres.

## Approach

- Cluster: `minikube start -p cndp-k8s --driver=docker --container-runtime=containerd --kubernetes-version=v1.36.5 --memory=8g --cpus=4 --disk-size=40g --ports=127.0.0.1:30080:30080,127.0.0.1:30300:30300 --keep-context`.
- Kafka: Strimzi 1.2.0 operator (Helm OCI chart `oci://quay.io/strimzi-helm/strimzi-kafka-operator`, namespace `strimzi`, `watchAnyNamespace=true`) + `KafkaNodePool` `dual-role` + `Kafka` `cndp` (version 4.3.1, KRaft, plain 9092 tls false, auto-create topics, replication 1, no entity operator).
- Postgres: plain StatefulSet `cndp-postgres` on `docker.io/library/postgres:18.6-alpine`, schema ConfigMap at `/docker-entrypoint-initdb.d`, volume at `/var/lib/postgresql`, Service `cndp-postgres-rw:5432`.
- Observability: one `docker.io/grafana/otel-lgtm:0.36.0` Deployment; Service `lgtm` (4318), Service `lgtm-grafana` NodePort 3000→30300.
- Apps: kustomize `infra/`, `base/` (3 Deployments; order-service NodePort 8080→30080), `overlays/{spring-boot,quarkus,dotnet,python,cpp,go}`.
- Images: `docker build` with each Containerfile (keeps host BuildKit caches) → `minikube -p cndp-k8s image load --overwrite=true`, `imagePullPolicy: Never`, names `localhost/cndp-05/<lang>-<svc>:v1`.
- Verify: existing `verify.sh` with `RUNTIME=kubernetes`, `BASE=http://127.0.0.1:30080`. Fresh namespace `cndp-05` per language.
- Rejected: `minikube image build` (loses caches), registry addon, CNPG (peer auth breaks psql check; S10 doesn't use it), plain Kafka StatefulSet, full LGTM Helm stack, no observability, one language only, Helm chart for S9, port-forward/tunnel/`minikube service` (forbidden).

## Steps

0. Plan housekeeping: S9 row "in progress"; S10 acceptance "Appendix S"; pins table adds kubectl 1.36.5, kubeconform v0.8.0, Strimzi chart 1.2.0, CRDs-catalog SHA, profile `cndp-k8s` ports 30080/30300.
1. Re-verify pins (gh release list, skopeo list-tags, `helm show chart/values` for Strimzi 1.2.0; confirm Kafka 4.3.1 and Kubernetes 1.36 supported).
2. Manifests in `examples/05-event-driven/k8s/`:
   - `infra/` (namespace `cndp-05`): secretGenerator `cndp-postgres-app` (appuser/apppass, same demo creds as compose, `disableNameSuffixHash: true`); configMapGenerator `postgres-init` from `../../db/init/*.sql`; `kafka.yaml` (nodepool persistent-claim 2Gi `deleteClaim: true`, requests 250m/1Gi, limit 2Gi); `postgres.yaml` (same env/flags as compose, readiness `pg_isready -U appuser -d appdb`); `lgtm.yaml` (GF_AUTH_* as compose, readiness `/api/health` on 3000, ~1.5Gi limit).
   - `base/`: label `app.kubernetes.io/part-of: cndp-05`; Deployments order-service, shipping-consumer, notification-consumer; restricted-v2-ready securityContext (runAsNonRoot, no privilege escalation, drop ALL, seccomp RuntimeDefault, no fixed UID); `PG_USER`/`PG_PASSWORD` from secretKeyRef; `OTEL_EXPORTER_OTLP_ENDPOINT=http://lgtm:4318`; order-service startup+readiness `/healthz:8080` (startup ~150 s); requests set; memory limits ~768Mi JVM/.NET, ~256Mi Go/C++/Python.
   - `overlays/<lang>/`: `images:` mapping; JSON6902 `add /spec/template/spec/containers/0/env/-` env patches with the compose variable names so `$(PG_PASSWORD)` expands. Smoke-render every overlay and check env order.
3. Scripts (all explicit `-p`/`--context`/`--kube-context`; never `minikube config set`; never change current-context): `setup-profile.sh` (preflight Docker context default, minikube ≥ v1.39.0, inotify; refuse if another profile Running; `ss -ltn` port check; create/start; assert `docker port cndp-k8s` binds 127.0.0.1), `build-images.sh <lang>…` (18-row table; .NET uses `dotnet/` context with `-f Containerfile.<svc>`), `deploy.sh <lang>` (helm upgrade --install Strimzi; apply ns; render+apply infra; wait Kafka Ready 600 s, postgres, lgtm; render+apply overlay; rollout status; poll /healthz), `teardown.sh [--operator]` (never deletes the profile; prints stop/delete commands), `verify-matrix.sh [langs]` (build, deploy, verify, evidence, namespace teardown; TSV + logs to `$OUT`, default outside the repo), `README.md`.
4. `examples/05-event-driven/verify.sh`: `kubernetes)` runtime with `KUBECTL`, `KUBE_CONTEXT` (default `cndp-k8s`), `KUBE_NAMESPACE` (default `cndp-05`); `ctr_target` maps `cndp-kafka`→`pod/cndp-dual-role-0 -c kafka`, `cndp-postgres`→`pod/cndp-postgres-0` (overridable `KAFKA_TARGET`, `POSTGRES_TARGET`); other `ctr_*` helpers error "not supported on kubernetes". Docker path unchanged; still 10 checks; shellcheck clean.
5. CI: `scripts/ci_changed_projects.py` new `k8s` kind (files under `examples/<NN>/k8s/` select that dir before the language fallback; `examples/<NN>/db/` changes also select `<NN>/k8s`; `k8s/*.sh` into `scripts`; `select_everything` includes them). `.github/workflows/examples.yml`: `changes` output `k8s`; job `k8s` installs kubectl v1.36.5 (sha256) and kubeconform v0.8.0 (CHECKSUMS), renders infra + every overlay into `kubeconform -strict -summary -kubernetes-version 1.36.5` with the CRDs-catalog schema location pinned to commit `63669a570e231d4f1f8396d229a1de512bcf0a34`, plus grep assertions (no `:latest`, app images `localhost/cndp-05/<lang>-`, `imagePullPolicy: Never`, nodePorts 30080/30300); add `k8s` to `examples-ok.needs`. actionlint clean.
6. Diagrams: `scripts/gen_31_diagrams.py` (pattern of `gen_30`) → `assets/diagrams/31-minikube-topology.{svg,excalidraw}` and `31-minikube-image-flow.{svg,excalidraw}`; QA-render to PNG.
7. Appendix `_docs/31-appendix-r-minikube.md` ("Running Example 05 on minikube", marker R, order 31, part "Deep-dive appendices"): why a cluster changes things; the runtime; Figure R.1; compose→Kubernetes mapping table; kustomize layout with a six-tab codetabs block of overlay env patches (Spring Boot, Quarkus, .NET, Python, C++, Go); Figure R.2; run it; recorded verify output; clean up; troubleshooting table; cross-check; verification footer. No "podman", no positional terms, `{% raw %}` around any `{{`. Voice scan ban tier must be 0.
8. Site/docs: glossary `order: 99`; `index.html` + `README.md` "eighteen … A–R"; `_docs/05-event-driven.md` cross-check sentence + footer; `examples/05-event-driven/README.md` "Run on minikube"; both prerequisites files pin minikube v1.39.0 and kubectl v1.36.5 with sha256 checks and a docker-driver note and resource row; CLAUDE.md minikube line. `validate_site.py` 0 errors; Jekyll build.
9. Live run: no other profile running, no compose containers; record current-context; `setup-profile.sh`; `verify-matrix.sh` all six; each `10 passed, 0 failed`; Grafana `/api/health` once; `teardown.sh --operator`; `minikube stop -p cndp-k8s`; current-context unchanged; evidence section in `_plans/modernization-plan.md`.
10. Opus validation (re-render, review, live rerun of at least a JVM language and C++), repairs, PR, CI (full matrix once), squash-merge.

## Acceptance criteria

- Renders: infra + six overlays render; kubeconform v0.8.0 `-strict` 0 invalid against 1.36.5.
- No `:latest`; pulled images fully qualified; app images `localhost/cndp-05/<lang>-<svc>:v1`.
- `cndp-k8s` docker/containerd/v1.36.5; no other profile changed.
- `docker port cndp-k8s` only `127.0.0.1:` for 30080 and 30300; no port-forward/tunnel/`minikube service` anywhere.
- `RUNTIME=kubernetes verify.sh` 10/10 for all six languages; docker-path verify still passes for at least one language.
- current-context unchanged; run ends with `cndp-k8s` Stopped (not deleted), namespaces `cndp-05` and `strimzi` removed first.
- Appendix R with order 31; glossary order 99; R.1 and R.2 as svg + excalidraw.
- `validate_site.py` 0 errors; Jekyll builds; voice scan 0 ban-tier hits on new/changed docs.
- Prerequisites pin minikube v1.39.0, kubectl v1.36.5 with sha256; CLAUDE.md updated; A–R in index and README.
- Plan file: S9 evidence; S10 says Appendix S; pins table updated.
- Selector: a `k8s/base/x.yaml` change selects only `k8s`; a `k8s/*.sh` change selects `scripts`; actionlint clean.
- PR checks green incl. new `k8s` job; squash-merged.

## Pins (re-verify at execution start)

minikube v1.39.0; Kubernetes v1.36.5; kubectl v1.36.5 (kustomize v5.8.1); Strimzi operator/chart 1.2.0 (Kafka image expected `quay.io/strimzi/kafka:1.2.0-kafka-4.3.1`); Kafka 4.3.1; postgres 18.6-alpine; otel-lgtm 0.36.0; kubeconform v0.8.0; CRDs-catalog `63669a570e231d4f1f8396d229a1de512bcf0a34`. Host Helm is v3.18.3 while docs pin 4.3.0: scripts use only `upgrade --install` with OCI (works on both); do not change host tools.

## Risks

Network collision (profile name); current-context switch (`--keep-context`); load restrictor (flag, or `kubectl create configmap --dry-run` fallback); `$(PG_PASSWORD)` env order; `localhost/` image names in containerd (fallback bare names, record it); Kafka CLI memory in broker pod (2Gi); JVM/.NET OOM; consumer CrashLoopBackOff (two-phase apply); Strimzi version support; CRDs-catalog schema drift (`-skip Kafka,KafkaNodePool` with a comment if needed); full CI matrix once; port collisions; other running stacks (refuse, never auto-stop); root images fine on minikube (S10 swaps); validator word rules; node disk (40g).
