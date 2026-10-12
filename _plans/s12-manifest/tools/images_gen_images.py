#!/usr/bin/env python3
"""Build the replacement figures for the S12 image audit.

site      : assets/diagrams/<name>.svg rendered as is (arrow glyphs -> ASCII for cairosvg)
variant   : a site SVG with label substitutions per language; source kept in edits/png/src/
authored  : new SVGs in the house style (Appendix J tables, .NET bridge and Stateless figures)
All PNGs go to lgtm-presentation/edits/png/ at 1400 px wide (cairosvg 2.9.1).
"""
import html
import re
from pathlib import Path

import cairosvg

REPO = Path("~/Dev/cloud-native-design-patterns")
DIAG = REPO / "assets" / "diagrams"
OUT = REPO / "lgtm-presentation" / "edits" / "png"
SRC = OUT / "src"
SRC.mkdir(parents=True, exist_ok=True)
FONT = "'Red Hat Text', 'Liberation Sans', system-ui, sans-serif"


def ascii_arrows(s):
    return s.replace("→", "-&gt;").replace("←", "&lt;-")


def render(svg_text, png_name):
    cairosvg.svg2png(bytestring=ascii_arrows(svg_text).encode(), write_to=str(OUT / f"{png_name}.png"),
                     output_width=1400, background_color="white")


SITE = ["04-cqrs", "04-log-tailing", "22-l7-journey", "22-east-west", "24-shared-database",
        "25-failure-taxonomy", "13-antipatterns-grid", "03-composition", "06-scale-on-lag",
        "06-derive-streams", "17-saga-state", "22-l7-layers", "25-circuit-breaker", "22-hop-cost",
        "29-dotnet-compilation", "29-kestrel-pipeline", "29-container-layers"]

E = html.escape
VARIANTS = {
    # name: (site svg, [(old, new), ...]); old/new are SVG-escaped text as it appears in the file
    "22-hop-cost-cpp": ("22-hop-cost", [("In-app rule eval (durable-rules)", "In-app rule eval (sol2 / Lua)")]),
    "22-hop-cost-go": ("22-hop-cost", [("In-app rule eval (durable-rules)", "In-app rule eval (gopher-lua)")]),
    "22-hop-cost-drools": ("22-hop-cost", [("In-app rule eval (durable-rules)", "In-app rule eval (Drools)")]),
    "22-hop-cost-nrules": ("22-hop-cost", [("In-app rule eval (durable-rules)", "In-app rule eval (NRules)")]),
    "02-pick-protocol-go": ("02-pick-protocol", [(">FastAPI<", ">net/http ServeMux<"),
                                                 (">Strawberry / Graphene<", ">gqlgen<"),
                                                 (">grpc + protobuf<", ">grpc-go + protobuf<")]),
    "02-pick-protocol-dotnet": ("02-pick-protocol", [(">FastAPI<", ">ASP.NET Core minimal APIs<"),
                                                     (">Strawberry / Graphene<", ">HotChocolate<"),
                                                     (">grpc + protobuf<", ">Grpc.AspNetCore + protobuf<")]),
    "02-pick-protocol-spring": ("02-pick-protocol", [(">FastAPI<", ">Spring Web MVC<"),
                                                     (">Strawberry / Graphene<", ">Spring for GraphQL<"),
                                                     (">grpc + protobuf<", ">grpc-java + protobuf<")]),
    "02-mesh-handles-wire-go": ("02-mesh-handles-wire", [(">FastAPI / grpc server<", ">net/http / grpc-go server<")]),
    "02-mesh-handles-wire-dotnet": ("02-mesh-handles-wire", [(">FastAPI / grpc server<", ">ASP.NET Core / gRPC server<")]),
    "02-mesh-handles-wire-spring": ("02-mesh-handles-wire", [(">FastAPI / grpc server<", ">Spring Boot / gRPC server<")]),
    "01-factors-mapped-py": ("01-factors-mapped", [("one repo · Poetry · one image per release",
                                                     "one repo · pip + requirements.txt · one image per release")]),
    "01-factors-mapped-go": ("01-factors-mapped", [("one repo · Poetry · one image per release",
                                                     "one repo · go.mod + go.sum · one image per release"),
                                                    ("pydantic-settings · per-profile · secrets injected",
                                                     "os.Getenv · per-profile · secrets injected")]),
}

