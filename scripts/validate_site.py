#!/usr/bin/env python3
"""Static validation for the Jekyll site ("Validate before commit" in CLAUDE.md).

Checks _docs/*.md, _parts/*.md, _example_pages/*.md and index.html:

  1. front matter parses as YAML
  2. {% raw %} / {% endraw %} balance
  3. no `{{` outside raw blocks except legitimate Liquid output
  4. every codetabs include is followed by exactly len(langs) fenced blocks
  5. every excalidraw figure has assets/diagrams/<file>.svg and .excalidraw
  6. no positional terms in prose (outside code fences and inline code)

  7. no `podman` anywhere outside the historical plans
     (on by default; --allow-podman turns it off); lgtm-presentation/ is included
  8. no positional terms in lgtm-presentation/*.md and lgtm-presentation/text/*.md
  9. the stale-stack denylist (scripts/deck-denylist.json) over lgtm-presentation/text/*.md

Optional: --allow-podman, --fail-on-warn. Output is `path:line: message`. Exit 1 on errors.
Needs python3 stdlib and PyYAML.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SITE_GLOBS = ["_docs/*.md", "_parts/*.md", "_example_pages/*.md", "index.html"]

# Liquid output tags that Jekyll legitimately uses in these files. Anything
# else starting with `{{` is treated as an unguarded brace pair from code
# (Go/C++ composite literals, JSON) that Liquid would try to evaluate.
LIQUID_OK = re.compile(
    r"""\{\{-?\s*(?:
        (?:site|page|include|forloop|doc|part|part_docs|this_part|
           prev_\w+|next_\w+)\b      # variable families used in layouts/pages
      | content\b
      | ['"][^'"]*['"]\s*\|          # string literal piped to a filter
    )""",
    re.X,
)

# Positional language. CLAUDE.md: cross-reference the concept, not a position.
POSITIONAL = [
    ("above", re.compile(r"\babove\b", re.I)),
    ("below", re.compile(r"\bbelow\b", re.I)),
    ("next slide", re.compile(r"\bnext\s+slide\b", re.I)),
    ("previous slide", re.compile(r"\bprevious\s+slide\b", re.I)),
    ("previous section", re.compile(r"\bprevious\s+section\b", re.I)),
    ("following section", re.compile(r"\bfollowing\s+section\b", re.I)),
    ("see slide N", re.compile(r"\bsee\s+slide\s+\d+", re.I)),
    ("preceding", re.compile(r"\bpreceding\b", re.I)),
]

# Technical uses that are not document positions. Each is matched against the
# text right after the term (and a little before it) and suppresses the hit.
POSITIONAL_EXEMPT = [
    # numeric/threshold comparisons: "below 1024", "above 50%", "below zero"
    re.compile(r"\b(?:above|below)\s+(?:[$~<>]?\d|zero|the\s+(?:threshold|limit|cutoff|floor|ceiling))", re.I),
    # hyphenated compounds: "above-average"
    re.compile(r"\b(?:above|below)-\w+", re.I),
    # "at or above/below" a level, "above/below the line" in SLO text
    re.compile(r"\b(?:at\s+or|or)\s+(?:above|below)\b", re.I),
]

FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})")
RAW_RE = re.compile(r"\{%-?\s*raw\s*-?%\}|\{%-?\s*endraw\s*-?%\}")
INCLUDE_RE = re.compile(r"\{%-?\s*include\s+([\w./-]+)(.*?)-?%\}", re.S)
ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path: Path, line: int, msg: str) -> None:
        self.errors.append(f"{rel(path)}:{line}: {msg}")

    def warn(self, path: Path, line: int, msg: str) -> None:
        self.warnings.append(f"{rel(path)}:{line}: warning: {msg}")


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def split_front_matter(text: str) -> tuple[str | None, int]:
    """Return (front matter text or None, number of lines it occupies)."""
    if not text.startswith("---"):
        return None, 0
    m = re.match(r"---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", text, re.S)
    if not m:
        return "", -1  # opened but never closed
    return m.group(1), m.group(0).count("\n")


def mask_raw(text: str, path: Path, rep: Report) -> str:
    """Blank out everything inside raw blocks (tags included), keeping newlines."""
    out = list(text)
    depth_start = None
    for m in RAW_RE.finditer(text):
        is_open = "endraw" not in m.group(0)
        if is_open:
            if depth_start is not None:
                rep.error(path, line_of(text, m.start()), "nested or repeated {% raw %} (previous one at line "
                          f"{line_of(text, depth_start)} is still open)")
                continue
            depth_start = m.start()
        else:
            if depth_start is None:
                rep.error(path, line_of(text, m.start()), "{% endraw %} without matching {% raw %}")
                continue
            for i in range(depth_start, m.end()):
                if out[i] != "\n":
                    out[i] = " "
            depth_start = None
    if depth_start is not None:
        rep.error(path, line_of(text, depth_start), "{% raw %} is never closed")
        for i in range(depth_start, len(text)):
            if out[i] != "\n":
                out[i] = " "
    return "".join(out)


def check_liquid_braces(masked: str, path: Path, rep: Report) -> None:
    for m in re.finditer(r"\{\{", masked):
        if not LIQUID_OK.match(masked, m.start()):
            snippet = masked[m.start():m.start() + 30].split("\n")[0]
            rep.error(path, line_of(masked, m.start()),
                      f"unguarded `{{{{` outside {{% raw %}}: {snippet!r}")


def fenced_regions(lines: list[str]) -> list[tuple[int, int]]:
    """(start, end) 0-based inclusive line indexes of each fenced block."""
    regions, i = [], 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if m:
            marker = m.group(2)
            j = i + 1
            while j < len(lines):
                c = FENCE.match(lines[j])
                if c and c.group(2)[0] == marker[0] and len(c.group(2)) >= len(marker) \
                        and lines[j].strip() == c.group(2):
                    break
                j += 1
            regions.append((i, min(j, len(lines) - 1)))
            i = j + 1
        else:
            i += 1
    return regions


def strip_raw_tags(text: str) -> str:
    """Blank only the raw/endraw tags (same offsets). Liquid emits the content of
    a raw block verbatim and drops the tags, so fenced blocks wrapped in
    {% raw %} are still ordinary blocks in the Markdown that kramdown sees."""
    return RAW_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def check_codetabs(masked: str, rendered: str, path: Path, rep: Report, fm_lines: int) -> None:
    """Mirror assets/js/codetabs.js: after the marker, absorb consecutive fenced
    blocks (blank lines between them are skipped) until prose appears. The count
    must equal the number of `|`-separated langs, because extra blocks would be
    left outside the tab group and missing ones would swallow the wrong content."""
    # `masked` finds real includes (those inside raw blocks are documentation);
    # `rendered` (raw tags only removed) is what the Markdown parser sees.
    lines = rendered.split("\n")
    regions = fenced_regions(lines)
    starts = {s: e for s, e in regions}
    for m in INCLUDE_RE.finditer(masked):
        if m.group(1) != "codetabs.html":
            continue
        attrs = dict(ATTR_RE.findall(m.group(2)))
        ln = line_of(masked, m.start())
        langs = [x.strip() for x in attrs.get("langs", "").split("|") if x.strip()]
        if not langs:
            rep.error(path, ln, "codetabs include has no langs=")
            continue
        end_line = line_of(masked, m.end() - 1)  # 1-based line holding the closing %}
        i, blocks = end_line, 0  # i is 0-based index of the line after the tag
        while i < len(lines):
            if not lines[i].strip():
                i += 1
            elif i in starts:
                blocks += 1
                i = starts[i] + 1
            else:
                break
        if blocks != len(langs):
            rep.error(path, ln, f"codetabs langs has {len(langs)} entries "
                                f"({'|'.join(langs)}) but {blocks} fenced block(s) follow")


def check_figures(masked: str, path: Path, rep: Report) -> None:
    captions: dict[str, int] = {}
    for m in INCLUDE_RE.finditer(masked):
        if m.group(1) != "excalidraw.html":
            continue
        attrs = dict(ATTR_RE.findall(m.group(2)))
        ln = line_of(masked, m.start())
        name = attrs.get("file")
        if not name:
            rep.error(path, ln, "excalidraw include has no file=")
            continue
        for ext in (".svg", ".excalidraw"):
            if not (ROOT / "assets" / "diagrams" / f"{name}{ext}").is_file():
                rep.error(path, ln, f"figure assets/diagrams/{name}{ext} is missing")
        if not attrs.get("alt"):
            rep.warn(path, ln, f"figure {name} has no alt text")
        cap = attrs.get("caption")
        if cap:
            if cap in captions:
                rep.warn(path, ln, f"duplicate figure caption {cap!r} (first at line {captions[cap]})")
            captions.setdefault(cap, ln)


def prose_lines(text: str) -> list[tuple[int, str]]:
    """Prose lines: outside fenced code, outside Liquid tags, inline code removed."""
    # Blank Liquid tags in place (figure alt text and captions describe the
    # picture itself, e.g. "a band below reads ...", which is a visual layout and
    # not a cross-reference to other text), keeping the rest of the line.
    text = re.sub(r"\{%.*?%\}", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    lines = text.split("\n")
    skip = set()
    for s_, e_ in fenced_regions(lines):
        skip.update(range(s_, e_ + 1))
    out = []
    for i, line in enumerate(lines):
        if i in skip:
            continue
        line = re.sub(r"`[^`]*`", " ", line)          # inline code
        line = re.sub(r"<!--.*?-->", " ", line)       # html comments
        out.append((i + 1, line))
    return out


def check_positional(text: str, path: Path, rep: Report, fm_lines: int) -> None:
    for ln, line in prose_lines(text):
        if ln <= fm_lines:
            # front matter description/title are prose too, keep checking them
            pass
        for label, rx in POSITIONAL:
            for m in rx.finditer(line):
                ctx = line[max(0, m.start() - 4): m.end() + 20]
                if any(ex.search(ctx) for ex in POSITIONAL_EXEMPT):
                    continue
                rep.error(path, ln, f"positional term '{label}': ...{line.strip()[:100]}")


def check_file(path: Path, rep: Report) -> None:
    text = path.read_text(encoding="utf-8")
    fm, fm_lines = split_front_matter(text)
    if fm_lines == -1:
        rep.error(path, 1, "front matter opened with --- but never closed")
        fm_lines = 0
    elif fm is None:
        if path.suffix == ".md":
            rep.error(path, 1, "missing front matter")
    else:
        try:
            data = yaml.safe_load(fm)
            if not isinstance(data, dict):
                rep.error(path, 1, "front matter is not a mapping")
            elif "title" not in data and path.name != "index.html":
                rep.warn(path, 1, "front matter has no title")
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            rep.error(path, (mark.line + 2) if mark else 1, f"front matter does not parse: {exc}")
    masked = mask_raw(text, path, rep)
    check_liquid_braces(masked, path, rep)
    check_codetabs(masked, strip_raw_tags(text), path, rep, fm_lines)
    check_figures(masked, path, rep)
    check_positional(text, path, rep, fm_lines)


PODMAN_SKIP_DIRS = {"node_modules", ".git", "_site", ".bundle", "vendor"}
PODMAN_HISTORY = {
    "_plans/phase3-backlog.md",
    "_plans/qa-pass-r70.md",
    "_plans/second-pass-audit.md",
    "_plans/iteration-plan.md",
    "scripts/validate_site.py",
}
PODMAN_SCAN_ROOTS = ["examples", "assets/diagrams", "scripts", "_plans", "_docs", "lgtm-presentation",
                     "_parts", "_example_pages", ".github", "_includes", "_layouts"]
PODMAN_SCAN_SUFFIXES = {
    ".md", ".html", ".yml", ".yaml", ".py", ".sh", ".svg", ".excalidraw", ".json",
    # source and config files under examples/ and scripts/
    ".go", ".cs", ".java", ".cpp", ".h", ".hpp", ".rego", ".toml", ".properties", ".conf",
}
PODMAN_ROOT_FILES = ["_config.yml", "Gemfile"]


def check_podman(rep: Report, site_files: list[Path]) -> None:
    files = set(site_files)
    files.update(ROOT.glob("*.md"))
    files.update(ROOT.glob("*.html"))
    files.update(ROOT / name for name in PODMAN_ROOT_FILES if (ROOT / name).is_file())
    for sub in PODMAN_SCAN_ROOTS:
        base = ROOT / sub
        if base.is_dir():
            files.update(p for p in base.rglob("*") if p.is_file())
    for p in sorted(files):
        rel = p.relative_to(ROOT)
        if PODMAN_SKIP_DIRS & set(rel.parts) or rel.as_posix() in PODMAN_HISTORY:
            continue
        if p.suffix not in PODMAN_SCAN_SUFFIXES and p.name not in {"Containerfile", "Dockerfile", "Gemfile"} \
                and not p.name.startswith("Containerfile"):
            continue
        try:
            data = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        # A `dnf remove ...` command (with its backslash continuations) may name
        # the distribution's podman packages: removing them is the instruction.
        in_remove = False
        for i, line in enumerate(data.split("\n"), 1):
            if "dnf remove" in line:
                in_remove = True
            if in_remove:
                in_remove = line.rstrip().endswith("\\")
                continue
            if re.search(r"podman", line, re.I):
                rep.error(p, i, f"podman reference: {line.strip()[:100]}")


DECK_DENYLIST = ROOT / "scripts" / "deck-denylist.json"
DECK_MD_GLOBS = ["lgtm-presentation/*.md", "lgtm-presentation/text/*.md"]


def check_deck_markdown(rep: Report) -> None:
    """Positional language over the deck Markdown (text copies, companions, BUILD.md)."""
    for g in DECK_MD_GLOBS:
        for p in sorted(ROOT.glob(g)):
            check_positional(p.read_text(encoding="utf-8"), p, rep, 0)


def check_denylist(rep: Report) -> None:
    """Stale-stack denylist: every line of the deck text copies (code included).

    An entry is {id, regex, flags?, exempt?, files?, why}; a hit is an error unless the
    exemption matches the same line; `files` limits it to text copies whose name contains
    one of the given strings.
    """
    entries = json.loads(DECK_DENYLIST.read_text(encoding="utf-8"))
    rules = []
    for e in entries:
        fl = re.I if "i" in e.get("flags", "") else 0
        rules.append((e, re.compile(e["regex"], fl),
                      re.compile(e["exempt"], re.I) if e.get("exempt") else None))
    for p in sorted(ROOT.glob("lgtm-presentation/text/*.md")):
        for i, line in enumerate(p.read_text(encoding="utf-8").split("\n"), 1):
            for e, rx, ex in rules:
                if e.get("files") and not any(k in p.name for k in e["files"]):
                    continue
                if rx.search(line) and not (ex and ex.search(line)):
                    rep.error(p, i, f"denylist [{e['id']}] {e['why']}: {line.strip()[:100]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--allow-podman", action="store_true",
                    help="skip the check that fails on any 'podman' reference (on by default)")
    ap.add_argument("--fail-on-warn", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    files: list[Path] = []
    for g in SITE_GLOBS:
        files += sorted(ROOT.glob(g))
    rep = Report()
    for f in files:
        check_file(f, rep)
    if not args.allow_podman:
        check_podman(rep, files)
    check_deck_markdown(rep)
    check_denylist(rep)

    for line in rep.errors + rep.warnings:
        print(line)
    failed = bool(rep.errors) or (args.fail_on_warn and bool(rep.warnings))
    print(f"validate_site: {len(files)} files, {len(rep.errors)} error(s), "
          f"{len(rep.warnings)} warning(s)", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
