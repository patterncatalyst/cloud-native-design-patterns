#!/usr/bin/env python3
"""Decision 7 figures: vendor-neutral label copies of four site SVGs, rendered for the decks.

Writes lgtm-presentation/edits/png/src/<name>.svg (the corrected SVG text) and
lgtm-presentation/edits/png/<name>.png (cairosvg 2.9.1, 1400 px, arrow glyphs written as ASCII because
cairosvg has no fallback font for them). The same label changes are the site fixes listed in
site-fixes.md (SVG text, the .excalidraw text and originalText, and alt text). Run with the S12 venv python.
"""
from pathlib import Path

import cairosvg

REPO = Path(__file__).resolve().parents[3]
DIAG = REPO / "assets" / "diagrams"
OUT = REPO / "lgtm-presentation" / "edits" / "png"
SRC = OUT / "src"

FIGS = {
    # png name: (site svg, [(old element text, new element text, expected count)])
    "12-valet-key": ("12-valet-key", [
        ("Resource (S3, blob, file)", "Resource (object store, file)", 1),
        ("the app never proxies the bytes — no long-lived credentials at the client (S3 pre-signed URLs, Azure "
         "SAS tokens, GCS signed URLs, STS AssumeRole)",
         "the app never proxies the bytes — no long-lived credentials at the client (Example 12: a ticket the "
         "service signs and verifies itself)", 1),
    ]),
    # the site zero-trust figure is vendor-neutral already; the decks' copy listed Google IAP, Cloudflare Access
    # and AWS Verified Access as examples
    "12-zero-trust": ("12-zero-trust", []),
    "net-advisory-tier-evaluation": ("advisory-tier-evaluation", [
        ("Tier 1 — AdminNetworkPolicy", "Tier 1 — CNP Admin tier", 1),
        ("Tier 3 — BANP", "Tier 3 — CNP Baseline tier", 1),
        ("ANP evaluates", "Admin tier evaluates", 1),
        ("cluster-scoped, priority 0-99", "cluster-scoped, priority 0-1000", 1),
        ("Allow", "Accept", 2),
        ("BANP evaluates", "Baseline tier evaluates", 1),
        ("cluster singleton, safety net", "cluster-scoped, safety net", 1),
        ("OVN-Kubernetes three-tier policy evaluation", "ClusterNetworkPolicy three-tier evaluation", 1),
        ("BANP catches unmatched traffic.", "The Baseline tier catches unmatched traffic.", 1),
        ("ANP Allow/Deny are final — NP and BANP are skipped.", "Admin Accept/Deny skip NP and Baseline.", 1),
        ("BANP is overridable by NetworkPolicy.", "Baseline is overridable by NetworkPolicy.", 1),
    ]),
    "net-advisory-ci-pipeline": ("advisory-ci-pipeline", [
        ("oc apply --dry-run", "kubeconform", 1),
        ("ACS Build-time", "Baseline Diff", 1),
        ("baseline validation", "vs observed flows", 1),
        ("ACS + OVN-K verify", "flow logs + Falco", 1),
    ]),
    "net-advisory-team-ownership": ("advisory-team-ownership", [
        ("EgressFirewall", "Egress rules", 1),
        ("ANP / BANP review", "Admin / Baseline review", 1),
        ("Perimeter (Palo Alto)", "Perimeter firewall", 1),
        ("AdminNetworkPolicy", "CNP Admin tier", 1),
        ("cluster guardrails, Allow/Deny/Pass", "cluster guardrails, Accept/Deny/Pass", 1),
        ("BANP", "CNP Baseline tier", 1),
        ("ACS baselines", "Observed baselines", 1),
    ]),
}


# authored .NET Appendix J tables (tools/images_gen_images.py builds them from _docs/23 tables, which the site
# fix changes the same way): corrected in place in edits/png/src/ and re-rendered
SRC_FIXES = {
    "70-appJ-pinned-libraries-dn": [
        ("Open-source Redis backplane (not Azure SignalR Service)", "Open-source Redis backplane (no managed SignalR service)", 1),
        ("Every entry is MIT, Apache 2.0 or BSD-3 · every entry runs on plain Kubernetes · no Azure-only dependencies",
         "Every entry is MIT, Apache 2.0 or BSD-3 · every entry runs on plain Kubernetes · no cloud-only dependencies", 1),
    ],
    "72-appJ-migration-reference-dn": [
        ("Same C# both sides of the wire; no Azure required", "Same C# both sides of the wire; no managed cloud service required", 1),
    ],
}


def main():
    jobs = [(png, DIAG / f"{site}.svg", subs) for png, (site, subs) in FIGS.items()]
    jobs += [(png, SRC / f"{png}.svg", subs) for png, subs in SRC_FIXES.items()]
    for png, path, subs in jobs:
        site = path.stem
        svg = path.read_text()
        for old, new, n in subs:
            a, b = f">{old}</text>", f">{new}</text>"
            if svg.count(a) != n and svg.count(b) == n:
                continue  # already corrected (re-run on a fixed src copy)
            if svg.count(a) != n:
                raise SystemExit(f"{site}: {old!r} found {svg.count(a)}x, expected {n}")
            svg = svg.replace(a, b)
        (SRC / f"{png}.svg").write_text(svg)
        cairosvg.svg2png(bytestring=svg.replace("→", "-&gt;").replace("←", "&lt;-").encode(),
                         write_to=str(OUT / f"{png}.png"), output_width=1400, background_color="white")
        print(png)


if __name__ == "__main__":
    main()
