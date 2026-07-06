#!/usr/bin/env python3
"""Generate architecture SVG + Excalidraw diagrams for each runnable example."""
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
import generate_diagram as gd


def gen_01():
    gd.OUT = "../examples/01-cloud-native-principles"
    gd.emit("architecture", 520, 220,
        nodes=[
            {"x": 20, "y": 80, "w": 100, "h": 50, "lines": ["curl"], "style": "sub"},
            {"x": 190, "y": 60, "w": 150, "h": 90, "lines": ["order-service", ":8080"], "style": "box"},
            {"x": 400, "y": 30, "w": 100, "h": 40, "lines": ["/healthz"], "style": "accent"},
            {"x": 400, "y": 80, "w": 100, "h": 40, "lines": ["/readyz"], "style": "accent"},
            {"x": 400, "y": 130, "w": 100, "h": 40, "lines": ["/orders"], "style": "accent"},
            {"x": 400, "y": 180, "w": 100, "h": 30, "lines": ["Postgres"], "style": "kernel"},
        ],
        edges=[
            {"x1": 120, "y1": 105, "x2": 190, "y2": 105},
            {"x1": 340, "y1": 80, "x2": 400, "y2": 50},
            {"x1": 340, "y1": 100, "x2": 400, "y2": 100},
            {"x1": 340, "y1": 120, "x2": 400, "y2": 150},
            {"x1": 300, "y1": 150, "x2": 400, "y2": 195, "dashed": True},
        ],
        notes=[
            {"x": 190, "y": 30, "text": "env: DATABASE_URL, SERVICE_VERSION", "size": 10, "color": "#888888"},
        ],
    )


def gen_02():
    gd.OUT = "../examples/02-communications"
    gd.emit("architecture", 580, 200,
        nodes=[
            {"x": 20, "y": 70, "w": 100, "h": 50, "lines": ["curl / browser"], "style": "sub"},
            {"x": 180, "y": 40, "w": 160, "h": 120, "lines": ["order-service", "REST + GraphQL + Kafka", ":8080"], "style": "box"},
            {"x": 430, "y": 30, "w": 130, "h": 50, "lines": ["inventory", "gRPC :50051"], "style": "user"},
            {"x": 430, "y": 120, "w": 130, "h": 50, "lines": ["Kafka", "order.placed"], "style": "accent"},
        ],
        edges=[
            {"x1": 120, "y1": 95, "x2": 180, "y2": 95},
            {"x1": 340, "y1": 70, "x2": 430, "y2": 55, "label": "gRPC"},
            {"x1": 340, "y1": 130, "x2": 430, "y2": 145, "label": "async", "dashed": True},
        ],
    )


def gen_03():
    gd.OUT = "../examples/03-composition"
    gd.emit("architecture", 600, 220,
        nodes=[
            {"x": 20, "y": 80, "w": 100, "h": 50, "lines": ["GraphQL client"], "style": "sub"},
            {"x": 180, "y": 50, "w": 140, "h": 110, "lines": ["gateway", "GraphQL schema", ":8080"], "style": "box"},
            {"x": 420, "y": 30, "w": 140, "h": 50, "lines": ["order-api", "REST :8081"], "style": "user"},
            {"x": 420, "y": 130, "w": 140, "h": 50, "lines": ["inventory", "gRPC :50051"], "style": "user"},
            {"x": 420, "y": 200, "w": 100, "h": 30, "lines": ["Postgres"], "style": "kernel"},
        ],
        edges=[
            {"x1": 120, "y1": 105, "x2": 180, "y2": 105},
            {"x1": 320, "y1": 75, "x2": 420, "y2": 55, "label": "REST"},
            {"x1": 320, "y1": 130, "x2": 420, "y2": 155, "label": "gRPC"},
            {"x1": 560, "y1": 80, "x2": 560, "y2": 200, "dashed": True},
        ],
        notes=[
            {"x": 430, "y": 100, "text": "DataLoader batches N+1 → 1", "size": 10, "color": "#888888"},
        ],
    )


