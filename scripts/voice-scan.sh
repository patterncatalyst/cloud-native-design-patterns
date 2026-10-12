#!/usr/bin/env bash
#
# voice-scan.sh - professional-voice scan over the reader-facing surfaces of this site.
#
#   scripts/voice-scan.sh                       gate mode: ban tier must be 0 (CI runs this)
#   scripts/voice-scan.sh --all-tiers-summary   all-tier totals for both scopes (never fails)
#   scripts/voice-scan.sh [options] [PATH...]   pass scan.sh options through, e.g. --tier watch --hits all;
#                                               with PATHs, scan only those (examples/ paths as Markdown)
#
# Two scopes, scanned separately because --ext applies to a whole scan.sh run:
#   site      the Jekyll content, layouts, homepage, README and diagram SVGs (default extensions)
#   examples  the example READMEs and PREREQUISITES.md (--ext md, so example source is not scanned)
# Add a new reader-facing surface to SITE_ROOTS. The scanner is vendored from lgtm-skills; see
# scripts/voice/README.md and fix it upstream rather than here.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
SCAN=(bash scripts/voice/scan.sh)

SITE_ROOTS=(_docs _parts _example_pages _includes _layouts index.html README.md assets/diagrams)
# S12: lgtm-presentation joins the gate when the decks are reviewed.
EXAMPLE_ROOTS=(examples)

# scan_scopes <site paths...> -- <example paths...> -- <scan.sh options...>
# Runs each non-empty scope; returns non-zero if either run fails.
scan_scopes() {
    local site=() examples=() opts=() rc=0
    while [[ $# -gt 0 && "$1" != -- ]]; do site+=("$1"); shift; done
    shift
    while [[ $# -gt 0 && "$1" != -- ]]; do examples+=("$1"); shift; done
    shift
    opts=("$@")
    if [[ ${#site[@]} -gt 0 ]]; then
        echo "== site"
        "${SCAN[@]}" "${opts[@]}" "${site[@]}" || rc=1
    fi
    if [[ ${#examples[@]} -gt 0 ]]; then
        echo "== examples (Markdown only; excerpt paths are relative to examples/ when the whole tree is scanned)"
        "${SCAN[@]}" --ext md "${opts[@]}" "${examples[@]}" || rc=1
    fi
    return "$rc"
}

run_both() { scan_scopes "${SITE_ROOTS[@]}" -- "${EXAMPLE_ROOTS[@]}" -- "$@"; }

if [[ $# -eq 0 ]]; then
    if run_both --tier ban --fail; then
        echo "voice scan: 0 ban-tier hits"
        exit 0
    fi
    echo
    echo "voice scan: ban-tier phrases found (rewrite them; see the lgtm-professional-voice rules):"
    run_both --tier ban --hits all || true
    exit 1
fi

if [[ "$1" == --all-tiers-summary ]]; then
    run_both --tier all
    exit 0
fi

# Split options (and their values) from paths. Options that take a value are listed explicitly.
opts=() site=() examples=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tier|--hits|--ext|--exclude|--patterns)
            [[ $# -ge 2 ]] || { echo "voice-scan.sh: $1 needs a value" >&2; exit 2; }
            opts+=("$1" "$2"); shift 2 ;;
        -*) opts+=("$1"); shift ;;
        examples|examples/*|./examples|./examples/*) examples+=("$1"); shift ;;
        *) site+=("$1"); shift ;;
    esac
done

if [[ ${#site[@]} -eq 0 && ${#examples[@]} -eq 0 ]]; then
    run_both "${opts[@]}"
else
    scan_scopes "${site[@]}" -- "${examples[@]}" -- "${opts[@]}"
fi
