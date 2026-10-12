#!/usr/bin/env python3
"""S12 fix round A: build the fixup op lists with measured counts.

    fixA_build.py [--write] [deck ...]

For each language deck the base is the deck as it is (or, for Go and C++, will be) committed:
Python, Quarkus, Spring, .NET = the committed .pptx with its existing fix files; Go, C++ = the
pre-S12 committed .pptx with _shared.json + the deck JSON *without* any fixA ops applied. On that
base the builder applies, in order:

  1. the base ops of fixA_rules (Q.fix1 / Q.fix2 for Quarkus, the cross-deck capsfix ops for the
     other five), replace counts re-measured (an op that no longer matches is dropped and listed);
  2. the content ops of fixA_rules (figure, code accuracy, notes drift, advisory, polish);
  3. the caps pairs of fixA_rules: each (find, repl) is located on every slide and notes body, and
     one replace op per scope is emitted with the slide ids and the measured count;
  4. one recolour_code op per code box that colour_audit still flags.

--write writes lgtm-presentation/edits/<deck>.fixN.json (committed decks) or appends the ops to
the deck JSON (Go, C++; ops tagged "_fixA"), and writes the scratch result to $FIXA/<deck>.pptx.
Run with the S12 venv python from the repository root.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deck_edit as de  # noqa: E402
import colour_audit  # noqa: E402
import fixA_rules as R  # noqa: E402
from pptx import Presentation  # noqa: E402

FIXA = Path(os.environ.get("FIXA", "/tmp/claude-1000/-home-rsedor-Dev/0dea024d-0bf0-4ae5-bddd-7dec0cf60b22/scratchpad/s12/fixA"))
EDITS = REPO / "lgtm-presentation" / "edits"
COMMITTED = {"Python": "d51c29f", "Quarkus": "40db0f0", "Spring": "94b7ec5", "DotNet": "99c5bf5"}
OUTFILE = {"Python": "fix1", "Quarkus": "fix1", "Spring": "fix2", "DotNet": "fix2"}


def name(d):
    return f"Designing-Cloud-Native-APIs-{d}"


def base_deck(d):
    """Path of the deck the fixA ops apply to."""
    out = FIXA / "base" / f"{d}.pptx"
    out.parent.mkdir(parents=True, exist_ok=True)
    pptx = REPO / "lgtm-presentation" / f"{name(d)}.pptx"
    if d in COMMITTED:
        subprocess.run(["cp", str(pptx), str(out)], check=True)
        return out
    jf = EDITS / f"{name(d)}.json"
    ops = [o for o in json.loads(jf.read_text())["ops"] if not o.get("_fixA")]
    tmp = FIXA / "base" / f"{d}.nofixA.json"
    tmp.write_text(json.dumps({"ops": ops}))
    r = subprocess.run([sys.executable, str(REPO / "scripts/deck_edit.py"), str(pptx), str(EDITS / "_shared.json"),
                        str(tmp), "--out", str(out)], cwd=REPO, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{d}: base apply failed: {r.stderr[-800:]}")
    return out


def count_replace(ctx, op):
    """Apply a replace op and return its real count (no expect check)."""
    o = dict(op, expect=0)
    try:
        de.op_replace(ctx, o)
        return 0
    except de.EditError as e:
        msg = str(e)
        return int(msg.rsplit("found ", 1)[1])


def locate_pair(ctx, find, repl, sids=None, scopes=("slide", "notes")):
    """Apply find->repl everywhere (or on sids); return ops with sldIds and counts."""
    ops = []
    for scope in scopes:
        hits, total = [], 0
        for s in ctx.prs.slides:
            if sids is not None and s.slide_id not in sids:
                continue
            roots = []
            if scope == "slide":
                roots.append(s._element)
            else:
                for r in de.notes_roots(s):
                    for sp in de.all_sps(r):
                        ph = sp.find(f"{de.q(de.P, 'nvSpPr')}/{de.q(de.P, 'nvPr')}/{de.q(de.P, 'ph')}")
                        if ph is not None and ph.get("type") == "body":
                            roots.append(sp)
            n = 0
            for root in roots:
                for p in root.iter(de.q(de.A, "p")):
                    n += de.replace_in_paragraph(p, find, repl, f"sldId {s.slide_id}", ctx.log)
            if n:
                hits.append(s.slide_id)
                total += n
        if total:
            ops.append({"op": "replace", "scope": scope, "sldIds": hits, "find": find, "repl": repl,
                        "expect": total})
    return ops


FOUND = {}


def code_subst(ctx, op):
    """Turn {"op": "code_subst", "sldId", "subst": [[old line, [new lines]], ...]} into a set_code
    op with the box's current lines, each old line (exact, once) replaced."""
    s = ctx.slide(op["sldId"])
    sp = de.select_sp(s._element, op, kind="code")
    lines = [l["text"] for l in de.code_lines(sp.find(de.q(de.P, "txBody")))]
    for old, new in op["subst"]:
        idx = [i for i, l in enumerate(lines) if l == old]
        if len(idx) != 1:
            raise SystemExit(f"code_subst sldId {op['sldId']}: {old!r} found {len(idx)} times")
        lines[idx[0]:idx[0] + 1] = new
    o = {"op": "set_code", "sldId": op["sldId"], "lines": lines}
    for k in ("shape", "shape_id", "pt", "line_spacing", "cat", "_why"):
        if k in op:
            o[k] = op[k]
    return o