def gen_04():
    gd.OUT = "../examples/04-data"
    gd.emit("architecture", 500, 300,
        nodes=[
            {"x": 20, "y": 30, "w": 100, "h": 50, "lines": ["curl"], "style": "sub"},
            {"x": 180, "y": 20, "w": 150, "h": 70, "lines": ["order-service", ":8080"], "style": "box"},
            {"x": 180, "y": 120, "w": 150, "h": 60, "lines": ["Postgres", "orders + outbox"], "style": "kernel"},
            {"x": 180, "y": 210, "w": 150, "h": 50, "lines": ["Debezium Connect", ":8083"], "style": "accent"},
            {"x": 180, "y": 280, "w": 150, "h": 40, "lines": ["Kafka (order.placed)"], "style": "accent"},
        ],
        edges=[
            {"x1": 120, "y1": 55, "x2": 180, "y2": 55},
            {"x1": 255, "y1": 90, "x2": 255, "y2": 120, "label": "BEGIN/COMMIT"},
            {"x1": 255, "y1": 180, "x2": 255, "y2": 210, "label": "WAL (logical)", "amber": True},
            {"x1": 255, "y1": 260, "x2": 255, "y2": 280},
        ],
        notes=[
            {"x": 370, "y": 155, "text": "single transaction", "size": 10, "color": "#888888"},
        ],
    )


def gen_05():
    gd.OUT = "../examples/05-event-driven"
    gd.emit("architecture", 560, 300,
        nodes=[
            {"x": 20, "y": 30, "w": 80, "h": 50, "lines": ["curl"], "style": "sub"},
            {"x": 160, "y": 20, "w": 150, "h": 70, "lines": ["order-service", ":8080"], "style": "box"},
            {"x": 370, "y": 30, "w": 140, "h": 50, "lines": ["Postgres", "orders"], "style": "kernel"},
            {"x": 190, "y": 130, "w": 130, "h": 50, "lines": ["Kafka", "order.placed"], "style": "accent"},
            {"x": 60, "y": 220, "w": 170, "h": 50, "lines": ["shipping-consumer", "shipping-group"], "style": "user"},
            {"x": 320, "y": 220, "w": 180, "h": 50, "lines": ["notification-consumer", "notification-group"], "style": "user"},
            {"x": 60, "y": 290, "w": 140, "h": 30, "lines": ["Postgres (shipments)"], "style": "kernel"},
            {"x": 340, "y": 290, "w": 160, "h": 30, "lines": ["Postgres (notifications)"], "style": "kernel"},
        ],
        edges=[
            {"x1": 100, "y1": 55, "x2": 160, "y2": 55},
            {"x1": 310, "y1": 55, "x2": 370, "y2": 55},
            {"x1": 235, "y1": 90, "x2": 255, "y2": 130},
            {"x1": 210, "y1": 180, "x2": 145, "y2": 220},
            {"x1": 300, "y1": 180, "x2": 410, "y2": 220},
            {"x1": 145, "y1": 270, "x2": 130, "y2": 290},
            {"x1": 410, "y1": 270, "x2": 420, "y2": 290},
        ],
        notes=[
            {"x": 140, "y": 205, "text": "fan-out: two independent consumer groups", "size": 10, "color": "#888888"},
        ],
    )


def gen_06():
    gd.OUT = "../examples/06-stream-processing"
    gd.emit("architecture", 460, 340,
        nodes=[
            {"x": 20, "y": 30, "w": 80, "h": 50, "lines": ["curl"], "style": "sub"},
            {"x": 160, "y": 20, "w": 150, "h": 70, "lines": ["order-service", ":8080"], "style": "box"},
            {"x": 370, "y": 30, "w": 70, "h": 50, "lines": ["Postgres"], "style": "kernel"},
            {"x": 160, "y": 130, "w": 150, "h": 40, "lines": ["Kafka (order.placed)"], "style": "accent"},
            {"x": 140, "y": 200, "w": 180, "h": 60, "lines": ["stream-processor", "group by merchant", "tumbling 10s windows"], "style": "box"},
            {"x": 120, "y": 290, "w": 220, "h": 40, "lines": ["Kafka (revenue.by-merchant)"], "style": "accent"},
        ],
        edges=[
            {"x1": 100, "y1": 55, "x2": 160, "y2": 55},
            {"x1": 310, "y1": 55, "x2": 370, "y2": 55},
            {"x1": 235, "y1": 90, "x2": 235, "y2": 130},
            {"x1": 235, "y1": 170, "x2": 235, "y2": 200},
            {"x1": 235, "y1": 260, "x2": 235, "y2": 290, "label": "derived stream", "amber": True},
        ],
    )


