#!/usr/bin/env python3
"""Check rewrite files (rewrites/*.json or any list of {find, repl, cat, decks?}) and op files.

    check_rewrites.py FILE.json [FILE.json ...]

For a rewrite list: every find must occur in at least one non-code segment of its decks (all six
language decks when "decks" is absent; "allow_code": true also allows code segments), and every
repl must have no ban-tier, positional or old-engine hit. Watch-tier hits in a repl are printed as
warnings (allowed only with a reason in "_keep"). For an ops file ({"ops": [...]}) the same text
checks run on every replace repl, set_text/set_notes paragraph and set_code line (code lines are
checked for the old engine only). Exit 1 on any error.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hits import pats, POS, EX, ENG, segs  # noqa: E402

LANG = [d for d in segs if d.startswith("Designing")]


def text_problems(t, code=False):
    errs, warns = [], []
    if ENG.search(t):
        errs.append("old engine name")
    if code:
        return errs, warns
    for tier, label, rx in pats:
        if rx.search(t):
            (errs if tier == "ban" else warns).append(f"{tier}:{label}")
    for rx in POS:
        for m in rx.finditer(t):
            ctx = t[max(0, m.start() - 4): m.end() + 20]
            if not any(e.search(ctx) for e in EX):
                errs.append("positional:" + m.group(0))
    return errs, warns


def main(paths):
    bad = 0
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        ops = data.get("ops") if isinstance(data, dict) else data
        is_rewrites = isinstance(data, list)
        for i, r in enumerate(ops):
            where = f"{path}#{i}"
            texts = []
            if is_rewrites or r.get("op") == "replace":
                if not r.get("find"):
                    print(f"ERROR {where}: empty find"); bad += 1; continue
                if r.get("find") == r.get("repl"):
                    print(f"ERROR {where}: find == repl"); bad += 1
                texts.append((r.get("repl", ""), bool(r.get("allow_code"))))
                if is_rewrites:
                    decks = r.get("decks", LANG)
                    found = any(r["find"] in s["text"] for d in decks for s in segs.get(d, [])
                                if (not s["code"] or r.get("allow_code")))
                    if not found:
                        print(f"ERROR {where}: find not in any segment of {decks if 'decks' in r else 'the six decks'}: {r['find'][:90]!r}")
                        bad += 1
            elif r.get("op") in ("set_text", "set_notes"):
                texts += [(p, False) for p in r.get("paragraphs", [])] + ([(r["text"], False)] if "text" in r else [])
            elif r.get("op") == "set_code":
                texts += [(ln, True) for ln in r.get("lines", [])]
                for ln in r.get("lines", []):
                    if len(ln) > 95:
                        print(f"ERROR {where}: code line over 95 columns ({len(ln)}): {ln[:60]!r}"); bad += 1
                if len(r.get("lines", [])) > 22:
                    print(f"WARN  {where}: {len(r['lines'])} code lines (deck_edit allows more only if the box had more)")
            for t, code in texts:
                errs, warns = text_problems(t, code)
                for e in errs:
                    print(f"ERROR {where}: {e}: {t[:110]!r}"); bad += 1
                for w in warns:
                    if not r.get("_keep"):
                        print(f"WARN  {where}: {w}: {t[:110]!r}")
    print(f"check_rewrites: {bad} error(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
