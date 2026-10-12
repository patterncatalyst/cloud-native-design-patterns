#!/usr/bin/env python3
"""S12 example alignment: put the deck code of align_build.py into the site codetabs.

    align_site.py

For each (chapter, heading) the first codetab after the heading has six fenced blocks in the order
Spring Boot, Quarkus, .NET, Python, C++, Go; the listed blocks are replaced by the deck lines (Go
with tab indentation, an excerpt's cut closing brace restored). Blocks not listed stay as they are.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_build import CODE, REPO  # noqa: E402

ORDER = ["Spring", "Quarkus", "DotNet", "Python", "Cpp", "Go"]

PLAN = [
    ("_docs/01-cloud-native-principles.md", "## A twelve-factor service, ready for the platform",
     {"Spring": ("Spring", 269), "Quarkus": ("Quarkus", 269), "DotNet": ("DotNet", 270),
      "Cpp": ("Cpp", 269), "Go": ("Go", 269)}),
    ("_docs/21-appendix-h-shutdown.md", "## The application side",
     {"Spring": ("Spring", 423), "Quarkus": ("Quarkus", 419), "DotNet": ("DotNet", 427),
      "Cpp": ("Cpp", 419), "Go": ("Go", 419)}),
    ("_docs/25-appendix-l-caching.md", "{% include excalidraw.html\n   file=\"24-write-back\"",
     {"Spring": ("Spring", 480), "Quarkus": ("Quarkus", 476), "DotNet": ("DotNet", 490),
      "Python": ("Python", 476), "Cpp": ("Cpp", 476), "Go": ("Go", 476)}),
]

# closing lines an excerpt on a slide cut for space
CLOSE = {("Quarkus", 269): ["}"], ("Cpp", 476): ["}"], ("Spring", 480): ["}"]}


def site_lines(key):
    lines = list(CODE[key]) + CLOSE.get(key, [])
    if key[0] == "Go":
        out = []
        for ln in lines:
            body = ln.lstrip(" ")
            n = len(ln) - len(body)
            out.append("\t" * (n // 3) + " " * (n % 3) + body if body else "")
        lines = out
    return lines


def main():
    for rel, anchor, repl in PLAN:
        path = REPO / rel
        text = path.read_text()
        start = text.index(anchor)
        tabs = text.index("{% include codetabs.html", start)
        lines = text[tabs:].split("\n")
        blocks, i = [], 1
        while len(blocks) < 6:
            while not lines[i].startswith("```"):
                i += 1
            j = i + 1
            while lines[j] != "```":
                j += 1
            blocks.append((i, j))
            i = j + 1
        for lang, key in sorted(repl.items(), key=lambda kv: -ORDER.index(kv[0])):
            a, b = blocks[ORDER.index(lang)]
            lines[a + 1:b] = site_lines(key)
        path.write_text(text[:tabs] + "\n".join(lines))
        print(rel, "replaced", ", ".join(repl))


if __name__ == "__main__":
    main()