def gen_09():
    gd.OUT = "../examples/09-api-registry"
    gd.emit("architecture", 500, 240,
        nodes=[
            {"x": 20, "y": 80, "w": 80, "h": 50, "lines": ["curl"], "style": "sub"},
            {"x": 180, "y": 40, "w": 180, "h": 120, "lines": ["Apicurio Registry", "v3 API :8081"], "style": "box"},
            {"x": 410, "y": 40, "w": 80, "h": 40, "lines": ["register"], "style": "accent"},
            {"x": 410, "y": 90, "w": 80, "h": 40, "lines": ["rules"], "style": "accent"},
            {"x": 410, "y": 140, "w": 80, "h": 40, "lines": ["versions"], "style": "accent"},
        ],
        edges=[
            {"x1": 100, "y1": 105, "x2": 180, "y2": 100},
            {"x1": 360, "y1": 60, "x2": 410, "y2": 60},
            {"x1": 360, "y1": 100, "x2": 410, "y2": 110},
            {"x1": 360, "y1": 140, "x2": 410, "y2": 160},
        ],
        notes=[
            {"x": 420, "y": 195, "text": "breaking → 409", "size": 10, "color": "#b8650a", "bold": True},
            {"x": 420, "y": 210, "text": "additive → 200", "size": 10, "color": "#555555"},
        ],
    )


def gen_11():
    gd.OUT = "../examples/11-observability"
    gd.emit("architecture", 600, 320,
        bands=[
            {"x": 10, "y": 230, "w": 580, "h": 80, "label": "LGTM Stack", "fill": "#f4f4f4"},
        ],
        nodes=[
            {"x": 20, "y": 30, "w": 80, "h": 50, "lines": ["curl"], "style": "sub"},
            {"x": 160, "y": 20, "w": 160, "h": 70, "lines": ["order-service", "REST + metrics :8080"], "style": "box"},
            {"x": 420, "y": 20, "w": 140, "h": 50, "lines": ["inventory", "gRPC :50051"], "style": "user"},
            {"x": 160, "y": 130, "w": 130, "h": 40, "lines": ["Kafka (order.placed)"], "style": "accent"},
            {"x": 370, "y": 130, "w": 180, "h": 50, "lines": ["notification-consumer", "extracts trace context"], "style": "user"},
            {"x": 30, "y": 250, "w": 80, "h": 40, "lines": ["Grafana"], "style": "box"},
            {"x": 140, "y": 250, "w": 80, "h": 40, "lines": ["Tempo"], "style": "box"},
            {"x": 250, "y": 250, "w": 80, "h": 40, "lines": ["Loki"], "style": "box"},
            {"x": 360, "y": 250, "w": 100, "h": 40, "lines": ["Prometheus"], "style": "box"},
            {"x": 490, "y": 250, "w": 80, "h": 40, "lines": ["OTel Coll."], "style": "accent"},
        ],
        edges=[
            {"x1": 100, "y1": 55, "x2": 160, "y2": 55},
            {"x1": 320, "y1": 45, "x2": 420, "y2": 45, "label": "gRPC"},
            {"x1": 240, "y1": 90, "x2": 225, "y2": 130, "label": "async", "dashed": True},
            {"x1": 290, "y1": 150, "x2": 370, "y2": 155},
            {"x1": 300, "y1": 200, "x2": 530, "y2": 250, "label": "OTLP", "amber": True},
        ],
        notes=[
            {"x": 180, "y": 200, "text": "W3C traceparent propagated across all hops", "size": 10, "color": "#888888"},
        ],
    )


def gen_12():
    gd.OUT = "../examples/12-security"
    gd.emit("architecture", 500, 280,
        nodes=[
            {"x": 20, "y": 30, "w": 80, "h": 50, "lines": ["Client"], "style": "sub"},
            {"x": 180, "y": 20, "w": 180, "h": 120, "lines": ["order-service", "trust_sidecar middleware", "per-tenant bulkhead", "valet key mint/verify"], "style": "box"},
            {"x": 420, "y": 60, "w": 60, "h": 40, "lines": ["store"], "style": "kernel"},
            {"x": 50, "y": 180, "w": 110, "h": 50, "lines": ["conftest"], "style": "sub"},
            {"x": 230, "y": 180, "w": 170, "h": 50, "lines": ["policy/*.rego", "signed images, non-root"], "style": "accent"},
        ],
        edges=[
            {"x1": 100, "y1": 55, "x2": 180, "y2": 55},
            {"x1": 360, "y1": 80, "x2": 420, "y2": 80},
            {"x1": 160, "y1": 205, "x2": 230, "y2": 205},
        ],
        notes=[
            {"x": 20, "y": 100, "text": "X-Forwarded-Client-Cert → 201", "size": 10, "color": "#555555"},
            {"x": 20, "y": 115, "text": "(no header) → 403", "size": 10, "color": "#b8650a"},
        ],
    )


