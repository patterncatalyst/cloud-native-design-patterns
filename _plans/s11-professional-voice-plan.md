# S11 plan — professional-voice pass and CI voice gate

Approved by the user 2026-10-11. Opus plan; Sonnet executes in batches on `docs/professional-voice`; Opus validates.

## User decisions (2026-10-11)

1. Fix the scanner upstream first, then vendor that commit: lgtm-skills PR #48, merged as `50b4c08f0454cfc5826096081d201827018d2b90` (scratch file outside the scanned mirror; `candid` flagged).
2. Fix watch tier too, with the triage policy below; every kept watch hit gets a reason code. Only ban tier is gated in CI.
3. `_plans/` stays internal history: not rewritten, not gated, still published.

## Baseline (main 48e7736, scanner 50b4c08)

- Whole repo: 338 lines, 91 ban (the extra one is `candid`, Appendix J line 18). In scope: 90 ban (24 `_docs` chapters plus 8 SVGs); out of scope: `lgtm-presentation/BUILD.md:52` (S12).
- In-scope watch: about 225 (199 site and diagrams, 26 `examples/**/*.md`).
- No ban hit is inside code or recorded output. Hits sit in prose, front-matter `description:`, `{% include excalidraw.html %}` alt/caption attributes, and SVG text.
- SVGs without a generator in the repo (hand-edit SVG `<text>`, `.excalidraw` `text` and `originalText`, and the doc alt/caption together): 04-cqrs, 05-checkpoint-recovery, 17-saga-state, 20-cynefin-coupling, 21-shutdown-sequence, 22-east-west, 22-hop-cost, 25-istio-resilience. 27-ci-gate comes from `scripts/gen_27_diagrams.py`.

## Scope (gated by `scripts/voice-scan.sh`)

| Surface | Status |
|---|---|
| `_docs/*.md`, `_parts/*.md`, `index.html`, `_example_pages/*.md`, `_includes/*.html`, `_layouts/*.html`, `README.md`, `assets/diagrams/*.svg` | in, gated (default extensions) |
| `examples/**/*.md` | in, gated (`--ext md`, so example source is not scanned) |
| `scripts/gen_*.py` label strings | edited only to keep a regenerated SVG in step; not gated |
| `verify.sh`, `k8s/*.sh`, `openshift/*.sh`, workflows, compose and YAML | out (code; echo text is recorded output) |
| `lgtm-presentation/` | out; S12 switches it on (commented line in the wrapper) |
| `_plans/`, `CLAUDE.md` | out (internal / agent-facing) |

## Steps

