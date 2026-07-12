#!/usr/bin/env python3
"""Generate diagrams for Appendix P: .NET on Linux."""
import generate_diagram as g
g.OUT = "../assets/diagrams"

# ── Figure P.1 — C# → CIL → Native compilation pipeline ──────────────
g.emit("29-dotnet-compilation", 880, 340,
    bands=[
        {"x": 10, "y": 10, "w": 860, "h": 320, "fill": "#fafafa",
         "label": "From source to machine code"},
    ],
    nodes=[
        # Source
        {"x": 30, "y": 70, "w": 130, "h": 70, "style": "user",
         "lines": ["C# source", "Program.cs", "*.csproj"]},
        # Roslyn compiler
        {"x": 210, "y": 70, "w": 140, "h": 70, "style": "accent",
         "lines": ["Roslyn compiler", "dotnet build", "syntax → IL"]},
        # CIL assembly
        {"x": 400, "y": 70, "w": 150, "h": 70, "style": "box",
         "lines": ["CIL assembly", "*.dll (IL bytecode)", "platform-neutral"]},
        # CoreCLR runtime
        {"x": 310, "y": 190, "w": 260, "h": 80, "style": "ink",
         "lines": ["CoreCLR runtime", "GC · JIT · type system", "libcoreclr.so on Linux"]},
        # JIT
        {"x": 620, "y": 70, "w": 120, "h": 70, "style": "accent",
         "lines": ["RyuJIT", "method-at-a-time", "profile-guided"]},
        # Native
        {"x": 780, "y": 70, "w": 80, "h": 70, "style": "kernel",
         "lines": ["x86-64", "native", "code"]},
        # BCL
        {"x": 620, "y": 190, "w": 120, "h": 80, "style": "user",
         "lines": ["BCL", "System.*", "M.E.*"]},
        # AOT alternative
        {"x": 620, "y": 280, "w": 230, "h": 46, "style": "ghost",
         "lines": ["NativeAOT: compile ahead-of-time", "single binary, no JIT needed"]},
    ],
    edges=[
        {"x1": 160, "y1": 105, "x2": 210, "y2": 105, "label": "compile"},
        {"x1": 350, "y1": 105, "x2": 400, "y2": 105, "label": "emit"},
        {"x1": 550, "y1": 105, "x2": 620, "y2": 105, "label": "load"},
        {"x1": 740, "y1": 105, "x2": 780, "y2": 105},
        {"x1": 440, "y1": 140, "x2": 440, "y2": 190, "label": "hosts", "lx": 20},
        {"x1": 570, "y1": 230, "x2": 620, "y2": 230, "label": "provides"},
        {"x1": 680, "y1": 140, "x2": 680, "y2": 190, "dashed": True, "label": "uses"},
    ],
    notes=[
        {"x": 30, "y": 290, "text": "C# is one of several .NET languages (F#, VB.NET).",
         "size": 11, "color": "#888888"},
        {"x": 30, "y": 310, "text": "CIL = Common Intermediate Language — the CPU-agnostic bytecode all .NET languages compile to.",
         "size": 11, "color": "#888888"},
    ],
)