def run_op(ctx, op):
    de.OPS[op["op"]](ctx, op)


def build(d, report):
    base = base_deck(d)
    prs = Presentation(str(base))
    ctx = de.Ctx(prs)
    out = []
    # 1 + 2: base and content ops (replace counts re-measured)
    for src, op in R.base_ops(d) + R.content_ops(d):
        if op["op"] == "replace" and op.get("locate"):
            meta = {k: v for k, v in op.items() if k in ("cat", "_why")}
            scopes = (op["scope"],) if op.get("scope") else ("slide", "notes")
            found = locate_pair(ctx, op["find"], op["repl"], None, scopes)
            FOUND.setdefault(("content", op["find"]), []).extend([d] if found else [])
            for o in found:
                out.append(dict(o, **meta, _src=src))
            continue
        if op["op"] == "code_subst":
            op = code_subst(ctx, op)
        if op["op"] == "replace":
            n = count_replace(ctx, op)
            if n == 0:
                report.append(f"{d}: dropped ({src}, no match): {op['find'][:70]!r}")
                continue
            if n != op["expect"]:
                report.append(f"{d}: re-measured ({src}): {op['find'][:60]!r} {op['expect']} -> {n}")
            out.append(dict(op, expect=n, _src=src))
        else:
            run_op(ctx, op)
            out.append(dict(op, _src=src))
    # 3: caps pairs
    for find, repl, sids in R.caps_pairs(d):
        ops = locate_pair(ctx, find, repl, sids)
        FOUND.setdefault(("caps", find), []).extend([d] if ops else [])
        for o in ops:
            out.append(dict(o, cat="voice", _src="caps"))
    # 4: recolour every code box the audit still flags
    tmp = FIXA / "base" / f"{d}.pre-recolour.pptx"
    prs.save(str(tmp))
    boxes = sorted({(h["sldId"], h["shape_id"]) for h in colour_audit.audit(tmp)})
    for sid, shid in boxes:
        # allow_noop: replaying the whole chain with the fixed set_code already colours most of
        # these boxes; the op then only has to hold, not to change anything
        op = {"op": "recolour_code", "sldId": sid, "shape_id": shid, "allow_noop": True, "cat": "code",
              "_src": "colour"}
        run_op(ctx, op)
        out.append(op)
    res = FIXA / f"{d}.pptx"
    prs.save(str(res))
    return out, res, base


def main(argv):
    write = "--write" in argv
    decks = [a for a in argv if not a.startswith("--")] or ["Python", "Quarkus", "Spring", "DotNet", "Go", "Cpp"]
    report = []
    for d in decks:
        ops, res, base = build(d, report)
        cats = {}
        for o in ops:
            cats[o["_src"]] = cats.get(o["_src"], 0) + 1
        print(f"{d}: {len(ops)} ops {cats} -> {res}")
        if write:
            if d in COMMITTED:
                f = EDITS / f"{name(d)}.{OUTFILE[d]}.json"
                f.write_text(json.dumps({"ops": ops}, indent=1, ensure_ascii=False) + "\n")
            else:
                f = EDITS / f"{name(d)}.json"
                data = json.loads(f.read_text())
                data["ops"] = [o for o in data["ops"] if not o.get("_fixA")] + [dict(o, _fixA=True) for o in ops]
                f.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            print(f"  wrote {f.relative_to(REPO)}")
    for (kind, find), ds in FOUND.items():
        if not ds:
            report.append(f"{kind} rule matched in no deck: {find!r}")
    for r in report:
        print("  " + r)
    hits = {}
    for (kind, find), ds in FOUND.items():
        for x in ds:
            hits[x] = hits.get(x, 0) + 1
    print("  rules matched per deck:", hits)


if __name__ == "__main__":
    main(sys.argv[1:])
