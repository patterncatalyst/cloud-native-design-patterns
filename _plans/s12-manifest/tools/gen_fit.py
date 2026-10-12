#!/usr/bin/env python3
"""Layout-fit amendment of the language-deck edit files (S12, step "layout fit").

    gen_fit.py apply   [deck ...]     plan files -> lgtm-presentation/edits/<deck>.json
    gen_fit.py suggest <deck> <after.pptx> <flags.json>
                                      print plan entries for the deck_fit.py flags of an
                                      after-edit copy (chips, font fits, frame growth); code
                                      that does not fit at 9 pt and other manual cases are
                                      listed as "manual"

Run with the S12 venv python from the repository root. The base of every deck file is its
committed pre-fit version (git show FIT_BASE:<path>, FIT_BASE defaults to c70ab3a), so `apply` is
idempotent. Plan: _plans/s12-manifest/fit/<deck>.json, {"entries": [...]}; an entry is one of

  {"sldId": N, "shape_id": M, "pt": 11, "line_spacing": 1.0}
        font fit. When the deck file has a set_code op for that box, "pt" (and "line_spacing")
        are added to it; otherwise a fit_font op is appended.
  {"sldId": N, "shape_id": M, "lines": [...], "pt": 10}
        replacement lines for the deck file's set_code op for that box, or an appended set_code op.
  {"sldId": N, "shape_id": M, "cuts": [{"from": a, "to": b, "first": "...", "ellipsis": "# ..."}],
   "edits": [{"line": i, "old": "...", "new": "..."}], "pt": 9, "line_spacing": 1.0}
        excerpt. Applied to the lines of the deck file's set_code op for that box (edits, which
        only reword comments, are allowed there), or appended as a cut_code op that keeps the
        formatting of the remaining lines (code the edits do not touch).
  {"sldId": N, "shape_id": M, "resize": {"cx": 2400000, "keep": "right"}}
        frame change; appends a resize_shape op.
  {"op": ...}
        any deck_edit op, appended as given (title and bullet shortening by replace).

Every op this tool adds or changes carries "cat": "fit" and "_fit" (the reason); appended ops go
after the Appendix R ops, at the end of the file.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLANS = REPO / "_plans" / "s12-manifest" / "fit"
EDITS = REPO / "lgtm-presentation" / "edits"
BASE = __import__("os").environ.get("FIT_BASE", "c70ab3a")
LANG = [f"Designing-Cloud-Native-APIs-{x}" for x in ("Python", "Quarkus", "Spring", "DotNet", "Go", "Cpp")]


def base_ops(deck):
    rel = f"lgtm-presentation/edits/{deck}.json"
    txt = subprocess.run(["git", "show", f"{BASE}:{rel}"], cwd=REPO, check=True,
                         capture_output=True, text=True).stdout
    return json.loads(txt)


def apply(decks):
    for deck in decks:
        plan_p = PLANS / f"{deck}.json"
        if not plan_p.exists():
            print(f"{deck}: no plan")
            continue
        plan = json.loads(plan_p.read_text())["entries"]
        data = base_ops(deck)
        ops = data["ops"]
        tail = []
        amended = appended = 0
        for e in plan:
            why = e.get("_why", "layout fit")
            if "op" in e:
                o = {k: v for k, v in e.items() if not k.startswith("_")}
                o.update({"cat": "fit", "_fit": why})
                tail.append(o)
                appended += 1
                continue
            sid, shid = e["sldId"], e["shape_id"]
            sc = [o for o in ops if o.get("op") == "set_code" and o.get("sldId") == sid
                  and o.get("shape_id") == shid]
            if len(sc) > 1:
                raise SystemExit(f"{deck}: {len(sc)} set_code ops for {sid}/{shid}")
            if "cuts" in e:
                if sc:
                    o = sc[0]
                    src = list(o["lines"]) if "lines" in o else o["code"].rstrip("\n").split("\n")
                    src = [ln.replace("\t", "    ").rstrip() for ln in src]
                    for ed in e.get("edits", []):
                        i = int(ed["line"]) - 1
                        if src[i] != ed["old"].rstrip():
                            raise SystemExit(f"{deck} {sid}/{shid}: edit line {i + 1} is {src[i]!r}, not {ed['old']!r}")
                        src[i] = ed["new"]
                    new, drop, ins = [], set(), {}
                    for c in e["cuts"]:
                        a, b = int(c["from"]), int(c.get("to", c["from"]))
                        if src[a - 1] != c["first"].rstrip():
                            raise SystemExit(f"{deck} {sid}/{shid}: line {a} is {src[a - 1]!r}, not {c['first']!r}")
                        drop.update(range(a - 1, b))
                        if c.get("ellipsis"):
                            ins[a - 1] = c["ellipsis"]
                    for i, ln in enumerate(src):
                        if i in ins:
                            new.append(ins[i])
                        if i not in drop:
                            new.append(ln)
                    o["lines"] = new
                    o.pop("code", None)
                    for k in ("pt", "line_spacing"):
                        if e.get(k) is not None:
                            o[k] = e[k]
                    o["_fit"] = why
                    amended += 1
                else:
                    if e.get("edits"):
                        raise SystemExit(f"{deck} {sid}/{shid}: edits need a set_code op")
                    o = {"op": "cut_code", "sldId": sid, "shape_id": shid, "cuts": e["cuts"]}
                    for k in ("pt", "line_spacing"):
                        if e.get(k) is not None:
                            o[k] = e[k]
                    o.update({"cat": "fit", "_fit": why})
                    tail.append(o)
                    appended += 1
            elif "resize" in e:
                o = {"op": "resize_shape", "sldId": sid, "shape_id": shid, **e["resize"],
                     "cat": "fit", "_fit": why}
                tail.append(o)
                appended += 1
            elif "lines" in e:
                if sc:
                    o = sc[0]
                    o["lines"] = list(e["lines"])
                    o.pop("code", None)
                else:
                    o = {"op": "set_code", "sldId": sid, "shape_id": shid, "lines": list(e["lines"]), "cat": "fit"}
                    tail.append(o)
                    appended += 1
                for k in ("pt", "line_spacing", "max_lines"):
                    if e.get(k) is not None:
                        o[k] = e[k]
                o["_fit"] = why
                amended += bool(sc)
            elif "pt" in e:
                if sc:
                    o = sc[0]
                    o["pt"] = e["pt"]
                    if e.get("line_spacing") is not None:
                        o["line_spacing"] = e["line_spacing"]
                    o["_fit"] = why
                    amended += 1
                else:
                    o = {"op": "fit_font", "sldId": sid, "shape_id": shid, "pt": e["pt"]}
                    if e.get("line_spacing") is not None:
                        o["line_spacing"] = e["line_spacing"]
                    o.update({"cat": "fit", "_fit": why})
                    tail.append(o)
                    appended += 1
            else:
                raise SystemExit(f"{deck}: entry without pt, lines, resize or op: {e}")
        ops.extend(tail)
        (EDITS / f"{deck}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        print(f"{deck}: {len(plan)} plan entries; {amended} set_code ops amended, {appended} ops appended")


# ----------------------------------------------------------------- suggestions

def suggest(deck, pptx, flags_p):
    sys.path.insert(0, str(REPO / "scripts"))
    import deck_edit as de  # noqa: E402
    from pptx import Presentation  # noqa: E402
    q, A, P = de.q, de.A, de.P
    prs = Presentation(pptx)
    sw, sh = prs.slide_width, prs.slide_height
    slides = {s.slide_id: s for s in prs.slides}
    flags = json.loads(Path(flags_p).read_text())
    by = {}
    for f in flags:
        by.setdefault((f["sldId"], f["shape_id"]), []).append(f)
    out, manual = [], []

    def frame(e):
        xf = e.find(f".//{q(A, 'xfrm')}")
        if xf is None or xf.find(q(A, "off")) is None:
            return None
        o, x = xf.find(q(A, "off")), xf.find(q(A, "ext"))
        return [int(o.get("x")), int(o.get("y")), int(o.get("x")) + int(x.get("cx")), int(o.get("y")) + int(x.get("cy"))]

    def ins(e):
        b = e.find(f"{q(P, 'txBody')}/{q(A, 'bodyPr')}")
        g = (lambda k, d: int(b.get(k, d))) if b is not None else (lambda k, d: d)
        return g("lIns", 91440), g("tIns", 45720), g("rIns", 91440), g("bIns", 45720)

    for (sid, shid), fs in sorted(by.items(), key=lambda kv: (kv[1][0]["slide"], kv[0][1] or 0)):
        num = fs[0]["slide"]
        kinds = {f["kind"].split("-with")[0]: f["by_pt"] for f in fs}
        if shid is None:
            manual.append((num, sid, shid, fs))
            continue
        s = slides[sid]
        sp = next((e for e in s._element.iter(q(P, "sp")) if de.sp_id(e) == shid), None)
        if sp is None:
            manual.append((num, sid, shid, fs))
            continue
        tx = sp.find(q(P, "txBody"))
        paras = [de.ptext(p) for p in tx.findall(q(A, "p"))]
        fonts = {de.run_font(r) for r in tx.iter(q(A, "r"))} - {None}
        mono = bool(fonts) and all(de.MONO_RE.search(f) for f in fonts)
        sizes = [de.run_size(r) for r in tx.iter(q(A, "r")) if de.run_size(r)]
        cur = max(sizes or [1800]) / 100
        fr = frame(sp)
        li, ti, ri, bi = ins(sp)
        if mono and len([ln for ln in de.code_lines(tx) if ln["text"].strip()]) == 1:
            # chip: one line wide enough for its text, right edge kept
            text = next(ln["text"] for ln in de.code_lines(tx) if ln["text"].strip())
            need = int((len(text) * 0.6 * cur + 4) * 12700) + li + ri
            if need > fr[2] - fr[0]:
                out.append({"sldId": sid, "shape_id": shid, "resize": {"cx": need, "keep": "right"},
                            "_why": f"slide {num}: chip '{text}' wraps; one line at {cur} pt"})
            else:
                manual.append((num, sid, shid, fs))
            continue
        if mono:
            lines = de.code_lines(tx)
            n = len(lines)
            wide = max(len(l["text"].replace("\t", "    ").rstrip()) for l in lines)
            spcs = [int(e.get("val")) / 100000 for e in tx.iter(q(A, "spcPct"))]
            spc = max(spcs) if spcs else 1.0
            h = (fr[3] - fr[1] - ti) / 12700
            w = (fr[2] - fr[0] - li - ri) / 12700

            def fits(pt, sp_):
                return n <= math.floor((h - 1.32 * pt) / (pt * 1.2 * sp_) + 1.02) and wide <= math.floor(w / (pt * 0.6))
            got = None
            pt = cur
            while pt >= 9 and got is None:
                if fits(pt, spc) and pt < cur:
                    got = (pt, None)
                pt -= 0.5
            pt = max(cur, 9.0)
            while pt >= 9 and got is None and spc > 1.0:
                if fits(pt, 1.0):
                    got = (pt, 1.0)
                pt -= 0.5
            if got and got[0] >= 9:
                e = {"sldId": sid, "shape_id": shid, "pt": got[0],
                     "_why": f"slide {num}: {n} code lines, {wide} columns; {cur} pt overflows the box"}
                if got[1]:
                    e["line_spacing"] = got[1]
                out.append(e)
            else:
                manual.append((num, sid, shid, fs + [{"kind": f"needs excerpt: {n} lines, {wide} cols, "
                                                      f"{math.floor((h - 1.32 * 9) / (9 * 1.2) + 1.02)} lines fit at 9 pt"}]))
            continue
        # text: grow the frame into free space, else shrink
        top = kinds.get("overflow-top", 0)
        bot = kinds.get("overflow-bottom", 0)
        right = kinds.get("overflow-right", 0)
        others = [k for k in kinds if k not in ("overflow-top", "overflow-bottom", "overflow-right")]
        if not (top or bot or right) or others and not all(k.startswith("collision") for k in others):
            manual.append((num, sid, shid, fs))
            continue
        m = int(3 * 12700)
        upper, lower = 0, sh
        for e in s._element.iter(q(P, "sp"), q(P, "pic"), q(P, "graphicFrame"), q(P, "cxnSp")):
            if e is sp:
                continue
            of = frame(e)
            if of is None:
                continue
            if of[0] <= fr[0] and of[1] <= fr[1] and of[2] >= fr[2] and of[3] >= fr[3]:
                continue  # a container (backdrop, full-slide picture)
            if of[2] - of[0] >= sw * 0.95 and of[3] - of[1] >= sh * 0.95:
                continue
            if min(of[2], fr[2] + (int(right * 12700) + m if right else 0)) <= max(of[0], fr[0]):
                continue  # not in the same column
            if of[1] >= fr[1] + (fr[3] - fr[1]) // 2:
                lower = min(lower, of[1] - 12700)      # below (or overlapping from below)
            elif of[3] <= fr[1] + (fr[3] - fr[1]) // 2:
                upper = max(upper, of[3] + 12700)      # above
        need = (fr[3] - fr[1]) + (int(top * 12700) + m if top else 0) + (int(bot * 12700) + m if bot else 0)
        y0 = fr[1] - (int(top * 12700) + m if top else 0)
        y1 = y0 + need
        if y1 > lower:
            y1, y0 = lower, lower - need
        nf = [fr[0], y0, fr[2] + (int(right * 12700) + m if right else 0), y1]
        blocked = [] if y0 >= upper else ["above"]
        if nf[1] >= 0 and nf[3] <= sh and nf[2] <= sw and not blocked:
            r = {}
            if nf[1] != fr[1]:
                r["y"] = nf[1]
            r["cy"] = nf[3] - nf[1]
            if nf[2] != fr[2]:
                r["cx"] = nf[2] - nf[0]
            out.append({"sldId": sid, "shape_id": shid, "resize": r,
                        "_why": f"slide {num}: text overflows its frame by "
                                + ", ".join(f"{k} {v} pt" for k, v in kinds.items() if k.startswith("overflow"))
                                + "; free space around the frame"})
        else:
            hh = (fr[3] - fr[1]) / 12700
            guess = math.floor(cur * math.sqrt(hh / (hh + top + bot + 0.0001)) * 2) / 2
            out.append({"sldId": sid, "shape_id": shid, "pt": guess,
                        "_why": f"slide {num}: text overflows by {top + bot} pt and the frame cannot grow; "
                                f"{cur} pt -> {guess} pt", "_auto_shrink": True})
    return out, manual


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "apply":
        apply(sys.argv[2:] or LANG)
    elif len(sys.argv) == 5 and sys.argv[1] == "suggest":
        o, m = suggest(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps({"entries": o, "manual": [{"slide": a, "sldId": b, "shape_id": c, "flags": d}
                                                   for a, b, c, d in m]}, indent=1, ensure_ascii=False))
    else:
        print(__doc__)
        sys.exit(2)