def gen_16():
    gd.OUT = "../examples/16-websockets"
    gd.emit("architecture", 500, 240,
        nodes=[
            {"x": 20, "y": 30, "w": 120, "h": 50, "lines": ["WS clients"], "style": "sub"},
            {"x": 60, "y": 120, "w": 130, "h": 50, "lines": ["ws-pod-1", ":8081"], "style": "box"},
            {"x": 280, "y": 120, "w": 130, "h": 50, "lines": ["ws-pod-2", ":8082"], "style": "box"},
            {"x": 170, "y": 200, "w": 140, "h": 40, "lines": ["Redis pub/sub", "ws:broadcast"], "style": "accent"},
        ],
        edges=[
            {"x1": 60, "y1": 80, "x2": 100, "y2": 120, "label": "WS"},
            {"x1": 120, "y1": 80, "x2": 340, "y2": 120, "label": "WS"},
            {"x1": 125, "y1": 170, "x2": 210, "y2": 200, "bidir": True},
            {"x1": 345, "y1": 170, "x2": 270, "y2": 200, "bidir": True},
        ],
        notes=[
            {"x": 160, "y": 20, "text": "cross-pod delivery via backplane", "size": 10, "color": "#888888"},
        ],
    )


def gen_17():
    gd.OUT = "../examples/17-sagas"
    gd.emit("architecture", 520, 280,
        nodes=[
            {"x": 20, "y": 30, "w": 80, "h": 50, "lines": ["curl"], "style": "sub"},
            {"x": 160, "y": 20, "w": 170, "h": 70, "lines": ["saga-orchestrator", ":8080"], "style": "box"},
            {"x": 390, "y": 30, "w": 110, "h": 50, "lines": ["Postgres", "sagas + log"], "style": "kernel"},
            {"x": 80, "y": 130, "w": 130, "h": 40, "lines": ["charge_payment"], "style": "accent"},
            {"x": 80, "y": 180, "w": 130, "h": 40, "lines": ["reserve_stock"], "style": "accent"},
            {"x": 80, "y": 230, "w": 130, "h": 40, "lines": ["book_shipping"], "style": "accent"},
            {"x": 300, "y": 180, "w": 130, "h": 40, "lines": ["release_stock"], "style": "ghost"},
            {"x": 300, "y": 230, "w": 130, "h": 40, "lines": ["refund_payment"], "style": "ghost"},
        ],
        edges=[
            {"x1": 100, "y1": 55, "x2": 160, "y2": 55},
            {"x1": 330, "y1": 55, "x2": 390, "y2": 55},
            {"x1": 200, "y1": 90, "x2": 145, "y2": 130},
            {"x1": 145, "y1": 170, "x2": 145, "y2": 180},
            {"x1": 145, "y1": 220, "x2": 145, "y2": 230},
            {"x1": 210, "y1": 250, "x2": 300, "y2": 200, "label": "on failure", "amber": True, "dashed": True},
            {"x1": 365, "y1": 220, "x2": 365, "y2": 230},
        ],
        notes=[
            {"x": 300, "y": 165, "text": "compensation (reverse order)", "size": 10, "color": "#b8650a"},
        ],
    )


def gen_18():
    gd.OUT = "../examples/18-errors"
    gd.emit("architecture", 540, 220,
        nodes=[
            {"x": 20, "y": 60, "w": 80, "h": 50, "lines": ["curl"], "style": "sub"},
            {"x": 160, "y": 40, "w": 170, "h": 90, "lines": ["order-service", "REST :8080", "problem+json errors"], "style": "box"},
            {"x": 400, "y": 50, "w": 120, "h": 70, "lines": ["inventory", "gRPC", ":50051"], "style": "user"},
        ],
        edges=[
            {"x1": 100, "y1": 85, "x2": 160, "y2": 85},
            {"x1": 330, "y1": 75, "x2": 400, "y2": 75, "label": "gRPC"},
        ],
        notes=[
            {"x": 160, "y": 160, "text": "422 → VALIDATION_ERROR", "size": 10, "color": "#555555"},
            {"x": 160, "y": 175, "text": "409 → STOCK_UNAVAILABLE (FAILED_PRECONDITION)", "size": 10, "color": "#555555"},
            {"x": 160, "y": 190, "text": "503 → INVENTORY_UNAVAILABLE + Retry-After", "size": 10, "color": "#b8650a"},
        ],
    )


