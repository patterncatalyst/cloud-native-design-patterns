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
         "text": "the services run on Docker Engine in CI exactly as on a laptop — no managed cloud — and a failed assertion fails the build"},
    ])
