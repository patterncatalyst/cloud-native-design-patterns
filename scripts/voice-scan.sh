#!/usr/bin/env bash
#
# voice-scan.sh - professional-voice scan over the reader-facing surfaces of this site.
#
#   scripts/voice-scan.sh                       gate mode: ban tier must be 0 (CI runs this)
#   scripts/voice-scan.sh --all-tiers-summary   all-tier totals for both scopes (never fails)
#   scripts/voice-scan.sh <scan.sh options>     pass options through, e.g. --tier watch --hits all
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

run_both() {
    local rc=0
    echo "== site"
    "${SCAN[@]}" "$@" "${SITE_ROOTS[@]}" || rc=1
    echo "== examples (Markdown only)"
    "${SCAN[@]}" --ext md "$@" "${EXAMPLE_ROOTS[@]}" || rc=1
    return "$rc"
}

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

run_both "$@"
