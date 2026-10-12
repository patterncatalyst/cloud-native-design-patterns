#!/usr/bin/env python3
"""Dry-run every edits file against a copy of its deck, then apply to a scratch copy and scan the result.

Run from anywhere with the S12 venv python. Writes M/verify/<deck>.{dryrun.txt,after.pptx,md} and prints a table.
"""
import json, re, shutil, subprocess, sys
from pathlib import Path
REPO = Path("~/Dev/cloud-native-design-patterns")
M = Path(__file__).resolve().parent.parent
V = str(M.parent / "venv" / "bin" / "python")
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deck_text  # noqa: E402
from hits import POS, EX  # noqa: E402
EDITS = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "lgtm-presentation" / "edits"
OUT = M / "verify"
OUT.mkdir(exist_ok=True)
LANG = [f"Designing-Cloud-Native-APIs-{x}" for x in ("Python", "Quarkus", "Spring", "DotNet", "Go", "Cpp")]
POLICY = ["K8s-Environment-Access-Policies", "Network-Policy-Process-Advisory"]
DENY = json.loads((REPO / "_plans/s12-manifest/denylist.json").read_text()) if (REPO / "_plans/s12-manifest/denylist.json").exists() else []
rows = []
for d in LANG + POLICY:
    src = REPO / "lgtm-presentation" / f"{d}.pptx"
    copy = OUT / f"{d}.pptx"
    shutil.copy2(src, copy)
    files = ([str(EDITS / "_shared.json")] if d in LANG else []) + [str(EDITS / f"{d}.json")]
    dr = subprocess.run([V, str(REPO / "scripts/deck_edit.py"), str(copy), *files, "--dry-run"],
                        cwd=REPO, capture_output=True, text=True)
    (OUT / f"{d}.dryrun.txt").write_text(dr.stdout + dr.stderr)
    ok_dry = dr.returncode == 0 and '"ok": true' in dr.stdout
    after = OUT / f"{d}.after.pptx"
    ap = subprocess.run([V, str(REPO / "scripts/deck_edit.py"), str(copy), *files, "--out", str(after)],
                        cwd=REPO, capture_output=True, text=True)
    md, _ = deck_text.pptx_to_md(after) if ap.returncode == 0 else ("", None)
    mdp = OUT / f"{d}.md"
    mdp.write_text(md)
    scan = lambda tier: subprocess.run(["bash", str(REPO / "scripts/voice/scan.sh"), "--tier", tier, "--hits", "all", str(mdp)],
                                       capture_output=True, text=True).stdout
    ban = scan("ban"); watch = scan("watch")
    nb = len([l for l in ban.splitlines() if re.match(r"^\S+:\d+:", l)])
    nw = len([l for l in watch.splitlines() if re.match(r"^\S+:\d+:", l)])
    # positional + engine + denylist over prose lines (code fences skipped for positional)
    pos = eng = 0; deny = []
    fence = False
    for i, line in enumerate(md.split("\n"), 1):
        if line.startswith("```"):
            fence = not fence
        if re.search("p" + "odman", line, re.I):
            eng += 1
        for e in DENY:
            if e.get("files") and not any(f in d for f in e["files"]):
                continue
            if re.search(e["regex"], line, re.I if "i" in e.get("flags", "") else 0):
                if e.get("exempt") and re.search(e["exempt"], line, re.I):
                    continue
                deny.append(f"{e['id']}:{i}:{line.strip()[:90]}")
        if fence:
            continue
        l2 = re.sub(r"`[^`]*`", " ", line)
        for rx in POS:
            for m in rx.finditer(l2):
                ctx = l2[max(0, m.start() - 4): m.end() + 20]
                if not any(x.search(ctx) for x in EX):
                    pos += 1
    (OUT / f"{d}.ban.txt").write_text(ban); (OUT / f"{d}.watch.txt").write_text(watch)
    (OUT / f"{d}.deny.txt").write_text("\n".join(deny))
    nslides = md.count("\n## [")
    rows.append((d, ok_dry, ap.returncode == 0, nslides, nb, nw, pos, eng, len(deny)))
print(f"{'deck':42} dry  apply slides ban watch pos engine deny")
for r in rows:
    print(f"{r[0]:42} {str(r[1]):5} {str(r[2]):5} {r[3]:6} {r[4]:3} {r[5]:5} {r[6]:3} {r[7]:6} {r[8]:4}")