ROUTER = {
    "22-business-rule-routing-cpp": dict(
        front="Drogon HttpController",
        code=["Task&lt;&gt; Orders::route(HttpRequestPtr req, auto cb) {",
              "  auto order = parse&lt;OrderIn&gt;(req);          // front",
              "  auto ctx   = co_await enrich(order);   // context",
              "  auto dests = router.evaluate(order, ctx); // rules",
              "  for (const auto&amp; dest : dests)        // dispatch",
              "    produce_to(*producer_, topic, id, body); // rdkafka++"],
        engine=["sol2 + Lua", "embedded Lua VM", "rules.lua, sandboxed", "(loaded at startup)"]),
    "22-business-rule-routing-go": dict(
        front="net/http handler",
        code=["func (s *Server) route(w http.ResponseWriter, r *http.Request) {",
              "rc    := enrich(ctx, order)            // context",
              "dests := rt.evaluate(ctx, order, rc)   // rules",
              "for _, dest := range dests {           // dispatch",
              "    cl.Produce(ctx, record(dest), done) // franz-go",
              "}"],
        engine=["gopher-lua", "Lua VM in pure Go", "rules.lua, sandboxed", "(pooled LState)"]),
    "22-business-rule-routing-dotnet": dict(
        front="OrderRouter (ASP.NET Core)",
        code=["public async Task Route(OrderInbound msg) {",
              "var fact = new OrderFact(id, cents, customer); // context",
              "var session = rules.CreateSession();",
              "session.Insert(fact); session.Fire();          // rules",
              "foreach (var dest in fact.WhereTo.Split(','))  // dispatch",
              "    await producer.ProduceAsync(topic, message); // Confluent.Kafka"],
        engine=["NRules", "Rete engine for .NET", "rules in C# (NRules.Fluent)", "(forward chaining)"]),
}


def router_variant(name, spec):
    svg = (DIAG / "22-business-rule-routing.svg").read_text()
    texts = re.findall(r"(<text[^>]*>)([^<]*)(</text>)", svg)
    old = [t[1] for t in texts]
    # locate the front title, the code lines and the engine lines by their site text
    fi = old.index("FastAPI / Starlette router")
    ci = old.index("@app.post(&quot;/orders/route&quot;)        # front")
    ei = old.index("durable-rules")
    repl = {fi: spec["front"]}
    for k, line in enumerate(spec["code"]):
        repl[ci + k] = line
    for k, line in enumerate(spec["engine"]):
        repl[ei + k] = line
    out, i = [], 0

    def sub(m):
        nonlocal i
        new = repl.get(i, m.group(2))
        i += 1
        return m.group(1) + new.replace(" ", " ") * 0 + new + m.group(3) if False else m.group(1) + new + m.group(3)
    svg2 = re.sub(r"(<text[^>]*>)([^<]*)(</text>)", sub, svg)
    return svg2


# ------------------------------------------------------------------ authored figures

def tbl(title, subtitle, header, rows, colw, foot, accent_col=None, italic_col=0, width=1600):
    rowh, top = 30, 120
    h = top + 34 + rowh * len(rows) + 90
    h = int(h * 1.08)  # blank band at the bottom: the slide caption sits over the frame bottom
    x0 = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" font-family="{FONT}">',
             f'<rect width="{width}" height="{h}" fill="#ffffff"/>',
             f'<text x="{width/2}" y="48" font-size="26" font-weight="700" fill="#151515" text-anchor="middle">{E(title)}</text>',
             f'<text x="{width/2}" y="78" font-size="16" font-style="italic" fill="#5a5a5a" text-anchor="middle">{E(subtitle)}</text>']
    x = x0
    for k, hd in enumerate(header):
        parts.append(f'<text x="{x+6}" y="{top+20}" font-size="14" font-weight="700" fill="#242424">{E(hd)}</text>')
        x += colw[k]
    parts.append(f'<line x1="{x0}" y1="{top+30}" x2="{x0+sum(colw)}" y2="{top+30}" stroke="#151515" stroke-width="1.5"/>')
    for r, row in enumerate(rows):
        y = top + 34 + r * rowh
        if r % 2 == 0:
            parts.append(f'<rect x="{x0}" y="{y}" width="{sum(colw)}" height="{rowh}" fill="#f4f4f4"/>')
        x = x0
        for k, cell in enumerate(row):
            style = ""
            fill = "#242424"
            if k == italic_col:
                style = ' font-style="italic"'
                fill = "#5a5a5a"
            elif k == 1:
                style = ' font-weight="700"'
                fill = "#151515"
            if accent_col is not None and k == accent_col:
                fill = "#0066CC"
                style = ' font-weight="700"'
            parts.append(f'<text x="{x+6}" y="{y+20}" font-size="13.5"{style} fill="{fill}">{E(cell)}</text>')
            x += colw[k]
    yf = top + 34 + rowh * len(rows) + 40
    for k, line in enumerate(foot):
        parts.append(f'<text x="{width/2}" y="{yf + k*26}" font-size="15" font-weight="{700 if k == 0 else 400}" '
                     f'fill="{"#3f7a1f" if k == 0 else "#5a5a5a"}" text-anchor="middle"{"" if k == 0 else " font-style=\"italic\""}>{E(line)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def md_table(path, start_hdr):
    lines = path.read_text().split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith(start_hdr))
    rows = []
    for l in lines[i + 2:]:
        if not l.startswith("|"):
            break
        rows.append([c.strip() for c in l.strip().strip("|").split("|")])
    return rows


