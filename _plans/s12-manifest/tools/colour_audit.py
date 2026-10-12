#!/usr/bin/env python3
"""Code-colour audit for the language decks (S12 fix round A).

    colour_audit.py <deck.pptx> [--parent <parent.pptx>] [--json]

Rule (the house code style of the decks): in a code box, a whole-line comment (# // -- /* *) is
the comment green 8FB98F and every other non-blank line is E6E6E6; a trailing comment that sits in
its own run on a code line may be green. Chips (one short monospace line) and the grey 8A8A8A
chip labels are not code boxes and are skipped.

Reports every line that breaks the rule as
    <slide no> sldId <id> shape <id> line <n> <kind> <text>
kind: code-as-comment (a code line with a green run that is not a trailing comment),
comment-as-code (a comment line with an E6E6E6 run), other-colour (a run of any other colour in a
code box). With --parent, each hit is marked "new" or "pre-existing" (the same sldId, shape id and
line text with the same colours in the parent deck). Exit 1 when a hit is found.
Run with the S12 venv python (python-pptx).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import deck_edit as de  # noqa: E402
from pptx import Presentation  # noqa: E402

A = de.A
CODE, COMMENT = "E6E6E6", "8FB98F"
CHIP_GREY = "8A8A8A"


def colour(r):
    rpr = r.find(de.q(A, "rPr"))
    sf = rpr.find(de.q(A, "solidFill")) if rpr is not None else None
    if sf is None or not len(sf):
        return "inherited"
    return sf[0].get("val") or sf[0].tag.split("}")[1]


def box_lines(tx):
    """Lines of a code box as lists of (text, colour) segments (runs split at embedded newlines
    and at a:br)."""
    lines = []
    for p in tx.findall(de.q(A, "p")):
        cur = []
        for c in p:
            if c.tag == de.q(A, "r"):
                parts = (c.findtext(de.q(A, "t")) or "").split("\n")
                for k, part in enumerate(parts):
                    if k > 0:
                        lines.append(cur)
                        cur = []
                    cur.append((part, colour(c)))
            elif c.tag == de.q(A, "br"):
                lines.append(cur)
                cur = []
        lines.append(cur)
    return lines


def line_hits(segs):
    text = "".join(t for t, _ in segs)
    if not text.strip():
        return []
    hits = []
    if de.is_comment(text):
        for t, c in segs:
            if t.strip() and c == CODE:
                hits.append("comment-as-code")
            elif t.strip() and c not in (CODE, COMMENT):
                hits.append(f"other-colour:{c}")
    else:
        seen_code = False
        for t, c in segs:
            if not t.strip():
                continue
            trailing = seen_code and de.is_comment(t)
            if c == COMMENT and not trailing:
                hits.append("code-as-comment")
            elif c not in (CODE, COMMENT):
                hits.append(f"other-colour:{c}")
            if not de.is_comment(t):
                seen_code = True
    return sorted(set(hits))


def boxes(path):
    prs = Presentation(str(path))
    for n, s in enumerate(prs.slides, 1):
        for sp in de.all_sps(s._element):
            tx = sp.find(de.q(de.P, "txBody"))
            if tx is None or not de.is_code_sp(sp):
                continue
            ls = box_lines(tx)
            nonblank = [l for l in ls if "".join(t for t, _ in l).strip()]
            if len(nonblank) == 1 and all(c == CHIP_GREY for t, c in nonblank[0] if t.strip()):
                continue  # a long chip label
            yield n, s.slide_id, de.sp_id(sp), ls


def audit(path):
    out = []
    for n, sid, shid, ls in boxes(path):
        for i, segs in enumerate(ls, 1):
            for kind in line_hits(segs):
                out.append({"slide": n, "sldId": sid, "shape_id": shid, "line": i, "kind": kind,
                            "text": "".join(t for t, _ in segs),
                            "colours": [c for t, c in segs if t.strip()]})
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("deck", type=Path)
    ap.add_argument("--parent", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    hits = audit(a.deck)
    if a.parent:
        old = {(h["sldId"], h["shape_id"], h["text"], tuple(h["colours"])) for h in audit(a.parent)}
        for h in hits:
            h["origin"] = "pre-existing" if (h["sldId"], h["shape_id"], h["text"], tuple(h["colours"])) in old else "new"
    if a.json:
        print(json.dumps(hits, indent=1))
    else:
        for h in hits:
            print(f"{h['slide']:3d} sldId {h['sldId']} shape {h['shape_id']} line {h['line']:2d} {h['kind']}"
                  + (f" [{h['origin']}]" if "origin" in h else "") + f" {h['text'][:90]!r}")
        print(f"colour_audit: {a.deck.name}: {len(hits)} hit(s) on "
              f"{len({h['sldId'] for h in hits})} slide(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
