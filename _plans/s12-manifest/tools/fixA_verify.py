#!/usr/bin/env python3
"""S12 fix round A: scan edited decks (scratch copies) for every gate of the round.

    fixA_verify.py <deck.pptx> [...]

Per deck: colour_audit (code lines coloured as comments and every other colour hit), caps_audit
(ALL-CAPS emphasis outside the allowlist), the voice scanner's ban tier on the text copy (prose,
and --raw with code included), positional terms (the hits.py set plus soft references such as
"covered next", "two slides back", "slide later", "next slides", "we'll see next"), the old
engine name and the stale-stack denylist. Writes <deck>.md next to the deck. Exit 1 on any hit.
Run with the S12 venv python.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deck_text  # noqa: E402
import colour_audit  # noqa: E402
import caps_audit  # noqa: E402

POS = [r"\babove\b", r"\bbelow\b", r"\bnext\s+slides?\b", r"\bprevious\s+slides?\b", r"\bprevious\s+section\b",
       r"\bfollowing\s+(section|slides?)\b", r"\bsee\s+slide\s+\d+", r"\bpreceding\b", r"\bcovered\s+(next|later|earlier)\b",
       r"\bslides?\s+(back|later|earlier|ago)\b", r"\b(later|earlier)\s+slides?\b", r"\bwe'll\s+see\s+(next|later|more)\b",
       r"\bnext\s+section\b", r"\bthe\s+slide\s+(before|after)\b", r"\bin\s+a\s+moment\b"]
POS = [re.compile(p, re.I) for p in POS]
EX = [re.compile(r"\b(?:above|below)\s+(?:[$~<>]?\d|zero|the\s+(?:threshold|limit|cutoff|floor|ceiling))", re.I),
      re.compile(r"\b(?:above|below)-\w+", re.I), re.compile(r"\b(?:at\s+or|or)\s+(?:above|below)\b", re.I)]
DENY = json.loads((REPO / "_plans/s12-manifest/denylist.json").read_text())


def voice_ban(md, raw=False):
    cmd = ["bash", str(REPO / "scripts/voice/scan.sh"), "--tier", "ban", "--hits", "all"] + (["--raw"] if raw else []) + [str(md)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if re.match(r"^\S+:\d+:", l)]


def check(deck: Path):
    md_text, _ = deck_text.pptx_to_md(deck)
    md = deck.with_suffix(".md")
    md.write_text(md_text)
    name = deck.stem.split(".")[0]
    res = {}
    hits = colour_audit.audit(deck)
    res["colour code-as-comment"] = [h for h in hits if h["kind"] == "code-as-comment"]
    res["colour other"] = [h for h in hits if h["kind"] != "code-as-comment"]
    res["caps"] = [h for h in caps_audit.scan(md) if not h["allow"]]
    res["ban"] = voice_ban(md)
    res["ban --raw"] = voice_ban(md, raw=True)
    pos, eng, deny = [], [], []
    fence = False
    for i, line in enumerate(md_text.split("\n"), 1):
        if line.startswith("```"):
            fence = not fence
            continue
        if re.search("p" + "odman", line, re.I):
            eng.append(i)
        for e in DENY:
            if e.get("files") and not any(f in deck.name or f.endswith(name) for f in e["files"]):
                continue
            if re.search(e["regex"], line, re.I if "i" in e.get("flags", "") else 0):
                if e.get("exempt") and re.search(e["exempt"], line, re.I):
                    continue
                deny.append(f"{e['id']}:{i}:{line.strip()[:80]}")
        if fence:
            continue
        l2 = re.sub(r"`[^`]*`", " ", line)
        for rx in POS:
            for m in rx.finditer(l2):
                ctx = l2[max(0, m.start() - 4): m.end() + 20]
                if not any(x.search(ctx) for x in EX):
                    pos.append(f"{i}:{m.group(0)}: {l2.strip()[:90]}")
    res["positional"], res["engine"], res["denylist"] = pos, eng, deny
    return res


def main(argv):
    bad = 0
    for a in argv:
        r = check(Path(a))
        line = ", ".join(f"{k} {len(v)}" for k, v in r.items())
        print(f"{Path(a).name}: {line}")
        for k, v in r.items():
            for x in v[:15]:
                print(f"   {k}: {x if isinstance(x, str) else json.dumps(x)[:160]}")
            bad += len(v)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