def bridge_svg():
    rows = [("IIS app pool", "Kubernetes Pod (ReplicaSet)"),
            ("App pool recycle", "Graceful shutdown + rolling deploy"),
            ("WCF service + DataContract", "gRPC + .proto (or ASP.NET Core + OpenAPI)"),
            ("WCF bindings (BasicHttp / NetTcp / MSMQ)", "REST + gRPC + Kafka, picked per call"),
            ("COM+ / MSDTC distributed transactions", "Saga + outbox (no two-phase commit)"),
            ("MSMQ / SQL Server Service Broker", "Kafka topic + consumer group (Confluent.Kafka)"),
            ("Windows Service", "IHostedService / BackgroundService in a Pod"),
            ("App.config / web.config", "appsettings.json + env vars + ConfigMap / Secret"),
            ("Windows performance counters", "OpenTelemetry metrics → Prometheus / Mimir"),
            ("Windows Event Log", "Structured logs (Microsoft.Extensions.Logging) → Loki"),
            ("Active Directory + Windows Auth", "mTLS via Istio + SPIFFE identity"),
            (".NET Remoting", "gRPC over HTTP/2"),
            ("BizTalk orchestration", "Temporal workflows / Stateless state machines")]
    W, H = 2000, 1120
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FONT}">',
         '<defs><marker id="a" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#999"/></marker></defs>',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="{W/2}" y="58" font-size="32" font-weight="700" fill="#2a2a2a" text-anchor="middle">From the Windows world to Kubernetes</text>',
         f'<text x="{W/2}" y="92" font-size="21" font-style="italic" fill="#6a6a6a" text-anchor="middle">what you knew, and what it becomes</text>',
         f'<text x="560" y="182" font-size="23" font-weight="700" font-style="italic" fill="#5a5a5a" text-anchor="middle">Windows / .NET 4.x era</text>',
         f'<text x="1475" y="182" font-size="23" font-weight="700" font-style="italic" fill="#5a5a5a" text-anchor="middle">Kubernetes / .NET 10 era</text>']
    for k, (l, r) in enumerate(rows):
        y = 190 + k * 61
        p.append(f'<rect x="104" y="{y}" width="914" height="54" rx="10" fill="#fcf2e1" stroke="#c9a14a" stroke-width="2.5"/>')
        p.append(f'<rect x="1052" y="{y}" width="846" height="54" rx="10" fill="#f5ebd6" stroke="#c4a06a" stroke-width="2.5"/>')
        p.append(f'<line x1="1018" y1="{y+27}" x2="1048" y2="{y+27}" stroke="#999" stroke-width="2.5" marker-end="url(#a)"/>')
        p.append(f'<text x="561" y="{y+34}" font-size="19.5" font-weight="700" fill="#6b4a12" text-anchor="middle">{E(l)}</text>')
        p.append(f'<text x="1475" y="{y+34}" font-size="19.5" font-weight="700" fill="#6b4a12" text-anchor="middle">{E(r)}</text>')
    p.append(f'<text x="{W/2}" y="1030" font-size="21" font-style="italic" fill="#7a5a1a" text-anchor="middle">The architectural shift: stop owning the host (IIS, MSDTC, MSMQ). Kubernetes owns the platform; you own the code.</text>')
    p.append(f'<text x="{W/2}" y="1086" font-size="21" font-style="italic" fill="#7a5a1a" text-anchor="middle">Most of these are patterns you already used; the platform now runs them instead of IIS.</text>')
    p.append("</svg>")
    return "\n".join(p)