0. lgtm-skills PR #48 (done, 50b4c08).
1. Plan status (S10 done, S11 in progress), vendor `scripts/voice/{scan.sh,patterns.tsv}` byte-identical from 50b4c08 plus `scripts/voice/README.md` (provenance: repo, path, SHA, date, license note, resync command, "fix upstream"), wrapper `scripts/voice-scan.sh` (two invocations: site roots with default extensions; `examples` with `--ext md`; no args = gate mode `--tier ban --fail` with `--hits all --tier ban` excerpts on failure and combined exit code; args pass through; `--all-tiers-summary`). No CI change yet.
2–7. Sonnet sweep batches (whole files; a chapter's SVG, `.excalidraw` and alt/caption travel together; checkpoint commit per batch):
   - B1 `_docs/05-event-driven.md` + diagrams 05-*
   - B2 `_docs/00`–`13` + diagrams 04-*, 08-*, 12-*, 13-*
   - B3 appendices A–H (`_docs/14`–`21`) + diagrams 15-*, 17-*, 18-*, 19-*, 20-*, 21-*
   - B4 appendices I–K (`_docs/22`–`24`) + diagrams 22-*, 24-*
   - B5 appendices L–P and glossary (`_docs/25`–`29-*`) + diagrams 25-*, 27-*
   - B6 appendices R–S (`_docs/31`, `_docs/32`), `_example_pages/*`, `_parts/*`, `index.html`, `README.md`, `examples/**/*.md`
8. CI gate in `.github/workflows/content.yml` job `validate` (feeds `content-ok`; no ruleset change): `bash scripts/voice-scan.sh` and `bash scripts/voice-scan.sh --all-tiers-summary`. CLAUDE.md documents the gate. Evidence table in `modernization-plan.md`.
9. Opus validation, repair rounds (max two), PR, CI green, squash-merge.

## Executor rules

1. Never edit inside fenced blocks, inline code, `{% raw %}` segments, codetab bodies, `{% include %}` `file=`/`langs=` attributes, URLs or link targets. Recorded output and result tables stay as they are.
2. Do not change meaning: every number, version, pin, claim and caveat survives. Rewrite the sentence, not the word.
3. Keep markdown structure: heading levels, list nesting, tables, wrapping style.
4. No positional words (above, below, preceding, following, next or previous section, later or earlier in this chapter). "The rest of this book/chapter" is rewritten by naming the concept or the chapter or appendix title.
5. Never name the old container engine.
6. "Verification status" footers: fix voice in the lead-in only, never the facts.
7. SVG triple rule: change the SVG `<text>`, both `text` and `originalText` in the `.excalidraw`, and any doc alt/caption that repeats the label, identically. The new label is no longer than the old one. Keep XML escapes valid.
8. No synonym swaps: never introduce truly, candid, intentional, deliberate, purposely, purposefully, real-world, out of the box, at no cost; "by design" only when followed by the reason.
9. Edits stay within the flagged sentence and its neighbour.
10. Watch-tier triage: delete "actually" unless it contrasts with a stated wrong belief; delete "simply/trivially" ("easy to miss/forget" stays); delete "very/really/crucially/notably" ("very high" stays only in a comparison-table cell); "quietly/silently" stay with a machine subject, rewrite drama; split prose lines with 3+ em dashes (empty table cells stay); lowercase ALL-CAPS in prose and labels (NETWORK/COMPONENT/LOAD taxonomy labels stay); "isn't X — it's Y" only when X is a misconception readers hold; "landscape" (survey) and the `22-l7-journey` identifier stay, prose "journey" becomes "path", rewrite "highest-leverage"; commit instead of "arguably"; result tables stay, headings rewritten only when no anchor points at them; minikube/OpenShift stay where they are the subject, "laptop" becomes "workstation" or "locally"; "lie" with a machine subject stays; one "This chapter is about" opener per chapter stays; README "the roadmap and the Phase-3 backlog" becomes "internal planning notes".
11. Handback ledger in the report: per file ban and watch before/after; each kept watch hit with a reason code (`machine-subject`, `literal-subject`, `table-data`, `survey-term`, `idiom`, `identifier`, `misconception-contrast`, `chapter-opener`); every heading whose text changed.
12. Before handing back: `scripts/voice-scan.sh --tier ban <files>` is 0 and `python3 scripts/validate_site.py` reports 0 errors.

## Acceptance criteria

1. `bash scripts/voice-scan.sh` exits 0 (0 ban-tier in both invocations).
2. Whole-repo ban scan lists only `lgtm-presentation/BUILD.md`.
3. In-scope watch tier drops from about 225; every survivor has a reason code (expected roughly 90–110).
4. For every changed `.md`, the ordered lists of fenced blocks, inline code spans, `{% raw %}` segments, link targets and include `file=`/`langs=` attributes are identical between main and HEAD.
5. Every changed line is within 2 lines of a baseline hit, or is a listed alt/caption/SVG mirror.
6. Added lines contain no synonym swaps, positional words or the old container engine's name.
7. No meaning drift (word-diff read: all of 05, 23, 24, 27 plus one file per other batch).
8. `validate_site.py` 0 errors.
9. Jekyll build (ruby:3.3, production, baseurl) for main and HEAD: same generated files; same ids except headings listed in ledgers with no inbound anchors; same href/src/data values.
10. Changed SVGs pass `xmllint`; changed `.excalidraw` files are valid JSON with `text == originalText`; alt/caption agree; labels no longer than before; rendered and inspected.
11. Vendored files byte-identical to lgtm-skills 50b4c08 (sha256), modes 100755/100644.
12. actionlint clean on `content.yml`; shellcheck clean on `scripts/voice-scan.sh`.
13. Gate proof (local, reverted): injection in a `_docs` page, in an `examples` README and in an SVG each exit 1; injection inside inline code and a fenced block exit 0.
14. mawk (ubuntu:24.04 container) and gawk give the same all-tier totals; the CI log shows them.
15. Plan shows S10 done and S11 validated with the per-file table; CLAUDE.md updated.
16. PR checks `site`, `content-ok`, `examples-ok` green, with the voice-scan step in the `content-ok` run log.

## Status

| Step | Status |
|---|---|
| 0 upstream fix | done (lgtm-skills #48, 50b4c08) |
| 1 vendor + wrapper | in progress |
| 2–7 batches | pending |
| 8 gate | pending |
| 9 validation, PR | pending |
