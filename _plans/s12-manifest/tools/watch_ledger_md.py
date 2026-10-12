#!/usr/bin/env python3
"""Write watch-ledger.md from M/verify/watch-ledger.json (output of watch_ledger.py).

Lines watch_ledger.py leaves unclassified are carried over from the committed ledger when the same deck already
lists the same pattern and text with a reason (manual classification); anything else is an error.
    python3 watch_ledger_md.py [M]
"""
import collections
import json
import re
import sys
from pathlib import Path

M = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent.parent / "watch-ledger.md"
DECKS = [f"Designing-Cloud-Native-APIs-{d}" for d in ("Python", "Quarkus", "Spring", "DotNet", "Go", "Cpp")] + \
    ["K8s-Environment-Access-Policies", "Network-Policy-Process-Advisory"]

data = json.loads((M / "verify" / "watch-ledger.json").read_text())
ledger = {d: [tuple(r) for r in data["ledger"].get(d, [])] for d in DECKS}
old = collections.defaultdict(dict)
deck = None
for line in OUT.read_text().split("\n"):
    m = re.match(r"^## (\S+)$", line)
    if m:
        deck = m.group(1)
        continue
    cells = [c.strip() for c in line.strip("|").split(" | ")] if line.startswith("| [") else None
    if deck and cells and len(cells) == 4:
        old[deck][(cells[1], cells[3][:100])] = cells[2]
for d, ln, slide, pat, text in data["unclassified"]:
    reason = old[d].get((pat, text[:140].replace("|", "\\|")[:100]))
    if not reason:
        raise SystemExit(f"unclassified and not in the committed ledger: {d} {ln} {pat} {text[:80]}")
    ledger[d].append((slide, pat, reason, text[:140]))

out = ["# Watch-tier ledger (decks after the S12 edits)", "",
       "Every watch-tier line the scanner still reports in the post-edit text copies (all edit files applied to fresh "
       "copies of the committed decks, including the decision-7 amendment of 2026-10-12), with its reason code from the "
       "README policy. Ban tier is 0 in all eight decks. Counts are scanner lines (one per pattern per line).", "",
       "| Deck | Kept watch lines | By reason |", "|---|---|---|"]
byp = collections.Counter()
for d in DECKS:
    c = collections.Counter(r[2] for r in ledger[d])
    for r in ledger[d]:
        byp[(r[1], r[2])] += 1
    out.append(f"| {d} | {len(ledger[d])} | " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())) + " |")
out += ["", "By pattern and reason (all decks):", "", "| Pattern | Reason | Lines |", "|---|---|---|"]
out += [f"| {p} | {r} | {n} |" for (p, r), n in sorted(byp.items())]
out += ["", "Notes:", "",
        "- `literal-subject`: the Appendix R slides and eyebrows (`APPENDIX R · MINIKUBE`), agenda and notes where "
        "minikube is the subject (no Appendix S slides after decision 7).",
        "- `notes-paragraph`: notes paragraphs with three or more em dashes, each sentence holding at most one.",
        "- `table-data`: recorded results and unit lists (\"10 passed, 0 failed\").",
        "- `quoted`: the book title *Release It!*.",
        "- The Network-Policy-Process-Advisory rework (decision 7) left no watch-tier line."]
for d in DECKS:
    if not ledger[d]:
        continue
    out += ["", f"## {d}", "", "| Slide | Pattern | Reason | Text |", "|---|---|---|---|"]
    out += [f"| {s} | {p} | {r} | {t.replace('|', chr(92) + '|')} |" for s, p, r, t in ledger[d]]
OUT.write_text("\n".join(out) + "\n")
print({d: len(ledger[d]) for d in DECKS})