# ── Figure P.2 — Kestrel request processing pipeline ─────────────────
g.emit("29-kestrel-pipeline", 880, 380,
    bands=[
        {"x": 10, "y": 10, "w": 860, "h": 140, "fill": "#eef4fb",
         "label": "Network layer"},
        {"x": 10, "y": 160, "w": 860, "h": 100, "fill": "#fff8ef",
         "label": "ASP.NET Core middleware pipeline"},
        {"x": 10, "y": 270, "w": 860, "h": 100, "fill": "#fafafa",
         "label": "Application endpoints"},
    ],
    nodes=[
        # Client
        {"x": 30, "y": 45, "w": 100, "h": 55, "style": "kernel",
         "lines": ["Client", "curl / browser"]},
        # Kestrel
        {"x": 200, "y": 35, "w": 160, "h": 75, "style": "ink",
         "lines": ["Kestrel", "libuv / IO_Uring", "HTTP/1.1, H2, H3"]},
        # TLS
        {"x": 410, "y": 45, "w": 120, "h": 55, "style": "user",
         "lines": ["TLS termination", "OpenSSL"]},
        # Connection
        {"x": 580, "y": 45, "w": 140, "h": 55, "style": "box",
         "lines": ["Connection mgmt", "keep-alive, pipelining"]},
        # Request parsing
        {"x": 760, "y": 45, "w": 100, "h": 55, "style": "box",
         "lines": ["HTTP parser", "Span<byte>"]},
        # Middleware
        {"x": 30, "y": 180, "w": 120, "h": 55, "style": "accent",
         "lines": ["Routing", "MapGet / MapPost"]},
        {"x": 170, "y": 180, "w": 120, "h": 55, "style": "accent",
         "lines": ["Auth", "JWT / OIDC"]},
        {"x": 310, "y": 180, "w": 120, "h": 55, "style": "accent",
         "lines": ["CORS", "cross-origin"]},
        {"x": 450, "y": 180, "w": 130, "h": 55, "style": "accent",
         "lines": ["Diagnostics", "OTel integration"]},
        {"x": 600, "y": 180, "w": 130, "h": 55, "style": "accent",
         "lines": ["WebSockets", "upgrade handler"]},
        {"x": 750, "y": 180, "w": 110, "h": 55, "style": "accent",
         "lines": ["Exception", "handler"]},
        # Endpoints
        {"x": 30, "y": 290, "w": 160, "h": 55, "style": "user",
         "lines": ["Minimal APIs", "app.MapGet(\"/orders\", ...)"]},
        {"x": 220, "y": 290, "w": 130, "h": 55, "style": "user",
         "lines": ["gRPC", "Grpc.AspNetCore"]},
        {"x": 380, "y": 290, "w": 140, "h": 55, "style": "user",
         "lines": ["GraphQL", "HotChocolate"]},
        {"x": 560, "y": 290, "w": 130, "h": 55, "style": "user",
         "lines": ["SignalR / WS", "real-time"]},
        {"x": 720, "y": 290, "w": 140, "h": 55, "style": "user",
         "lines": ["Health checks", "/healthz, /readyz"]},
    ],
    edges=[
        {"x1": 130, "y1": 72, "x2": 200, "y2": 72},
        {"x1": 360, "y1": 72, "x2": 410, "y2": 72},
        {"x1": 530, "y1": 72, "x2": 580, "y2": 72},
        {"x1": 720, "y1": 72, "x2": 760, "y2": 72},
        # down from parsed to middleware
        {"x1": 810, "y1": 100, "x2": 810, "y2": 180, "amber": True,
         "label": "request", "lx": -30},
        # through middleware
        {"x1": 150, "y1": 208, "x2": 170, "y2": 208},
        {"x1": 290, "y1": 208, "x2": 310, "y2": 208},
        {"x1": 430, "y1": 208, "x2": 450, "y2": 208},
        {"x1": 580, "y1": 208, "x2": 600, "y2": 208},
        {"x1": 730, "y1": 208, "x2": 750, "y2": 208},
    ],
    notes=[
        {"x": 30, "y": 370, "text": "Kestrel is the built-in cross-platform web server — no IIS, no Apache, no nginx required.",
         "size": 11, "color": "#888888"},
    ],
)