def gen_19():
    gd.OUT = "../examples/19-ddd-hexagonal"
    gd.emit("architecture", 520, 280,
        bands=[
            {"x": 130, "y": 20, "w": 260, "h": 100, "label": "domain/ (pure, no framework imports)", "fill": "#eef4fb"},
        ],
        nodes=[
            {"x": 160, "y": 45, "w": 90, "h": 40, "lines": ["models"], "style": "user"},
            {"x": 260, "y": 45, "w": 100, "h": 40, "lines": ["ports", "(Protocol)"], "style": "user"},
            {"x": 30, "y": 160, "w": 140, "h": 50, "lines": ["REST adapter", "driving (HTTP)"], "style": "box"},
            {"x": 30, "y": 230, "w": 140, "h": 40, "lines": ["CLI adapter", "driving (CLI)"], "style": "box"},
            {"x": 340, "y": 160, "w": 150, "h": 50, "lines": ["postgres_repo", "driven (outbound)"], "style": "kernel"},
            {"x": 340, "y": 230, "w": 150, "h": 40, "lines": ["log_publisher", "driven (outbound)"], "style": "kernel"},
            {"x": 190, "y": 140, "w": 130, "h": 40, "lines": ["PlaceOrder", "use case"], "style": "accent"},
        ],
        edges=[
            {"x1": 170, "y1": 185, "x2": 190, "y2": 165},
            {"x1": 170, "y1": 250, "x2": 190, "y2": 175},
            {"x1": 320, "y1": 160, "x2": 340, "y2": 175},
            {"x1": 320, "y1": 165, "x2": 340, "y2": 245, "dashed": True},
        ],
    )


def gen_21():
    gd.OUT = "../examples/21-graceful-shutdown"
    gd.emit("architecture", 460, 250,
        nodes=[
            {"x": 20, "y": 30, "w": 80, "h": 40, "lines": ["SIGTERM"], "style": "accent"},
            {"x": 160, "y": 20, "w": 170, "h": 80, "lines": ["order-service", ":8080"], "style": "box"},
            {"x": 390, "y": 30, "w": 60, "h": 50, "lines": ["Postgres"], "style": "kernel"},
            {"x": 160, "y": 130, "w": 170, "h": 40, "lines": ["/readyz → 503"], "style": "accent"},
            {"x": 160, "y": 180, "w": 170, "h": 40, "lines": ["drain in-flight"], "style": "sub"},
            {"x": 160, "y": 230, "w": 170, "h": 30, "lines": ["close DB pool, exit"], "style": "sub"},
        ],
        edges=[
            {"x1": 100, "y1": 50, "x2": 160, "y2": 50, "amber": True},
            {"x1": 330, "y1": 55, "x2": 390, "y2": 55},
            {"x1": 245, "y1": 100, "x2": 245, "y2": 130},
            {"x1": 245, "y1": 170, "x2": 245, "y2": 180},
            {"x1": 245, "y1": 220, "x2": 245, "y2": 230},
        ],
        notes=[
            {"x": 30, "y": 85, "text": "stops new traffic", "size": 10, "color": "#888888"},
        ],
    )