def stateless_svg():
    W, H = 2000, 1020
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FONT}">',
         '<defs><marker id="g" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#888"/></marker>'
         '<marker id="r" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#c0474a"/></marker></defs>',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="{W/2}" y="60" font-size="32" font-weight="700" fill="#2a2a2a" text-anchor="middle">Stateless for in-process sagas in .NET</text>',
         f'<text x="{W/2}" y="92" font-size="21" font-style="italic" fill="#6a6a6a" text-anchor="middle">lighter-weight: states + triggers + transitions, persisted in your own DB</text>']
    states = [("Created", "#fcf2e1", "#c9a14a", "#6b4a12"), ("Paid", "#e7eef8", "#2f5ea8", "#1d3a6b"),
              ("Reserved", "#f7e6f0", "#a0457a", "#6b2a50"), ("Shipped", "#f5ebd6", "#c4904a", "#6b4a12"),
              ("Done", "#e8f2e0", "#4f8a2f", "#2d5a16")]
    trig = ["PayOk", "ReserveOk", "ShipOk", "Delivered"]
    for k, (n, f, s, t) in enumerate(states):
        x = 200 + k * 340
        p.append(f'<rect x="{x}" y="196" width="260" height="102" rx="12" fill="{f}" stroke="{s}" stroke-width="2.5"/>')
        p.append(f'<text x="{x+130}" y="232" font-size="24" font-weight="700" fill="{t}" text-anchor="middle">{n}</text>')
        if k < 4:
            p.append(f'<line x1="{x+260}" y1="247" x2="{x+338}" y2="247" stroke="#888" stroke-width="2.5" marker-end="url(#g)"/>')
            p.append(f'<text x="{x+299}" y="236" font-size="14" font-weight="700" fill="#1d3a6b" text-anchor="middle">{trig[k]}</text>')
    p.append('<line x1="1010" y1="298" x2="1010" y2="362" stroke="#c0474a" stroke-width="2.5" stroke-dasharray="7 5" marker-end="url(#r)"/>')
    p.append('<text x="1030" y="342" font-size="16" font-style="italic" fill="#a02a2a">on StepFail</text>')
    for k, n in enumerate(["Compensating", "Failed"]):
        x = 880 + k * 340
        p.append(f'<rect x="{x}" y="366" width="260" height="84" rx="12" fill="#f8e2e2" stroke="#c0474a" stroke-width="2.5"/>')
        p.append(f'<text x="{x+130}" y="402" font-size="23" font-weight="700" fill="#8a2020" text-anchor="middle">{n}</text>')
    p.append('<line x1="1140" y1="408" x2="1218" y2="408" stroke="#c0474a" stroke-width="2.5" marker-end="url(#r)"/>')
    boxes = [
        (102, "#f5ebd6", "#c4904a", "#5a3a08", "StateMachine&lt;TState, TTrigger&gt;",
         ["states · triggers · transitions", "guards (predicate on edge)", "entry / exit actions",
          "OnTransitioned listeners", "", "Stateless package (Apache 2.0)", "tiny dependency, no extra runtime"]),
        (746, "#eeeeee", "#888888", "#3a3a3a", "Persist state yourself",
         ["serialize CurrentState → saga row", "", "EF Core · Dapper · Marten", "",
          "one DbContext transaction per step", "scheduled sweeper for in-flight sagas"]),
        (1390, "#e7eef8", "#2f5ea8", "#1d3a6b", "Driving the machine",
         ["await sm.FireAsync(", "    Trigger.PayOk, payload);", "", "// guards + actions run on transition",
          "// persister saves new CurrentState", "", "need durable timers and retries:", "Temporal (separate server)"]),
    ]
    for x, f, s, t, title, lines in boxes:
        w = 576 if x != 1390 else 542
        p.append(f'<rect x="{x}" y="544" width="{w}" height="304" rx="12" fill="{f}" stroke="{s}" stroke-width="2.5"/>')
        p.append(f'<text x="{x+w/2}" y="580" font-size="23" font-weight="700" fill="{t}" text-anchor="middle">{title}</text>')
        for k, line in enumerate(lines):
            mono = x == 1390 and (line.startswith("await") or line.startswith("    ") or line.startswith("//"))
            fam = ' font-family="\'Red Hat Mono\', \'Liberation Mono\', monospace"' if mono else ""
            p.append(f'<text x="{x+w/2}" y="{606 + k*24}" font-size="18"{fam} fill="{t}" text-anchor="middle">{E(line)}</text>')
    p.append(f'<text x="{W/2}" y="922" font-size="21" font-weight="700" fill="#4f8a2f" text-anchor="middle">in-process · no extra cluster to run · open source (Apache 2.0)</text>')
    p.append(f'<text x="{W/2}" y="988" font-size="21" font-style="italic" fill="#7a5a1a" text-anchor="middle">When the saga is small, in-process, and you do not want a separate Temporal cluster.</text>')
    p.append("</svg>")
    return "\n".join(p)


