#!/usr/bin/env python3
"""Generate the window-types diagram for chapter 06."""
import generate_diagram as g
g.OUT = "../assets/diagrams"

g.emit("06-window-types", 880, 340,
    bands=[
        {"x": 10, "y": 10,  "w": 860, "h": 100, "fill": "#eef4fb",
         "label": "Tumbling — fixed, no overlap"},
        {"x": 10, "y": 120, "w": 860, "h": 100, "fill": "#fff8ef",
         "label": "Hopping (sliding) — fixed, overlapping"},
        {"x": 10, "y": 230, "w": 860, "h": 100, "fill": "#fafafa",
         "label": "Session — variable, gap-based"},
    ],
    nodes=[
        # Tumbling windows
        {"x": 30, "y": 45, "w": 160, "h": 50, "style": "user",
         "lines": ["Window 1", "00:00 – 05:00"]},
        {"x": 210, "y": 45, "w": 160, "h": 50, "style": "user",
         "lines": ["Window 2", "05:00 – 10:00"]},
        {"x": 390, "y": 45, "w": 160, "h": 50, "style": "user",
         "lines": ["Window 3", "10:00 – 15:00"]},
        {"x": 570, "y": 45, "w": 160, "h": 50, "style": "user",
         "lines": ["Window 4", "15:00 – 20:00"]},
        {"x": 750, "y": 50, "w": 100, "h": 40, "style": "ghost",
         "lines": ["no overlap"]},

        # Hopping windows
        {"x": 30, "y": 155, "w": 200, "h": 50, "style": "accent",
         "lines": ["Window A", "00:00 – 05:00"]},
        {"x": 110, "y": 155, "w": 200, "h": 50, "style": "accent",
         "lines": ["Window B", "01:00 – 06:00"]},
        {"x": 190, "y": 155, "w": 200, "h": 50, "style": "accent",
         "lines": ["Window C", "02:00 – 07:00"]},
        {"x": 750, "y": 160, "w": 100, "h": 40, "style": "ghost",
         "lines": ["smoothed view"]},

        # Session windows
        {"x": 30, "y": 265, "w": 120, "h": 50, "style": "box",
         "lines": ["Session 1", "3 events"]},
        {"x": 250, "y": 265, "w": 80, "h": 50, "style": "kernel",
         "lines": ["gap", "> 10 min"]},
        {"x": 410, "y": 265, "w": 200, "h": 50, "style": "box",
         "lines": ["Session 2", "7 events"]},
        {"x": 700, "y": 265, "w": 80, "h": 50, "style": "kernel",
         "lines": ["gap", "> 10 min"]},
    ],
    edges=[
        # Tumbling arrows
        {"x1": 190, "y1": 70, "x2": 210, "y2": 70},
        {"x1": 370, "y1": 70, "x2": 390, "y2": 70},
        {"x1": 550, "y1": 70, "x2": 570, "y2": 70},
        # Session arrows
        {"x1": 150, "y1": 290, "x2": 250, "y2": 290, "dashed": True},
        {"x1": 330, "y1": 290, "x2": 410, "y2": 290, "dashed": True},
        {"x1": 610, "y1": 290, "x2": 700, "y2": 290, "dashed": True},
    ],
    notes=[
        {"x": 30, "y": 330, "text": "Tumbling: one event → one window. Hopping: one event → multiple windows. Session: variable length, closed by inactivity.",
         "size": 11, "color": "#888888"},
    ],
)

print("Done — generated 06-window-types diagram")