def gen_22():
    gd.OUT = "../examples/22-l7-routing"
    gd.emit("architecture", 560, 300,
        bands=[
            {"x": 10, "y": 10, "w": 540, "h": 150, "label": "Mesh-level routing (Envoy)", "fill": "#fafafa"},
            {"x": 10, "y": 180, "w": 540, "h": 110, "label": "In-app rule routing", "fill": "#f4f4f4"},
        ],
        nodes=[
            {"x": 30, "y": 50, "w": 100, "h": 50, "lines": ["Client"], "style": "sub"},
            {"x": 200, "y": 40, "w": 140, "h": 60, "lines": ["Envoy proxy", "L7 router :8080"], "style": "box"},
            {"x": 410, "y": 30, "w": 120, "h": 40, "lines": ["order-v1"], "style": "user"},
            {"x": 410, "y": 90, "w": 120, "h": 40, "lines": ["order-v2"], "style": "accent"},
            {"x": 30, "y": 210, "w": 100, "h": 50, "lines": ["Client"], "style": "sub"},
            {"x": 200, "y": 200, "w": 160, "h": 70, "lines": ["router-service", "rules engine :8090"], "style": "box"},
        ],
        edges=[
            {"x1": 130, "y1": 75, "x2": 200, "y2": 70},
            {"x1": 340, "y1": 55, "x2": 410, "y2": 50, "label": "90%"},
            {"x1": 340, "y1": 85, "x2": 410, "y2": 110, "label": "10%", "amber": True},
            {"x1": 130, "y1": 235, "x2": 200, "y2": 235},
        ],
        notes=[
            {"x": 420, "y": 145, "text": "x-route-to: v2 → override", "size": 10, "color": "#555555"},
            {"x": 380, "y": 230, "text": "VIP → priority topic", "size": 10, "color": "#b8650a"},
            {"x": 380, "y": 245, "text": "default → standard", "size": 10, "color": "#555555"},
        ],
    )


def gen_24():
    gd.OUT = "../examples/24-monolith-to-microservices"
    gd.emit("architecture", 560, 300,
        bands=[
            {"x": 10, "y": 10, "w": 540, "h": 130, "label": "Content-based routing (strangler fig)", "fill": "#fafafa"},
            {"x": 10, "y": 160, "w": 540, "h": 130, "label": "Decorating collaborator", "fill": "#f4f4f4"},
        ],
        nodes=[
            {"x": 30, "y": 50, "w": 80, "h": 50, "lines": ["Client"], "style": "sub"},
            {"x": 180, "y": 40, "w": 120, "h": 60, "lines": ["Router", ":8080"], "style": "box"},
            {"x": 380, "y": 30, "w": 120, "h": 40, "lines": ["monolith"], "style": "kernel"},
            {"x": 380, "y": 80, "w": 120, "h": 40, "lines": ["new-service"], "style": "accent"},
            {"x": 30, "y": 200, "w": 80, "h": 50, "lines": ["Client"], "style": "sub"},
            {"x": 180, "y": 190, "w": 120, "h": 60, "lines": ["Decorator", ":8091"], "style": "box"},
            {"x": 380, "y": 200, "w": 120, "h": 40, "lines": ["Legacy"], "style": "kernel"},
            {"x": 380, "y": 260, "w": 60, "h": 30, "lines": ["Redis"], "style": "accent"},
            {"x": 460, "y": 260, "w": 80, "h": 30, "lines": ["Kafka"], "style": "accent"},
        ],
        edges=[
            {"x1": 110, "y1": 75, "x2": 180, "y2": 70},
            {"x1": 300, "y1": 55, "x2": 380, "y2": 50},
            {"x1": 300, "y1": 85, "x2": 380, "y2": 100, "amber": True},
            {"x1": 110, "y1": 225, "x2": 180, "y2": 220},
            {"x1": 300, "y1": 220, "x2": 380, "y2": 220},
            {"x1": 260, "y1": 250, "x2": 380, "y2": 275, "dashed": True},
            {"x1": 260, "y1": 250, "x2": 460, "y2": 275, "dashed": True},
        ],
        notes=[
            {"x": 310, "y": 130, "text": "PUT /rules: flip routing, flip back", "size": 10, "color": "#888888"},
        ],
    )


def gen_25():
    gd.OUT = "../examples/25-caching"
    gd.emit("architecture", 460, 250,
        nodes=[
            {"x": 20, "y": 30, "w": 80, "h": 50, "lines": ["Client"], "style": "sub"},
            {"x": 160, "y": 20, "w": 150, "h": 70, "lines": ["cache-service", ":8080"], "style": "box"},
            {"x": 380, "y": 20, "w": 60, "h": 40, "lines": ["Redis"], "style": "accent"},
            {"x": 380, "y": 80, "w": 80, "h": 40, "lines": ["Postgres"], "style": "kernel"},
            {"x": 160, "y": 140, "w": 130, "h": 40, "lines": ["flusher", "write-back → DB"], "style": "sub"},
            {"x": 160, "y": 200, "w": 140, "h": 40, "lines": ["refresher", "hot keys → cache"], "style": "sub"},
        ],
        edges=[
            {"x1": 100, "y1": 55, "x2": 160, "y2": 55},
            {"x1": 310, "y1": 40, "x2": 380, "y2": 40, "label": "cache tier"},
            {"x1": 310, "y1": 80, "x2": 380, "y2": 100, "label": "source of truth"},
            {"x1": 245, "y1": 90, "x2": 245, "y2": 140, "dashed": True},
            {"x1": 290, "y1": 160, "x2": 380, "y2": 100, "dashed": True},
            {"x1": 300, "y1": 220, "x2": 380, "y2": 40, "dashed": True},
        ],
    )


