#!/usr/bin/env python3
"""Generate diagrams for Appendix Q: Blazor Server + SignalR."""
import generate_diagram as g
g.OUT = "../assets/diagrams"

# ── Figure Q.1 — Blazor Server circuit ──────────────────────────────────
g.emit("30-blazor-circuit", 880, 340,
    bands=[
        {"x": 10, "y": 10, "w": 330, "h": 320, "fill": "#eef4fb",
         "label": "Browser"},
        {"x": 360, "y": 10, "w": 510, "h": 320, "fill": "#fff8ef",
         "label": "ASP.NET Core server"},
    ],
    nodes=[
        # Browser side
        {"x": 30, "y": 55, "w": 140, "h": 55, "style": "user",
         "lines": ["Blazor JS", "runtime (tiny)"]},
        {"x": 190, "y": 55, "w": 130, "h": 55, "style": "box",
         "lines": ["DOM", "rendered HTML"]},
        {"x": 30, "y": 150, "w": 290, "h": 50, "style": "accent",
         "lines": ["SignalR circuit (WebSocket)", "persistent, one per client"]},
        {"x": 30, "y": 240, "w": 140, "h": 55, "style": "kernel",
         "lines": ["User events", "click, submit, input"]},
        # Server side
        {"x": 380, "y": 55, "w": 160, "h": 55, "style": "ink",
         "lines": ["Component tree", "C# Razor components"]},
        {"x": 570, "y": 55, "w": 140, "h": 55, "style": "accent",
         "lines": ["Render diff", "compute delta"]},
        {"x": 730, "y": 55, "w": 120, "h": 55, "style": "box",
         "lines": ["DOM diff", "minimal patch"]},
        {"x": 380, "y": 150, "w": 160, "h": 55, "style": "user",
         "lines": ["SignalR Hub", "OrderHub.cs"]},
        {"x": 570, "y": 150, "w": 140, "h": 55, "style": "box",
         "lines": ["DI services", "DbContext, APIs"]},
        {"x": 380, "y": 240, "w": 160, "h": 55, "style": "kernel",
         "lines": ["Redis backplane", "scale-out pub/sub"]},
        {"x": 570, "y": 240, "w": 290, "h": 55, "style": "ghost",
         "lines": ["Other Blazor pods subscribe to", "the same Redis channels"]},
    ],
    edges=[
        {"x1": 170, "y1": 82, "x2": 190, "y2": 82, "label": "apply"},
        # Circuit down (events)
        {"x1": 170, "y1": 268, "x2": 170, "y2": 200, "amber": True,
         "label": "events ↑"},
        # Circuit up (diffs)
        {"x1": 260, "y1": 200, "x2": 260, "y2": 82, "amber": True,
         "label": "diffs ↓", "lx": 10},
        # Server: circuit to hub
        {"x1": 360, "y1": 177, "x2": 380, "y2": 177},
        # Server: hub to component tree
        {"x1": 460, "y1": 150, "x2": 460, "y2": 110},
        # Render flow
        {"x1": 540, "y1": 82, "x2": 570, "y2": 82},
        {"x1": 710, "y1": 82, "x2": 730, "y2": 82},
        # Hub to DI
        {"x1": 540, "y1": 177, "x2": 570, "y2": 177},
        # Hub to backplane
        {"x1": 460, "y1": 205, "x2": 460, "y2": 240},
    ],
    notes=[
        {"x": 30, "y": 310, "text": "All C# logic stays server-side. The browser sends events; the server sends DOM diffs.",
         "size": 11, "color": "#888888"},
    ],
)

# ── Figure Q.2 — SignalR Redis backplane ────────────────────────────────
g.emit("30-signalr-backplane", 880, 310,
    bands=[
        {"x": 10, "y": 10, "w": 560, "h": 190, "fill": "#eef4fb",
         "label": "Blazor Server pods"},
        {"x": 590, "y": 10, "w": 280, "h": 190, "fill": "#fff8ef",
         "label": "Shared backplane"},
    ],
    nodes=[
        # Pods
        {"x": 30, "y": 55, "w": 150, "h": 55, "style": "user",
         "lines": ["blazor-pod-1", "42 circuits"]},
        {"x": 210, "y": 55, "w": 150, "h": 55, "style": "user",
         "lines": ["blazor-pod-2", "38 circuits"]},
        {"x": 390, "y": 55, "w": 150, "h": 55, "style": "user",
         "lines": ["blazor-pod-3", "0 circuits (new)"]},
        # Load balancer
        {"x": 30, "y": 140, "w": 510, "h": 40, "style": "kernel",
         "lines": ["Kubernetes Service / load balancer — sticky per circuit"]},
        # Redis
        {"x": 620, "y": 55, "w": 220, "h": 55, "style": "ink",
         "lines": ["Redis", "SignalR backplane"]},
        {"x": 620, "y": 140, "w": 220, "h": 40, "style": "box",
         "lines": ["pub/sub on cndp-signalr:*"]},
        # Clients
        {"x": 30, "y": 230, "w": 240, "h": 55, "style": "accent",
         "lines": ["Dashboard clients", "browser tabs, each on one circuit"]},
        {"x": 360, "y": 230, "w": 240, "h": 55, "style": "box",
         "lines": ["REST API caller", "curl POST /orders"]},
        {"x": 650, "y": 230, "w": 190, "h": 55, "style": "ghost",
         "lines": ["Group message", "via Redis → all pods"]},
    ],
    edges=[
        # Pods to Redis
        {"x1": 180, "y1": 82, "x2": 620, "y2": 82, "dashed": True,
         "label": "subscribe"},
        {"x1": 360, "y1": 82, "x2": 620, "y2": 82, "dashed": True},
        {"x1": 540, "y1": 82, "x2": 620, "y2": 82, "dashed": True},
        # Redis to pub/sub
        {"x1": 730, "y1": 110, "x2": 730, "y2": 140},
        # Clients to LB
        {"x1": 150, "y1": 230, "x2": 150, "y2": 180},
    ],
    notes=[
        {"x": 30, "y": 300, "text": "One AddStackExchangeRedis() call replaces the manual pub/sub setup from Appendix C.",
         "size": 11, "color": "#888888"},
    ],
)

print("Done — generated 2 diagrams for Appendix Q")
