#!/usr/bin/env python3
"""Generate diagrams for Appendix R: Running Example 05 on minikube."""
import generate_diagram as g
g.OUT = "../assets/diagrams"

# ── Figure R.1 — cluster topology and host access ───────────────────────
g.emit("31-minikube-topology", 880, 420,
    bands=[
        {"x": 10, "y": 10, "w": 200, "h": 400, "fill": "#eef4fb",
         "label": "Host (Docker Engine)"},
        {"x": 230, "y": 10, "w": 640, "h": 400, "fill": "#f7f7f7",
         "label": "Node container cndp-k8s (containerd, Kubernetes v1.36.5)"},
        {"x": 250, "y": 40, "w": 160, "h": 360, "fill": "#ffffff",
         "label": "namespace strimzi"},
        {"x": 430, "y": 40, "w": 425, "h": 360, "fill": "#fff8ef",
         "label": "namespace cndp-05"},
    ],
    nodes=[
        {"x": 25, "y": 60, "w": 170, "h": 55, "style": "user",
         "lines": ["curl, verify.sh", "127.0.0.1:30080"]},
        {"x": 25, "y": 135, "w": 170, "h": 55, "style": "user",
         "lines": ["Browser", "127.0.0.1:30300"]},
        {"x": 25, "y": 210, "w": 170, "h": 55, "style": "kernel",
         "lines": ["kubectl --context", "cndp-k8s"]},
        {"x": 25, "y": 285, "w": 170, "h": 55, "style": "ghost",
         "lines": ["Other profiles", "stopped"]},
        {"x": 265, "y": 310, "w": 130, "h": 60, "style": "accent",
         "lines": ["Strimzi operator", "Helm chart 1.2.0"]},
        {"x": 450, "y": 80, "w": 190, "h": 55, "style": "ink",
         "lines": ["order-service", "NodePort 30080"]},
        {"x": 660, "y": 80, "w": 180, "h": 55, "style": "box",
         "lines": ["shipping-consumer", "notification-consumer"]},
        {"x": 450, "y": 180, "w": 190, "h": 60, "style": "accent",
         "lines": ["Kafka cndp (KRaft)", "cndp-kafka-bootstrap:9092"]},
        {"x": 660, "y": 180, "w": 180, "h": 60, "style": "accent",
         "lines": ["Postgres 18", "cndp-postgres-rw:5432"]},
        {"x": 450, "y": 285, "w": 190, "h": 60, "style": "kernel",
         "lines": ["LGTM (otel-lgtm)", "lgtm:4318, Grafana 30300"]},
        {"x": 660, "y": 285, "w": 180, "h": 60, "style": "sub",
         "lines": ["Secret cndp-postgres-app", "PG_USER, PG_PASSWORD"]},
    ],
    edges=[
        {"x1": 195, "y1": 87, "x2": 450, "y2": 107, "amber": True},
        {"x1": 195, "y1": 162, "x2": 450, "y2": 315, "amber": True},
        {"x1": 195, "y1": 237, "x2": 450, "y2": 215, "dashed": True, "label": "exec", "lx": 0},
        {"x1": 395, "y1": 335, "x2": 450, "y2": 225, "dashed": True, "label": "manages", "lx": -4},
        {"x1": 545, "y1": 135, "x2": 545, "y2": 180, "label": "produce"},
        {"x1": 750, "y1": 135, "x2": 750, "y2": 180, "label": "insert"},
        {"x1": 640, "y1": 208, "x2": 660, "y2": 208},
    ],
    notes=[
        {"x": 25, "y": 395, "text": "Both ports are published on 127.0.0.1 when the profile is created. No port-forward, tunnel or minikube service.",
         "size": 11, "color": "#888888"},
    ],
)

# ── Figure R.2 — image flow ─────────────────────────────────────────────
g.emit("31-minikube-image-flow", 880, 300,
    bands=[
        {"x": 10, "y": 10, "w": 540, "h": 190, "fill": "#eef4fb",
         "label": "Host"},
        {"x": 570, "y": 10, "w": 300, "h": 190, "fill": "#fff8ef",
         "label": "Node container cndp-k8s"},
    ],
    nodes=[
        {"x": 30, "y": 55, "w": 150, "h": 55, "style": "box",
         "lines": ["Containerfile", "per language, per service"]},
        {"x": 210, "y": 55, "w": 150, "h": 55, "style": "accent",
         "lines": ["docker build", "host BuildKit cache"]},
        {"x": 390, "y": 55, "w": 140, "h": 55, "style": "user",
         "lines": ["Docker image store", "localhost/cndp-05/..."]},
        {"x": 590, "y": 55, "w": 130, "h": 55, "style": "kernel",
         "lines": ["containerd", "same image name"]},
        {"x": 740, "y": 55, "w": 110, "h": 55, "style": "ink",
         "lines": ["Pod", "pullPolicy: Never"]},
        {"x": 390, "y": 140, "w": 140, "h": 40, "style": "sub",
         "lines": ["tag :v1, no :latest"]},
        {"x": 30, "y": 230, "w": 820, "h": 45, "style": "ghost",
         "lines": ["Rejected: minikube image build (discards the host caches), a registry addon (extra moving part)"]},
    ],
    edges=[
        {"x1": 180, "y1": 82, "x2": 210, "y2": 82},
        {"x1": 360, "y1": 82, "x2": 390, "y2": 82},
        {"x1": 530, "y1": 82, "x2": 590, "y2": 82, "amber": True, "label": "image load", "lx": 0, "ly": -14},
        {"x1": 720, "y1": 82, "x2": 740, "y2": 82},
    ],
    notes=[],
)
print("Done — generated 2 diagrams for Appendix R")