# ── Figure P.3 — Multi-stage container build ─────────────────────────
g.emit("29-container-layers", 880, 460,
    bands=[
        {"x": 10, "y": 10, "w": 400, "h": 440, "fill": "#fff8ef",
         "label": "Build stage (discarded)"},
        {"x": 430, "y": 10, "w": 440, "h": 440, "fill": "#eef4fb",
         "label": "Runtime stage (shipped)"},
    ],
    nodes=[
        # Build stage
        {"x": 30, "y": 55, "w": 180, "h": 55, "style": "accent",
         "lines": ["ubi9/dotnet-100", "SDK image (~780 MB)"]},
        {"x": 230, "y": 55, "w": 160, "h": 55, "style": "kernel",
         "lines": ["SDK tools", "MSBuild, NuGet, Roslyn"]},
        {"x": 30, "y": 140, "w": 360, "h": 50, "style": "box",
         "lines": ["COPY *.csproj → dotnet restore", "download NuGet packages (cached layer)"]},
        {"x": 30, "y": 210, "w": 360, "h": 50, "style": "box",
         "lines": ["COPY source → dotnet publish -c Release", "compile C# → CIL, tree-shake deps"]},
        {"x": 30, "y": 290, "w": 170, "h": 55, "style": "ink",
         "lines": ["/app output", "*.dll + deps", "~30–80 MB"]},
        # Trimming note
        {"x": 220, "y": 290, "w": 170, "h": 55, "style": "ghost",
         "lines": ["PublishTrimmed", "removes unused BCL", "assemblies"]},
        # Runtime stage
        {"x": 450, "y": 55, "w": 200, "h": 55, "style": "user",
         "lines": ["ubi9/dotnet-100-aspnet", "runtime image (~170 MB)"]},
        {"x": 670, "y": 55, "w": 180, "h": 55, "style": "kernel",
         "lines": ["Runtime only", "CoreCLR + ASP.NET Core"]},
        {"x": 450, "y": 140, "w": 400, "h": 50, "style": "box",
         "lines": ["COPY --from=build /app .", "only the published output, no SDK"]},
        {"x": 450, "y": 210, "w": 200, "h": 55, "style": "box",
         "lines": ["EXPOSE 8080", "Kestrel binds 8080"]},
        {"x": 670, "y": 210, "w": 180, "h": 55, "style": "box",
         "lines": ["non-root user", "UID 1001 (UBI default)"]},
        {"x": 450, "y": 290, "w": 400, "h": 55, "style": "ink",
         "lines": ["Final image: ~200 MB", "UBI9 base + ASP.NET runtime + app DLLs"]},
        # K8s
        {"x": 450, "y": 370, "w": 190, "h": 55, "style": "user",
         "lines": ["Kubernetes Pod", "limits, probes, OTel"]},
        {"x": 660, "y": 370, "w": 190, "h": 55, "style": "user",
         "lines": ["Podman / Docker", "compose for local dev"]},
    ],
    edges=[
        # Build flow
        {"x1": 210, "y1": 82, "x2": 230, "y2": 82},
        {"x1": 210, "y1": 110, "x2": 210, "y2": 140, "label": "step 1"},
        {"x1": 210, "y1": 190, "x2": 210, "y2": 210, "label": "step 2"},
        {"x1": 210, "y1": 260, "x2": 115, "y2": 290},
        # Copy to runtime
        {"x1": 200, "y1": 317, "x2": 450, "y2": 165, "amber": True,
         "label": "COPY --from=build"},
        # Runtime flow
        {"x1": 650, "y1": 82, "x2": 670, "y2": 82},
        {"x1": 650, "y1": 190, "x2": 650, "y2": 210},
        {"x1": 650, "y1": 265, "x2": 650, "y2": 290},
        {"x1": 545, "y1": 345, "x2": 545, "y2": 370},
        {"x1": 755, "y1": 345, "x2": 755, "y2": 370},
    ],
    notes=[
        {"x": 30, "y": 375, "text": "Red Hat UBI images are freely redistributable",
         "size": 11, "color": "#888888"},
        {"x": 30, "y": 395, "text": "and supported for production use.",
         "size": 11, "color": "#888888"},
        {"x": 30, "y": 425, "text": "The SDK never ships — only the runtime and your app DLLs.",
         "size": 11, "color": "#888888"},
    ],
)

print("Done — generated 3 diagrams for Appendix P")
