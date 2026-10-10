#!/usr/bin/env python3
"""Select the example projects that CI should build (stdlib only).

Used by the `changes` job of .github/workflows/examples.yml, and runnable locally:

    scripts/ci_changed_projects.py --base origin/main --head HEAD
    scripts/ci_changed_projects.py --all
    scripts/ci_changed_projects.py --files examples/02-communications/go/order-service/main.go
    scripts/ci_changed_projects.py cpp-context examples/02-communications/cpp/order-service

Output is one JSON object with a compact array per kind:

    jvm      directories containing pom.xml
    dotnet   directories containing *.csproj
    go       directories containing go.mod
    python   directories containing requirements.txt
    cpp      directories containing conanfile.py (each also has a Dockerfile)
    compose  compose*.yaml files
    scripts  verify.sh files

Everything is selected when the base is unknown (workflow_dispatch, all-zero
`before` SHA of a first push, a base that cannot be diffed) and when a shared
input changes: anything under examples/_infra/, this script, or the workflow.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = "examples"

EVERYTHING_TRIGGERS = (
    "examples/_infra/",
    ".github/workflows/examples.yml",
    "scripts/ci_changed_projects.py",
)

# kind -> marker file glob that makes a directory a project of that kind
MARKERS = {
    "jvm": "pom.xml",
    "dotnet": "*.csproj",
    "go": "go.mod",
    "python": "requirements.txt",
    "cpp": "conanfile.py",
}
# language directory names used under examples/NN-*/ -> kinds they hold
LANG_DIRS = {
    "spring-boot": ("jvm",),
    "quarkus": ("jvm",),
    "dotnet": ("dotnet",),
    "go": ("go",),
    "python": ("python",),
    "cpp": ("cpp",),
}
KINDS = list(MARKERS) + ["compose", "scripts"]
ZERO_SHA = re.compile(r"^0+$")
# Changes that cannot affect a build or a config check.
INERT = ("*.md", "*.svg", "*.excalidraw", "*.png")
INERT_DIRS = ("db", "collections", "grafana", "otelcol")


# Files under examples/_infra/ are fragments pulled in by the examples' compose
# files (compose-debezium.yaml refers to a service that compose-kafka.yaml
# defines), so they are not valid on their own. Every example that includes one
# is checked, and a change to _infra selects everything.
COMPOSE_FRAGMENT_DIR = "examples/_infra/"


def is_compose(path: str) -> bool:
    return (bool(re.fullmatch(r"compose[^/]*\.ya?ml", os.path.basename(path)))
            and not path.startswith(COMPOSE_FRAGMENT_DIR))


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, text=True,
                          capture_output=True).stdout


def tracked(prefix: str = EXAMPLES) -> list[str]:
    return [p for p in git("ls-files", prefix).splitlines() if p]


def is_project(directory: Path, kind: str) -> bool:
    return directory.is_dir() and any(directory.glob(MARKERS[kind]))


def all_projects(kind: str, files: list[str], under: str = EXAMPLES) -> set[str]:
    """Project dirs of `kind` among tracked files below `under`."""
    glob = MARKERS[kind]
    out = set()
    for f in files:
        if f.startswith(under.rstrip("/") + "/") and fnmatch.fnmatch(os.path.basename(f), glob):
            out.add(os.path.dirname(f))
    return out


def select_everything() -> dict[str, set[str]]:
    files = tracked()
    sel = {k: all_projects(k, files) for k in MARKERS}
    sel["compose"] = {f for f in files if is_compose(f)}
    sel["scripts"] = {f for f in files if os.path.basename(f) == "verify.sh"}
    return sel


def nearest_project(path: str, kind: str) -> str | None:
    d = Path(path).parent
    while str(d) not in (".", EXAMPLES, ""):
        if is_project(ROOT / d, kind):
            return str(d)
        d = d.parent
    return None


def select_for_changes(changed: list[str]) -> dict[str, set[str]]:
    files = tracked()
    sel: dict[str, set[str]] = {k: set() for k in KINDS}
    for f in changed:
        if not f.startswith(EXAMPLES + "/"):
            continue
        parts = f.split("/")
        name = parts[-1]
        exists = (ROOT / f).exists()
        if is_compose(f):
            if exists:
                sel["compose"].add(f)
            continue
        if name == "verify.sh":
            if exists:
                sel["scripts"].add(f)
            continue
        if any(fnmatch.fnmatch(name, pat) for pat in INERT) or any(p in INERT_DIRS for p in parts[2:-1]):
            continue
        hit = False
        for kind in MARKERS:
            proj = nearest_project(f, kind)
            if proj:
                sel[kind].add(proj)
                hit = True
        if hit or len(parts) < 3:
            continue
        # No project above the file. A file under <example>/<lang>/ (a shared
        # proto, a lock file, a Dockerfile next to several services) selects every
        # project of that language there. A file elsewhere in the example (e.g.
        # <example>/proto/) can feed any language, so it selects the whole example.
        example = "/".join(parts[:2])
        lang = parts[2] if len(parts) > 3 else None
        if lang in LANG_DIRS:
            for kind in LANG_DIRS[lang]:
                sel[kind] |= all_projects(kind, files, f"{example}/{lang}")
        else:
            for kind in MARKERS:
                sel[kind] |= all_projects(kind, files, example)
    return sel


def changed_files(base: str | None, head: str) -> list[str] | None:
    """Changed paths between base and head, or None when it cannot be diffed."""
    if not base or ZERO_SHA.match(base):
        return None
    try:
        return git("diff", "--name-only", base, head).splitlines()
    except subprocess.CalledProcessError:
        return None


def to_json(sel: dict[str, set[str]]) -> dict[str, str]:
    return {k: json.dumps(sorted(sel.get(k, set())), separators=(",", ":")) for k in KINDS}


def cpp_context(directory: str) -> str:
    """Docker build context for a cpp project dir.

    Most Dockerfiles use the service directory itself; those in a multi-service
    example copy `<service>/conanfile.py` and `proto/`, so their context is the
    parent (cpp/) directory, as in the example's compose.yaml."""
    d = Path(directory)
    text = (ROOT / d / "Dockerfile").read_text()
    if re.search(rf"^COPY\s+(?:--\S+\s+)*{re.escape(d.name)}/", text, re.M):
        return str(d.parent)
    return str(d)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", choices=["select", "cpp-context"], default="select")
    ap.add_argument("arg", nargs="?", help="project directory for cpp-context")
    ap.add_argument("--base", help="base SHA/ref to diff against")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--event", default="", help="GitHub event name; workflow_dispatch selects everything")
    ap.add_argument("--all", action="store_true", help="select everything")
    ap.add_argument("--files", nargs="*", help="treat these paths as the changed files (testing)")
    ap.add_argument("--github-output", action="store_true", help="append key=value lines to $GITHUB_OUTPUT")
    args = ap.parse_args()

    if args.command == "cpp-context":
        print(cpp_context(args.arg))
        return 0

    reason = None
    changed: list[str] | None = None
    if args.all or args.event == "workflow_dispatch":
        reason = "everything requested"
    elif args.files is not None:
        changed = args.files
    else:
        changed = changed_files(args.base, args.head)
        if changed is None:
            reason = "no usable base to diff against"
    if changed is not None:
        trigger = next((f for f in changed if f.startswith(EVERYTHING_TRIGGERS)), None)
        if trigger:
            reason = f"shared input changed: {trigger}"
    sel = select_everything() if reason else select_for_changes(changed or [])
    print(f"selection: {reason or str(len(changed or [])) + ' changed file(s)'}", file=sys.stderr)

    out = to_json(sel)
    if args.github_output and os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            for k, v in out.items():
                fh.write(f"{k}={v}\n")
    print(json.dumps({k: json.loads(v) for k, v in out.items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