def main():
    for name in SITE:
        render((DIAG / f"{name}.svg").read_text(), name)
    for name, (base, subs) in VARIANTS.items():
        svg = (DIAG / f"{base}.svg").read_text()
        for o, n in subs:
            assert o in svg, (name, o)
            svg = svg.replace(o, n)
        (SRC / f"{name}.svg").write_text(svg)
        render(svg, name)
    for name, spec in ROUTER.items():
        svg = router_variant(name, spec)
        (SRC / f"{name}.svg").write_text(svg)
        render(svg, name)
    j = REPO / "_docs" / "23-appendix-j-dotnet-toolkit.md"
    lib = md_table(j, "| Concern | Library |")
    svg = tbl("The pinned .NET 10 toolkit", "every library in your csproj: purpose, license, NuGet package",
              ["Concern", "Library", "Purpose", "License", "NuGet package"],
              [r[:5] for r in lib], [160, 300, 500, 130, 560],
              ["Every entry is MIT, Apache 2.0 or BSD-3 · every entry runs on plain Kubernetes · no cloud-only dependencies",
               "Kafka through Confluent.Kafka directly; stream processing on Streamiz.Kafka.Net."], accent_col=3, width=1740)
    (SRC / "70-appJ-pinned-libraries-dn.svg").write_text(svg)
    render(svg, "70-appJ-pinned-libraries-dn")
    plat = md_table(j, "| Concern | Component |")
    plat = [[c if not (r[1].startswith("Redis") and k == 3) else "AGPL-3.0 (Redis 8) / BSD (Valkey)"
             for k, c in enumerate(r)] for r in plat]
    svg = tbl("The pinned cloud-native platform stack", "the cluster-side open-source components your .NET Pods rely on",
              ["Concern", "Component", "Purpose", "License"], plat, [260, 420, 520, 340],
              ["These components serve a Spring Boot or Python stack the same way.",
               "Standard CNCF-friendly stack; .NET 10 is the runtime in the application Pods."], accent_col=3)
    (SRC / "71-appJ-pinned-platform-dn.svg").write_text(svg)
    render(svg, "71-appJ-pinned-platform-dn")
    mig = md_table(j, "| Concern | Coming from")
    svg = tbl("Migration reference", "concrete patterns from Windows / .NET Framework 4.x to Kubernetes / .NET 10",
              ["Concern", "Coming from (Windows / .NET 4.x)", "Going to (.NET 10 / Kubernetes)", "What changes most"],
              mig, [200, 380, 560, 640],
              ["Almost every row keeps the shape of the pattern; what changes is who owns the host and the substrate.",
               "The last column is usually 'the platform owns more, your code owns less'."], width=1860)
    (SRC / "72-appJ-migration-reference-dn.svg").write_text(svg)
    render(svg, "72-appJ-migration-reference-dn")
    svg = bridge_svg()
    (SRC / "01b-windows-to-k8s-bridge-dn.svg").write_text(svg)
    render(svg, "01b-windows-to-k8s-bridge-dn")
    svg = stateless_svg()
    (SRC / "63-appD-stateless-dn.svg").write_text(svg)
    render(svg, "63-appD-stateless-dn")


if __name__ == "__main__":
    main()
