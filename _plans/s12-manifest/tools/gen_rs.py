#!/usr/bin/env python3
"""Generate the Appendix R / S slides and the agenda update for each language deck.

Writes rs/<deck>.json (deck_edit ops). Template slides are the Appendix O slides of the same
deck (divider, figure, code, bullets); shape ids are read from each deck so the ops address the
right boxes. Run with the S12 venv python. Content source: _docs/31-appendix-r-minikube.md,
_docs/32-appendix-s-openshift-local.md and examples/05-event-driven/{k8s,openshift}/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path("/home/rsedor/Dev/cloud-native-design-patterns")
sys.path.insert(0, str(REPO / "scripts"))
from pptx import Presentation  # noqa: E402
from pptx.util import Emu  # noqa: E402

WORK = Path(__file__).resolve().parent
PNG = "lgtm-presentation/edits/png"  # relative to the repo root (run deck_edit from there)

DECKS = {
    # deck: (lang id in scripts, display name, templates {divider, figure, code, bullets}, last page)
    "Python": ("python", "Python", dict(divider=516, figure=525, code=521, bullets=527), 243),
    "Quarkus": ("quarkus", "Quarkus", dict(divider=516, figure=525, code=521, bullets=527), 243),
    "Spring": ("spring-boot", "Spring Boot", dict(divider=520, figure=529, code=525, bullets=531), 247),
    "DotNet": ("dotnet", ".NET", dict(divider=530, figure=539, code=535, bullets=541), 271),
    "Go": ("go", "Go", dict(divider=516, figure=525, code=521, bullets=527), 243),
    "Cpp": ("cpp", "C++", dict(divider=516, figure=525, code=521, bullets=527), 243),
}

ENV = {  # k8s/overlays/<lang>/kustomization.yaml, the variables each overlay appends
    "spring-boot": [
        "- name: SPRING_DATASOURCE_URL",
        '  value: "jdbc:postgresql://cndp-postgres-rw:5432/appdb"',
        "- name: SPRING_DATASOURCE_USERNAME",
        '  value: "$(PG_USER)"',
        "- name: SPRING_DATASOURCE_PASSWORD",
        '  value: "$(PG_PASSWORD)"',
        "- name: SPRING_KAFKA_BOOTSTRAP_SERVERS",
        '  value: "cndp-kafka-bootstrap:9092"',
    ],
    "quarkus": [
        "- name: QUARKUS_DATASOURCE_JDBC_URL",
        '  value: "jdbc:postgresql://cndp-postgres-rw:5432/appdb"',
        "- name: QUARKUS_DATASOURCE_USERNAME",
        '  value: "$(PG_USER)"',
        "- name: QUARKUS_DATASOURCE_PASSWORD",
        '  value: "$(PG_PASSWORD)"',
        "- name: KAFKA_BOOTSTRAP_SERVERS",
        '  value: "cndp-kafka-bootstrap:9092"',
    ],
    "dotnet": [
        "- name: DATABASE_URL",
        '  value: "Host=cndp-postgres-rw;Port=5432;Database=appdb;\\',
        '    Username=$(PG_USER);Password=$(PG_PASSWORD)"',
        "- name: KAFKA_BOOTSTRAP",
        '  value: "cndp-kafka-bootstrap:9092"',
        "# order-service only",
        "- name: SERVICE_VERSION",
        '  value: "1.0.0"',
    ],
    "python": [
        "- name: DATABASE_URL",
        '  value: "postgres://$(PG_USER):$(PG_PASSWORD)@cndp-postgres-rw:5432/appdb"',
        "- name: KAFKA_BOOTSTRAP",
        '  value: "cndp-kafka-bootstrap:9092"',
        "# memory: requests 128Mi, limits 256Mi",
    ],
    "cpp": [
        "- name: PG_CONNINFO",
        '  value: "postgresql://$(PG_USER):$(PG_PASSWORD)@cndp-postgres-rw:5432/appdb"',
        "- name: KAFKA_BOOTSTRAP",
        '  value: "cndp-kafka-bootstrap:9092"',
        "# memory: requests 128Mi, limits 256Mi",
    ],
    "go": [
        "- name: DATABASE_URL",
        '  value: "postgres://$(PG_USER):$(PG_PASSWORD)@cndp-postgres-rw:5432/appdb"',
        "- name: KAFKA_BOOTSTRAP",
        '  value: "cndp-kafka-bootstrap:9092"',
        "# memory: requests 128Mi, limits 256Mi",
    ],
}

AGENDA_TAIL = {
    # second agenda column from "07 · Workflows & Jobs" down; the E-I line is shortened so the
    # extra R-S line fits the fixed box (no autofit).
    "default": [
        "07 · Workflows & Jobs", "08 · API Management", "09 · API Registry", "10 · API Metadata",
        "11 · Observability", "12 · Security", "13 · Anti-Patterns",
        "Appendices A–D · Protocols, Versioning, WebSockets, Sagas",
        "Appendices E–I · Errors, DDD, Coupling, Shutdown, L7 Routing",
        "Appendices K–L · Monolith → Microservices, Caching Patterns",
        "Appendices M–O · Failure modes, Feature Flags, API Testing",
        "Appendices R–S · Example 05 on minikube and OpenShift Local",
        "Glossary of acronyms",
    ],
    "DotNet": [
        "07 · Workflows & Jobs", "08 · API Management", "09 · API Registry", "10 · API Metadata",
        "11 · Observability", "12 · Security", "13 · Anti-Patterns",
        "Appendices A–D · Protocols, Versioning, WebSockets, Sagas",
        "Appendices E–I · Errors, DDD, Coupling, Shutdown, L7 Routing",
        "Appendices J–L · .NET 10 Toolkit, Monolith → Microservices, Caching",
        "Appendices M–O · Failure modes, Feature Flags, API Testing",
        "Appendices P–S · .NET on Linux, Blazor, minikube, OpenShift Local",
        "Glossary of acronyms",
    ],
    "Cpp": [
        "07 · Workflows & Jobs", "08 · API Management", "09 · API Registry", "10 · API Metadata",
        "11 · Observability", "12 · Security", "13 · Anti-Patterns",
        "Appendices A–D · Protocols, Versioning, WebSockets, Sagas",
        "Appendices E–I · Errors, DDD, Coupling, Shutdown, L7 Routing",
        "Appendices K–L · Monolith → Microservices, Caching Patterns",
        "Appendices M–O · Failure modes, Feature Flags, API Testing",
        "Appendix R · Example 05 on minikube",
        "Glossary of acronyms",
    ],
}

AGENDA_NOTES = {
    "default": (
        "The agenda: a short setup, thirteen sections, and the deep-dive appendices. The setup motivates "
        "why patterns matter in the age of AI. Sections 1 to 6 build the system from principles up through "
        "data and streaming; sections 7 to 13 cover the operational platform around it (workflows, management, "
        "registry, metadata, observability), then security, and close on anti-patterns.",
        "The appendices are reference material for the questions that come up: protocols, versioning, "
        "WebSockets, sagas, errors, DDD, coupling, shutdown, L7 routing, monolith-to-microservices decomposition, "
        "caching, failure modes, feature flags and API testing{extra}. Appendices R and S run Example 05 on "
        "minikube and on OpenShift Local with the same verify.sh as compose. A glossary of acronyms closes the deck.",
        "Tell the audience which sections you will cover given the session length. The overview that follows "
        "reframes the agenda as the narrative arc: what we build and in what order.",
    ),
    "Cpp": (
        "The agenda: the same scope as the other decks in the series. A short setup, thirteen sections, the "
        "deep-dive appendices A to O, Appendix R and a glossary. Every section is shown in idiomatic C++23; "
        "the architecture and the running example are the same as in the other languages.",
        "Appendix R runs Example 05 on minikube with the same verify.sh as compose. OpenShift Local "
        "(Appendix S in the other decks) covers Spring Boot, Quarkus, .NET, Python and Go, not C++.",
        "Tell the audience which sections you will cover given the session length.",
    ),
}


def shapes(prs, sid):
    s = next(x for x in prs.slides if x.slide_id == sid)
    out = []
    for sh in s.shapes:
        d = dict(id=sh.shape_id, name=sh.name, y=round(Emu(sh.top).inches, 2), h=round(Emu(sh.height).inches, 2),
                 pic=sh.shape_type == 13, text=sh.text_frame.text if sh.has_text_frame else "")
        if sh.has_text_frame:
            sz = [r.font.size.pt for p in sh.text_frame.paragraphs for r in p.runs if r.font.size]
            fn = [r.font.name or "" for p in sh.text_frame.paragraphs for r in p.runs]
            d["size"] = max(sz) if sz else 0
            d["mono"] = any("Mono" in f for f in fn)
        out.append(d)
    return out


def pick(sh, cond, what, sid):
    hit = [s for s in sh if cond(s)]
    if len(hit) != 1:
        raise SystemExit(f"template {sid}: {what} matched {len(hit)}: {[(s['id'], s['text'][:30]) for s in hit]}")
    return hit[0]["id"]


def roles(prs, t):
    r = {}
    d = shapes(prs, t["divider"])
    r["div_letter"] = pick(d, lambda s: not s["pic"] and s.get("size") == 22, "divider letter", t["divider"])
    r["div_title"] = pick(d, lambda s: not s["pic"] and s.get("size", 0) >= 40, "divider title", t["divider"])
    r["div_sub"] = pick(d, lambda s: not s["pic"] and 14 <= s.get("size", 0) <= 18, "divider subtitle", t["divider"])
    for kind in ("figure", "code", "bullets"):
        sh = shapes(prs, t[kind])
        r[f"{kind}_eyebrow"] = pick(sh, lambda s: not s["pic"] and abs(s["y"] - 0.42) < 0.05, "eyebrow", t[kind])
        r[f"{kind}_title"] = pick(sh, lambda s: not s["pic"] and abs(s["y"] - 0.74) < 0.05, "title", t[kind])
        r[f"{kind}_foot"] = pick(sh, lambda s: not s["pic"] and abs(s["y"] - 6.50) < 0.05, "caption", t[kind])
        if kind == "figure":
            r["figure_pic"] = pick(sh, lambda s: s["pic"] and 1.5 < s["y"] < 2.0, "picture", t[kind])
        if kind == "code":
            r["code_chip"] = pick(sh, lambda s: s.get("mono") and abs(s["y"] - 1.06) < 0.05, "chip", t[kind])
            r["code_box"] = pick(sh, lambda s: s.get("mono") and s["h"] > 3, "code box", t[kind])
        if kind == "bullets":
            r["bullets_body"] = pick(sh, lambda s: not s["pic"] and abs(s["y"] - 1.85) < 0.05 and s["h"] > 3, "body", t[kind])
    return r


class Gen:
    def __init__(self, deck, prs):
        self.deck = deck
        self.lang, self.name, self.t, self.page = DECKS[deck]
        self.r = roles(prs, self.t)
        self.ops = []
        self.n = 0

    def _clone(self, kind, tag):
        self.ops.append({"op": "clone_slide", "template": self.t[kind], "as": tag, "cat": "new"})
        return "$" + tag

    def _page(self, ref):
        self.page += 1
        self.ops.append({"op": "set_page_number", "sldId": ref, "text": str(self.page), "cat": "new"})

    def _notes(self, ref, paras):
        self.ops.append({"op": "set_notes", "sldId": ref, "paragraphs": list(paras), "cat": "new"})

    def _text(self, ref, sid, paras):
        self.ops.append({"op": "set_text", "sldId": ref, "shape_id": sid, "paragraphs": list(paras), "cat": "new"})

    def divider(self, tag, letter, title, sub, notes):
        ref = self._clone("divider", tag)
        self._text(ref, self.r["div_letter"], [letter])
        self._text(ref, self.r["div_title"], [title])
        self._text(ref, self.r["div_sub"], [sub])
        self._notes(ref, notes)

    def bullets(self, tag, eyebrow, title, items, foot, notes):
        ref = self._clone("bullets", tag)
        self._page(ref)
        self._text(ref, self.r["bullets_eyebrow"], [eyebrow])
        self._text(ref, self.r["bullets_title"], [title])
        self._text(ref, self.r["bullets_body"], items)
        self._text(ref, self.r["bullets_foot"], [foot])
        self._notes(ref, notes)

    def figure(self, tag, eyebrow, title, png, caption, notes):
        ref = self._clone("figure", tag)
        self._page(ref)
        self._text(ref, self.r["figure_eyebrow"], [eyebrow])
        self._text(ref, self.r["figure_title"], [title])
        self.ops.append({"op": "replace_picture", "sldId": ref, "shape_id": self.r["figure_pic"],
                         "png": f"{PNG}/{png}.png", "cat": "new"})
        self._text(ref, self.r["figure_foot"], [caption])
        self._notes(ref, notes)

    def code(self, tag, eyebrow, title, chip, lines, caption, notes):
        ref = self._clone("code", tag)
        self._page(ref)
        self._text(ref, self.r["code_eyebrow"], [eyebrow])
        self._text(ref, self.r["code_title"], [title])
        self._text(ref, self.r["code_chip"], [chip])
        self.ops.append({"op": "set_code", "sldId": ref, "shape_id": self.r["code_box"], "lines": list(lines), "cat": "new"})
        self._text(ref, self.r["code_foot"], [caption])
        self._notes(ref, notes)


R_EB = "APPENDIX R · MINIKUBE"
S_EB = "APPENDIX S · OPENSHIFT LOCAL"
R_TIMES = "Spring Boot 361 s · Quarkus 135 s · .NET 134 s · Python 116 s · C++ 103 s · Go 104 s"
S_TIMES = "Spring Boot 139 s · Quarkus 123 s · .NET 125 s · Python 121 s · Go 120 s"


def appendix_r(g: Gen):
    lang, name = g.lang, g.name
    cpp = g.deck == "Cpp"
    g.divider("r0", "R", "Example 05 on minikube",
              "The same services and the same verify.sh on a single-node Kubernetes cluster",
              ["Appendix R takes Example 05, the event-driven fan-out, from docker compose to a single-node "
               "Kubernetes cluster on minikube, in all six languages, and records what changed. Compose proves "
               "the code; a cluster adds questions compose never asks: where configuration and credentials live, "
               "how a service finds a broker that an operator manages, what restarts a process that exits, and how "
               "a request from the host reaches a pod.",
               "The arc: the runtime, the topology, the compose-to-Kubernetes mapping, one overlay per language, "
               "how images get into the node, how to run it, and the recorded results."
               + (" OpenShift Local (Appendix S) is not part of the C++ deck: that appendix covers the other five "
                  "languages, and C++ runs here on minikube." if cpp else
                  " Appendix S then reuses the same contract on OpenShift Local.")])
    g.bullets("r1", R_EB, "From compose to a cluster", [
        "Compose proves the code; a cluster adds configuration, credentials, discovery, restarts and ingress.",
        "Scope: Example 05 (event-driven fan-out), three services, all six languages, one node.",
        "One Kafka broker, one Postgres instance, no service mesh: a local topology, not production.",
        "The contract carries over: Service names, the Secret, environment variables, the health endpoint.",
        "The same verify.sh runs against compose and the cluster: ten checks per language.",
    ], "Site: Appendix R · Code: examples/05-event-driven/k8s/",
        ["What the appendix covers and what it leaves out. The scope is one example on one node: one Kafka broker, "
         "one Postgres instance, no service mesh. High availability, network policy and autoscaling are outside it.",
         "What it fixes is the contract between an application and its platform: the Service names, the Secret that "
         "holds the database credential, the environment variables each language reads, and the health endpoint. "
         "That contract is what carries over to OpenShift Local, and it is why the application code is unchanged.",
         "The test is the one compose uses: verify.sh, ten checks, with its container operations switched to "
         "kubectl exec."])
    g.bullets("r2", R_EB, "The minikube runtime", [
        "Profile cndp-k8s: Docker driver on Docker Engine, containerd, Kubernetes v1.36.5.",
        "8 GB memory, 4 CPUs, 40 GB disk for Kafka, Postgres, LGTM and three services.",
        "NodePorts 30080 (order-service) and 30300 (Grafana), published on 127.0.0.1 at creation.",
        "No kubectl port-forward, minikube tunnel or minikube service: forwarded connections drop.",
        "Every command passes --context cndp-k8s; setup-profile.sh restores the prior context.",
    ], "minikube v1.39.0 · kubectl v1.36.5 · Helm v4.3.0 · Strimzi 1.2.0",
        ["minikube runs the control plane and the workload in one container on Docker Engine, the same engine "
         "compose uses, with containerd as the container runtime inside the node. Kubernetes v1.36.5 matches the "
         "pinned kubectl, so client and server are the same version.",
         "Host access uses two NodePorts published on the loopback address when the profile is created. "
         "Port-forwarding, minikube tunnel and minikube service are not used: forwarded connections drop under load "
         "and on idle, and a drop looks like a broken service. setup-profile.sh checks with docker port that both "
         "ports bind to 127.0.0.1.",
         "The kubectl context never changes: every command names --context cndp-k8s, minikube start runs with "
         "--keep-context, and setup-profile.sh restores the prior context because minikube's restart path can "
         "override that flag."])
    g.figure("r3", R_EB, "One node, two namespaces", "31-minikube-topology",
             "The node container holds two namespaces; the host reaches two loopback NodePorts and uses kubectl exec",
             ["The topology. The node container cndp-k8s holds two namespaces: strimzi runs the Strimzi operator, and "
              "cndp-05 runs order-service, the shipping and notification consumers, a single-node KRaft Kafka cluster, "
              "Postgres 18, the LGTM stack and the Postgres Secret.",
              "From the host, curl and verify.sh reach order-service on 127.0.0.1:30080, a browser reaches Grafana on "
              "127.0.0.1:30300, and kubectl exec runs the Kafka and Postgres checks inside their pods. Other minikube "
              "profiles stay stopped while this one runs."])
    g.bullets("r4", R_EB, "Compose to Kubernetes", [
        "kafka → Strimzi Kafka + KafkaNodePool, bootstrap cndp-kafka-bootstrap:9092 (Kafka 4.3.1).",
        "postgres → StatefulSet cndp-postgres, schema ConfigMap, Service cndp-postgres-rw.",
        "Credential → Secret cndp-postgres-app, read through secretKeyRef.",
        "build: → docker build, then minikube image load; imagePullPolicy: Never.",
        "healthcheck → startup and readiness probes on the order-service /healthz.",
        "ports: 8080:8080 → NodePort 30080.",
    ], "The schema file and the OTLP endpoint http://lgtm:4318 are the same ones compose uses.",
        ["Each compose element has a Kubernetes counterpart, and each counterpart changes something. Kafka becomes a "
         "Kafka resource that the Strimzi operator turns into a broker; the plain listener on port 9092 is in-cluster "
         "only. Postgres becomes a StatefulSet that mounts the same schema file compose mounts.",
         "The demo credential moves out of every service's environment into one Secret. Only order-service has an HTTP "
         "surface, so it alone has startup and readiness probes, with a 150-second startup window for the JVM and .NET "
         "images. The consumers have no HTTP surface: the cluster restarts them if they exit, and they start from the "
         "earliest offset, so a restart loses nothing."])
    g.code("r5", R_EB, "One overlay per language", "yaml · kustomize", [
        f"# k8s/overlays/{lang}/kustomization.yaml (excerpt)",
        "images:",
        "  - name: order-service",
        f"    newName: localhost/cndp-05/{lang}-order-service",
        "    newTag: v1",
        "  # shipping-consumer and notification-consumer map the same way",
        "# appended to each Deployment's environment by a JSON patch",
        *ENV[lang],
    ], "base/ is language-neutral; each overlay maps the images and appends the variables its language reads.",
        [f"The {name} overlay. The base Deployments are language-neutral: they run with a restricted security context "
         "(non-root, no privilege escalation, all capabilities dropped, RuntimeDefault seccomp, no fixed user ID), read "
         "PG_USER and PG_PASSWORD from the Secret, and point OTEL_EXPORTER_OTLP_ENDPOINT at the LGTM Service.",
         "Each overlay maps the three image names to localhost/cndp-05/<language>-<service>:v1 and appends the variables "
         "that language already reads in compose, so the application code is untouched. Kubernetes expands $(PG_PASSWORD) "
         "only if PG_PASSWORD is defined earlier in the list, which is why the credential variables sit in the base."])
    g.figure("r6", R_EB, "Images built on the host", "31-minikube-image-flow",
             "docker build on the host, minikube image load into the node; pods never pull",
             ["The cluster does not build images. Each service is built on the host with docker build, which keeps the "
              "host's BuildKit caches (a cold C++ build takes about half an hour), then copied into the node's containerd "
              "store with minikube image load.",
              "The Deployments set imagePullPolicy: Never, so a missing image fails fast with ErrImageNeverPull instead "
              "of trying a registry that does not have it. Tags are always v1; nothing uses latest."])
    g.code("r7", R_EB, "Run it", "bash · minikube", [
        "# from examples/05-event-driven/, with no other profile or container running",
        "k8s/setup-profile.sh        # create cndp-k8s; check the published ports",
        f"k8s/build-images.sh {lang:<8}# docker build, then minikube image load",
        f"k8s/deploy.sh {lang:<14}# Strimzi, Kafka, Postgres, LGTM, then the overlay",
        "RUNTIME=kubernetes BASE=http://127.0.0.1:30080 ./verify.sh",
        "",
        "# all six languages, a fresh namespace for each",
        "OUT=/tmp/cndp-k8s-matrix k8s/verify-matrix.sh",
        "",
        "# clean up: the namespace, the Strimzi release and its CRDs; then stop the profile",
        "k8s/teardown.sh --operator",
        "minikube stop -p cndp-k8s",
    ], "With RUNTIME=kubernetes, verify.sh runs its container checks through kubectl exec; the ten checks are unchanged.",
        ["The run, from the example directory. setup-profile.sh creates the profile and refuses to start while another "
         f"profile or a container is running. build-images.sh builds and loads the three {name} images, and deploy.sh "
         "installs Strimzi, then Kafka, Postgres and LGTM, then the overlay.",
         "verify.sh is the file compose uses. Its container operations go through helper functions, and "
         "RUNTIME=kubernetes swaps them: the Kafka checks run in pod cndp-dual-role-0 and the Postgres checks in "
         "cndp-postgres-0.",
         "What to show: the ten check marks and the Results line, then Grafana on 127.0.0.1:30300. Fallback: the "
         "recorded results that follow. teardown.sh never deletes the profile; minikube stop frees the memory and keeps "
         "the images."])
    g.bullets("r8", R_EB, "Recorded results", [
        "10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0).",
        R_TIMES + ".",
        "Tempo received traces from order-service, shipping-consumer and notification-consumer in every language.",
        "shipping-consumer scaled to 0: no shipment; back to 1: the group resumes from its committed offset.",
        "Stop the profile before starting compose or another cluster; the scripts refuse to run alongside them.",
    ], "Times cover the image build and load, the deploy, the checks and the namespace teardown.",
        ["The recorded run, 2026-10-11: every language passed all ten checks with a fresh namespace per language. "
         "After each run, verify-matrix.sh asked Tempo through the lgtm pod which services had sent traces, and all "
         "three services reported in every language.",
         "The scale-down check was run by hand: with the shipping consumer at zero replicas a new order produces no "
         "shipment; scaled back to one, the consumer group resumes from its last committed offset and the shipment "
         "appears. That is the event-driven contract from the Event-Driven section, observed on a cluster."
         + (" C++ stops here: OpenShift Local covers the other five languages." if cpp else "")])


def appendix_s(g: Gen):
    lang, name = g.lang, g.name
    g.divider("s0", "S", "Example 05 on OpenShift Local",
              "Operators from OLM, restricted-v2 pods, Routes and an internal registry",
              ["Appendix S runs the same three services and the same verify.sh on OpenShift Local (CRC). OpenShift is "
               "stricter than minikube in four places, and each one changes the deployment: operators come from the "
               "Operator Lifecycle Manager, pods run under a security context constraint that assigns an arbitrary "
               "user ID, traffic enters through Routes, and images come from a registry inside the cluster.",
               "The scope is the same as Appendix R: one example, one node. The language overlays are the minikube "
               "overlays, unchanged; the OpenShift directory adds only what the platform needs. Five languages run "
               "here: Spring Boot, Quarkus, .NET, Python and Go."])
    g.bullets("s1", S_EB, "What OpenShift changes", [
        "Operators come from OLM: AMQ Streams 3.2 by Subscription, a pinned CSV, Manual approval.",
        "Pods run under the restricted-v2 SCC with an arbitrary non-root user ID in group 0.",
        "Traffic enters through edge-TLS Routes on apps-crc.testing, not NodePorts.",
        "Images go to the internal registry with skopeo copy; pods pull with imagePullPolicy: Always.",
        "Kafka 4.2.0 (the AMQ Streams 3.2 bundle); Postgres from Red Hat's rhel10/postgresql-18.",
    ], "Site: Appendix S · Code: examples/05-event-driven/openshift/",
        ["The four differences from minikube, and what each one changes. AMQ Streams is the supported Red Hat build "
         "of Strimzi, installed the OpenShift way through a Subscription. Its 3.2 bundle ships broker images for Kafka "
         "4.1 and 4.2 only, so the Kafka resource is patched to 4.2.0.",
         "The Postgres image is Red Hat's, built for an assigned user ID; the schema runs from a postgresql-start hook "
         "as appuser. There is no node image store to load into, so a registry is the interface, and the pull policy is "
         "Always because the tag stays v1 across runs."])
    g.bullets("s2", S_EB, "The OpenShift Local runtime", [
        "crc 2.64.0: OpenShift 4.22.14 and Kubernetes v1.35.6 in a VM on the host (KVM).",
        "12 vCPU, 32768 MiB, 80 GB disk: the platform, Kafka, Postgres, LGTM and three services.",
        "Every oc call names --context crc-admin; no script runs oc config use-context.",
        "The kubeadmin password, tokens and the pull secret are never printed or stored.",
        "One cluster at a time: setup-crc.sh refuses while minikube or a container is running.",
    ], "CRC is stopped after use, never deleted, so the next start is quick.",
        ["OpenShift Local runs a single-node OpenShift cluster in a virtual machine managed by the crc command. crc "
         "setup makes api.crc.testing and *.apps-crc.testing resolve locally, which is what lets a Route work without "
         "a tunnel.",
         "crc start prints the kubeadmin and developer passwords; setup-crc.sh discards that output, so no password "
         "reaches a terminal, a log or a file. It records the current kubectl context first, including the case where "
         "none is set, and restores it on exit."])
    g.figure("s3", S_EB, "Topology on OpenShift Local", "32-openshift-topology",
             "The operator lives in its own namespace and manages Kafka in cndp-05; Routes carry the host traffic",
             ["The topology. cndp-amq-streams holds the Subscription and the AMQ Streams operator; cndp-05 holds the three "
              "services, Kafka 4.2.0, Postgres 18 and the LGTM stack. The operator's OperatorGroup selects all "
              "namespaces, so it manages the Kafka cluster in cndp-05 without a second OperatorGroup there.",
              "The host reaches order-service and Grafana through edge-TLS Routes and uses oc exec for the Kafka and "
              "Postgres checks."])
    g.code("s4", S_EB, "Pinning an operator with OLM", "yaml · OLM", [
        "# openshift/operators/subscription.yaml (excerpt)",
        "apiVersion: operators.coreos.com/v1alpha1",
        "kind: Subscription",
        "metadata:",
        "  name: amq-streams",
        "  namespace: cndp-amq-streams",
        "spec:",
        "  name: amq-streams",
        "  source: redhat-operators",
        "  sourceNamespace: openshift-marketplace",
        "  channel: amq-streams-3.2.x",
        "  startingCSV: amqstreams.v3.2.1-14",
        "  installPlanApproval: Manual",
    ], "deploy.sh approves only the InstallPlan for the pinned CSV; a later upgrade waits unapproved.",
        ["On minikube the Strimzi operator is a Helm release. On OpenShift an operator is a Subscription to a package "
         "in a catalog, and OLM does the install. startingCSV names the ClusterServiceVersion to install, and "
         "installPlanApproval: Manual makes OLM propose an InstallPlan and wait.",
         "deploy.sh approves only the InstallPlan that lists the pinned CSV and waits for the CSV to reach Succeeded. "
         "The channel is the minor channel amq-streams-3.2.x, not the default stable channel, so a new minor release "
         "does not change what is installed. Before installing, deploy.sh refuses to continue if it finds another "
         "project's AMQ Streams or Strimzi installation, because a cluster-wide operator would also manage its clusters."])
    g.bullets("s5", S_EB, "restricted-v2 without exceptions", [
        "The base already sets non-root, no privilege escalation, no capabilities, RuntimeDefault seccomp.",
        "No runAsUser, fsGroup or SCC binding in the overlays; nothing runs oc adm policy.",
        "Images end in a numeric USER (185 on the JVM images, 1001 on the others) and own their files as group 0.",
        "otel-lgtm 0.36.0 runs as an arbitrary UID with emptyDir volumes for /data, /tmp and /var/tempo.",
        "Every application pod reported openshift.io/scc: restricted-v2 in all five languages.",
    ], "If a future image needs root: a scoped anyuid RoleBinding for one ServiceAccount, never cluster-wide.",
        ["restricted-v2 is the default SCC for ordinary workloads: it requires runAsNonRoot, forbids privilege "
         "escalation, drops all capabilities, applies the runtime-default seccomp profile and assigns a user ID from "
         "the project's range, with group 0. The minikube base already sets that security context and never names a "
         "user ID, so the OpenShift overlays add nothing.",
         "Each Containerfile ends in a numeric non-root USER and copies files with --chown=<uid>:0 --chmod=g=u, so the "
         "assigned user ID, which is always in group 0, can read and write what the image owns. The observability "
         "image is built to run as root; run with a read-only root it needed three emptyDir mounts and "
         "GF_PLUGINS_PREINSTALL_DISABLED=true, and then ran under restricted-v2 with no exception."])
    g.figure("s6", S_EB, "Images through the internal registry", "32-openshift-image-flow",
             "skopeo pushes from the Docker image store to the internal registry; the token never touches a file",
             ["The Docker builds are the ones from Appendix R, with the same names and the same host caches; only the "
              "destination changes. docker push to the registry route would need the ingress CA trusted by the Docker "
              "daemon, a permanent root-owned change to the host. skopeo copy reads the image from the Docker daemon and "
              "takes the CA from a directory the user owns.",
              "The first push creates the ImageStream; pods pull the v1 tag with imagePullPolicy: Always."])
    g.code("s7", S_EB, "A registry push without a token on disk", "bash · skopeo", [
        'token="$(oc --context crc-admin create token builder -n cndp-05 --duration=10m)"',
        'skopeo copy --dest-cert-dir "$STATE/registry-ca" \\',
        '  --dest-authfile <(printf \'{"auths":{"%s":{"auth":"%s"}}}\' "$REGISTRY_ROUTE" \\',
        '      "$(printf \'builder:%s\' "$token" | base64 -w0)") \\',
        f'  "docker-daemon:localhost/cndp-05/{lang}-order-service:v1" \\',
        f'  "docker://$REGISTRY_ROUTE/cndp-05/{lang}-order-service:v1"',
        "unset token",
    ], "A ten-minute builder token in a shell variable, passed through a pipe: no file, no argument list.",
        ["The credential is the short-lived token of the project's builder service account, held only in a shell "
         "variable. skopeo reads credentials from an authfile, and the authfile here is a process substitution, a pipe, "
         "so no file contains the token.",
         "printf is a Bash builtin, so the token is in no process's argument list either, which is what --dest-creds and "
         "--dest-registry-token would expose to ps. skopeo login is not used because it writes an authfile to disk. "
         "build-push-images.sh creates one token per image."])
    if g.deck == "DotNet":
        g.code("s7n", S_EB, "Trace context through Kafka headers", "csharp · Confluent.Kafka", [
            "// OrderService/Program.cs (excerpt): producer span, context into the headers",
            'publish = orderSource.StartActivity("order.placed publish", ActivityKind.Producer);',
            "var message = new Message<Null, string> { Value = json, Headers = new Headers() };",
            "Propagators.DefaultTextMapPropagator.Inject(",
            "    new PropagationContext(",
            "        publish?.Context ?? Activity.Current?.Context ?? default, Baggage.Current),",
            "    message.Headers,",
            "    (headers, key, value) => headers.Add(key, Encoding.UTF8.GetBytes(value)));",
            'await producer.ProduceAsync("order.placed", message);',
            "",
            "// ShippingConsumer/Program.cs (excerpt): continue the trace from the headers",
            "var parent = Propagators.DefaultTextMapPropagator.Extract(",
            "    default,",
            "    cr.Message.Headers,",
            "    (headers, key) => headers is null",
            "        ? Array.Empty<string>()",
            "        : headers.Where(h => h.Key == key)",
            "                 .Select(h => h.GetValueBytes())",
            "                 .Where(b => b is not null)",
            "                 .Select(b => Encoding.UTF8.GetString(b!)));",
            'using var span = source.StartActivity("process_shipment", ActivityKind.Consumer,',
            "    parent.ActivityContext);",
        ], "Confluent.Kafka has no built-in tracing: the W3C trace context travels in the record headers.",
            ["The check that matters for an event-driven example is that one trace crosses the topic. Spring Boot, "
             "Quarkus, Python and Go propagate the W3C trace context in the Kafka record headers through their "
             "instrumentation. Confluent.Kafka has no built-in tracing, so the .NET order-service span and the consumer "
             "spans were three unrelated traces until the code carried the context itself.",
             "The order-service starts a producer span and injects the context into the record headers; each consumer "
             "extracts it and starts its span as a child. On compose the .NET example passes verify.sh 10 of 10, and "
             "Tempo holds one trace with all three services."])
    g.code("s8", S_EB, "Run it", "bash · OpenShift Local", [
        "# from examples/05-event-driven/, with minikube and compose stopped",
        "openshift/setup-crc.sh                 # crc start, ingress CA, registry route",
        f"openshift/build-push-images.sh {lang:<8}# docker build, then skopeo copy",
        f"openshift/deploy.sh {lang:<19}# operator, infrastructure, overlay",
        "RUNTIME=kubernetes KUBECTL=oc KUBE_CONTEXT=crc-admin KUBE_NAMESPACE=cndp-05 \\",
        "  BASE=https://order-service-cndp-05.apps-crc.testing \\",
        '  CURL_OPTS="--cacert $HOME/.local/state/cndp-05-crc/ingress-ca.crt" ./verify.sh',
        "",
        "# five languages, a fresh project for each",
        "OUT=/tmp/cndp-ocp-matrix openshift/verify-matrix.sh",
        "",
        "# remove the operator, its CRDs, the projects and the route change; then crc stop",
        "openshift/teardown.sh",
    ], "The Route's certificate is verified against the cluster's ingress CA; nothing uses curl -k.",
        ["The run. setup-crc.sh starts CRC, reads the ingress CA from the default-ingress-cert ConfigMap and enables "
         f"the registry's default route only if it is off. build-push-images.sh builds the three {name} images and "
         "copies them into the registry; deploy.sh installs the operator, the infrastructure and the overlay.",
         "verify.sh is unchanged: KUBECTL=oc and KUBE_CONTEXT=crc-admin select the cluster, and the Route's certificate "
         "is checked against the ingress CA. Plain HTTP on the Route answers with a redirect to HTTPS.",
         "What to show: the ten check marks over HTTPS, then the openshift.io/scc annotation on a pod. Fallback: the "
         "recorded results that follow. teardown.sh deletes the Kafka resources while the operator still runs, then "
         "the project, the operator and the CRDs it owns, and finally runs crc stop."])
    g.bullets("s9", S_EB, "Recorded results", [
        "10 passed, 0 failed in all five languages, every pod under restricted-v2 (2026-10-11).",
        S_TIMES + ".",
        "One trace per order crosses Kafka: order-service, shipping-consumer, notification-consumer.",
        "Plain HTTP on the Route answers 302 to HTTPS; Grafana 13.2.3 is healthy through its Route.",
        "A second teardown finds nothing to do and exits 0; CRC is stopped, not deleted.",
    ], "OpenShift Local 4.22.14 · crc 2.64.0 · AMQ Streams amqstreams.v3.2.1-14 · Kafka 4.2.0",
        ["The recorded run, 2026-10-11: each language passed verify.sh, produced a trace that Tempo returned with all "
         "three services, and had every application pod under restricted-v2. Between languages only the cndp-05 project "
         "is removed; the operator stays, so later languages skip the install.",
         "Teardown removed the operator, its CRDs, the namespaces and the registry route change, then stopped CRC. The "
         "SCC rejection of a fixed root user ID was not exercised on this run."])


def agenda(g: Gen, prs):
    key = g.deck if g.deck in AGENDA_TAIL else "default"
    s = next(x for x in prs.slides if x.slide_id == 257)
    col = [sh for sh in s.shapes if sh.has_text_frame and "Glossary of acronyms" in sh.text_frame.text]
    assert len(col) == 1
    g.ops.append({"op": "set_text", "sldId": 257, "shape_id": col[0].shape_id, "paragraphs": AGENDA_TAIL[key],
                  "cat": "new", "_why": "agenda gains Appendices R-S (C++: R)"})
    nkey = "Cpp" if g.deck == "Cpp" else "default"
    paras = list(AGENDA_NOTES[nkey])
    extra = ", plus the .NET toolkit, .NET on Linux and Blazor Server" if g.deck == "DotNet" else ""
    paras = [p.replace("{extra}", extra) for p in paras]
    g.ops.append({"op": "set_notes", "sldId": 257, "paragraphs": paras, "cat": "new"})


def main():
    (WORK / "ops-90-rs").mkdir(exist_ok=True)
    for deck in DECKS:
        name = f"Designing-Cloud-Native-APIs-{deck}"
        prs = Presentation(str(REPO / "lgtm-presentation" / f"{name}.pptx"))
        g = Gen(deck, prs)
        agenda(g, prs)
        appendix_r(g)
        if deck != "Cpp":
            appendix_s(g)
        (WORK / "ops-90-rs" / f"{name}.json").write_text(json.dumps({"ops": g.ops}, indent=1, ensure_ascii=False) + "\n")
        print(name, len(g.ops), "ops, last page", g.page, g.r)


if __name__ == "__main__":
    main()
