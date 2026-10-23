#!/usr/bin/env python3
"""Classify every watch-tier hit left in the post-edit text copies (M/verify/<deck>.md).

Prints unclassified hits (to fix) and writes M/verify/watch-ledger.md (per deck, kept hits with reasons).
"""
import re, subprocess, sys, collections, json
from pathlib import Path
M = Path(__file__).resolve().parent.parent
VER = M / "verify"
REPO = Path(__file__).resolve().parents[3]
SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9'\"‘“(`\[])")
decks = sys.argv[1:] or [p.stem for p in sorted(VER.glob("*.md")) if not p.name.startswith("watch")]
ledger = collections.defaultdict(list)
unclassified = []
for d in decks:
    md = VER / f"{d}.md"
    out = subprocess.run(["bash", str(REPO / "scripts/voice/scan.sh"), "--tier", "watch", "--hits", "all", str(md)],
                         capture_output=True, text=True).stdout
    lines = md.read_text().split("\n")
    pat = None
    for l in out.splitlines():
        m = re.match(r"^## \[watch\] (.*)$", l)
        if m:
            pat = m.group(1); continue
        m = re.match(r"^\S*?:(\d+):(.*)$", l)
        if not m or pat is None:
            continue
        ln = int(m.group(1)); text = lines[ln - 1]
        # find the slide heading for context
        k = ln - 1
        while k > 0 and not lines[k].startswith("## ["):
            k -= 1
        slide = lines[k][:60] if k > 0 else ""
        reason = None
        if pat.startswith("em-dash"):
            sents = SPLIT.split(text)
            if all(s.count("—") <= 1 for s in sents):
                reason = "notes-paragraph" if text.startswith(">") else "one-per-sentence"
        elif pat.startswith("environment-specific"):
            if re.search(r"minikube|OpenShift|k3d|kind\b", text, re.I) and not re.search(r"laptop|my machine", text, re.I):
                reason = "literal-subject"
        elif pat.startswith("parallel-number"):
            if re.search(r"\d+ passed, \d+ failed|\d+ vCPU|MiB|GB|\bms\b|\bs\b", text):
                reason = "table-data"
        elif pat.startswith("lie"):
            if re.search(r"failures lie|failure that lies|hang, or lie|mtime can lie|clock[s]? (can )?lie|health check[s]? (can )?lie|metrics lie", text, re.I):
                reason = "machine-subject"
        elif pat.startswith("quietly"):
            if re.search(r"(silently|quietly) (rais|fail|drop|corrupt|break|increas|retr|los|swallow|skip|ignor|discard|diverg|degrad|stale|accept|truncat|wrap|reorder|overwrit|duplicat|block|time)|break(s)? silently|fail(s|ing)? silently|(dropp|lost|lose|ignored|swallowed|discarded)\w* silently", text, re.I):
                reason = "machine-subject"
        elif pat.startswith("soft hype") and re.search(r"landscape", text, re.I):
            reason = "survey-term"
        elif pat.startswith("deliberate (adjective)") and re.search(r"deliberate (intermediate|transition|stage|state)", text, re.I):
            reason = "planned-stage"
        elif pat.startswith("exclamation") and re.search(r"Release It!", text):
            reason = "quoted"
        if reason:
            ledger[d].append((slide, pat, reason, text[:140]))
        else:
            unclassified.append((d, ln, slide, pat, text[:200]))
for u in unclassified:
    print("UNCLASSIFIED", *u, sep=" | ")
print(len(unclassified), "unclassified;", {d: len(v) for d, v in ledger.items()})
with open(VER / "watch-ledger.json", "w") as f:
    json.dump({"ledger": ledger, "unclassified": unclassified}, f, indent=1, ensure_ascii=False)