def gen_26():
    gd.OUT = "../examples/26-failure-modes"
    gd.emit("architecture", 520, 230,
        nodes=[
            {"x": 20, "y": 30, "w": 80, "h": 50, "lines": ["Client"], "style": "sub"},
            {"x": 160, "y": 20, "w": 190, "h": 90, "lines": ["edge-service", "timeout · retry · breaker", "bulkhead · deadline", ":8080"], "style": "box"},
            {"x": 410, "y": 30, "w": 100, "h": 70, "lines": ["backend", ":8081"], "style": "user"},
        ],
        edges=[
            {"x1": 100, "y1": 55, "x2": 160, "y2": 55},
            {"x1": 350, "y1": 65, "x2": 410, "y2": 65},
        ],
        notes=[
            {"x": 410, "y": 130, "text": "/mode controls:", "size": 10, "color": "#555555"},
            {"x": 410, "y": 145, "text": "healthy | slow | failing | flaky", "size": 10, "color": "#888888"},
            {"x": 160, "y": 140, "text": "breaker trips → fallback", "size": 10, "color": "#b8650a"},
            {"x": 160, "y": 155, "text": "deadline exhausted → reject", "size": 10, "color": "#b8650a"},
        ],
    )


def gen_27():
    gd.OUT = "../examples/27-feature-flags"
    gd.emit("architecture", 480, 200,
        nodes=[
            {"x": 20, "y": 50, "w": 80, "h": 50, "lines": ["Client"], "style": "sub"},
            {"x": 160, "y": 30, "w": 180, "h": 80, "lines": ["flag-service", "OpenFeature SDK", ":8080"], "style": "box"},
            {"x": 400, "y": 40, "w": 70, "h": 60, "lines": ["flagd", "gRPC", ":8013"], "style": "accent"},
            {"x": 400, "y": 140, "w": 70, "h": 40, "lines": ["flags.json"], "style": "kernel"},
        ],
        edges=[
            {"x1": 100, "y1": 75, "x2": 160, "y2": 70},
            {"x1": 340, "y1": 70, "x2": 400, "y2": 70, "label": "gRPC"},
            {"x1": 435, "y1": 100, "x2": 435, "y2": 140, "dashed": True},
        ],
        notes=[
            {"x": 160, "y": 140, "text": "flagd down → coded defaults", "size": 10, "color": "#b8650a"},
            {"x": 160, "y": 155, "text": "service keeps serving 200s", "size": 10, "color": "#888888"},
        ],
    )


def gen_28():
    gd.OUT = "../examples/28-newman"
    gd.emit("architecture", 500, 220,
        nodes=[
            {"x": 20, "y": 30, "w": 100, "h": 50, "lines": ["Newman CLI"], "style": "sub"},
            {"x": 20, "y": 110, "w": 200, "h": 90, "lines": ["orders.postman_collection", "CRUD · validation · flow", "JUnit XML reporter"], "style": "box"},
            {"x": 310, "y": 60, "w": 150, "h": 60, "lines": ["order-service", ":8080"], "style": "user"},
            {"x": 310, "y": 150, "w": 100, "h": 40, "lines": ["Postgres"], "style": "kernel"},
        ],
        edges=[
            {"x1": 70, "y1": 80, "x2": 70, "y2": 110},
            {"x1": 220, "y1": 140, "x2": 310, "y2": 90},
            {"x1": 385, "y1": 120, "x2": 385, "y2": 150, "dashed": True},
        ],
        notes=[
            {"x": 310, "y": 40, "text": "black-box testing: any backend", "size": 10, "color": "#888888"},
        ],
    )


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    gen_01(); gen_02(); gen_03(); gen_04(); gen_05()
    gen_06(); gen_09(); gen_11(); gen_12(); gen_16()
    gen_17(); gen_18(); gen_19(); gen_21(); gen_22()
    gen_24(); gen_25(); gen_26(); gen_27(); gen_28()
    print("Done — 20 diagrams generated.")
