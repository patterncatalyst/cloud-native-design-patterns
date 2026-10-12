#!/usr/bin/env python3
"""Generate the diagram for Appendix O: Newman as a merge gate (Figure O.5)."""
import generate_diagram as g
g.OUT = "../assets/diagrams"

g.emit("27-ci-gate", 920, 280,
    bands=[],
    nodes=[
        {"x": 30, "y": 110, "w": 120, "h": 60, "style": "box", "lines": ["Pull request"]},
        {"x": 185, "y": 110, "w": 120, "h": 60, "style": "box", "lines": ["Build image"]},
        {"x": 340, "y": 100, "w": 160, "h": 80, "style": "sub",
         "lines": ["docker compose up", "order, payment,", "inventory …"]},
        {"x": 535, "y": 110, "w": 150, "h": 60, "style": "accent",
         "lines": ["newman run", "collection"]},
        {"x": 720, "y": 110, "w": 170, "h": 60, "style": "user",
         "lines": ["gate", "pass → merge", "fail → block"]},
    ],
    edges=[
        {"x1": 150, "y1": 140, "x2": 185, "y2": 140},
        {"x1": 305, "y1": 140, "x2": 340, "y2": 140},
        {"x1": 500, "y1": 140, "x2": 535, "y2": 140},
        {"x1": 685, "y1": 140, "x2": 720, "y2": 140, "amber": True},
    ],
    notes=[
        {"x": 460, "y": 250, "anchor": "middle", "color": "#2f6db5",
         "text": "the services run on Docker Engine in CI as they do locally — no managed cloud — and a failed assertion fails the build"},
    ])

# ---- Figure O.3: one collection, six implementations -----------------------
IMPLS = ["Spring Boot", "Quarkus", ".NET", "Python", "C++", "Go"]
top = 40
mid = top + (56 * len(IMPLS) - 12) / 2   # vertical centre of the backend column
starts = [-12, -7, -2, 2, 7, 12]
g.emit("27-black-box", 920, 40 + 56 * len(IMPLS) + 70,
    bands=[],
    nodes=[
        {"x": 40, "y": mid - 40, "w": 200, "h": 80, "style": "accent",
         "lines": ["One collection", "newman run", "tests the HTTP contract"]},
        {"x": 340, "y": mid - 22, "w": 200, "h": 44, "style": "user",
         "lines": ["same HTTP API", "/orders, /payments …"]},
    ] + [
        {"x": 640, "y": top + 56 * i, "w": 240, "h": 44, "style": "box",
         "lines": [f"order-service · {name}"]} for i, name in enumerate(IMPLS)
    ],
    edges=[
        {"x1": 240, "y1": mid, "x2": 340, "y2": mid + 2},
    ] + [
        {"x1": 540, "y1": mid + starts[i], "x2": 640, "y2": top + 56 * i + 22,
         "dashed": i in (0, len(IMPLS) - 1)} for i in range(len(IMPLS))
    ],
    notes=[
        {"x": 460, "y": 40 + 56 * len(IMPLS) + 44, "anchor": "middle", "color": "#333", "bold": True,
         "text": "because Newman tests the API as a black box, one collection validates every implementation — the contract is the spec, not the code"},
    ])
