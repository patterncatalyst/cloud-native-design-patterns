#!/usr/bin/env python3
"""Generate the queue-worker diagram for chapter 07."""
import generate_diagram as g
g.OUT = "../assets/diagrams"

g.emit("07-queue-worker", 880, 280,
    bands=[
        {"x": 10, "y": 10, "w": 400, "h": 260, "fill": "#eef4fb",
         "label": "Request path (fast)"},
        {"x": 430, "y": 10, "w": 440, "h": 260, "fill": "#fff8ef",
         "label": "Off the request path (heavy)"},
    ],
    nodes=[
        {"x": 30, "y": 55, "w": 120, "h": 55, "style": "kernel",
         "lines": ["Client", "curl / browser"]},
        {"x": 200, "y": 55, "w": 180, "h": 55, "style": "user",
         "lines": ["order-service", "POST /orders → 201"]},
        {"x": 200, "y": 150, "w": 180, "h": 55, "style": "ink",
         "lines": ["Kafka", "order.placed topic"]},
        {"x": 460, "y": 55, "w": 180, "h": 55, "style": "accent",
         "lines": ["queue worker", "image resize / email"]},
        {"x": 460, "y": 150, "w": 180, "h": 55, "style": "box",
         "lines": ["KEDA ScaledObject", "scale on lag, to zero"]},
        {"x": 690, "y": 55, "w": 150, "h": 55, "style": "box",
         "lines": ["object store", "resized output"]},
    ],
    edges=[
        {"x1": 150, "y1": 82, "x2": 200, "y2": 82, "label": "POST"},
        {"x1": 290, "y1": 110, "x2": 290, "y2": 150, "label": "publish"},
        {"x1": 380, "y1": 177, "x2": 460, "y2": 82, "amber": True,
         "label": "consume"},
        {"x1": 550, "y1": 110, "x2": 550, "y2": 150, "dashed": True,
         "label": "scales"},
        {"x1": 640, "y1": 82, "x2": 690, "y2": 82, "label": "store"},
    ],
    notes=[
        {"x": 30, "y": 240, "text": "The HTTP handler returns 201 immediately; heavy work drains from the topic.",
         "size": 11, "color": "#888888"},
        {"x": 30, "y": 258, "text": "Kill the worker → the message waits. Restart → resumes from the last committed offset.",
         "size": 11, "color": "#888888"},
    ],
)

print("Done — generated 07-queue-worker diagram")
