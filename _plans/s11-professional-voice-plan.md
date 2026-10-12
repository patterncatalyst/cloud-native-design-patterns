# S11 plan — professional-voice pass and CI voice gate

Approved by the user 2026-10-11. Opus plan; Sonnet executes in batches on `docs/professional-voice`; Opus validates.

## User decisions (2026-10-11)

1. Fix the scanner upstream first, then vendor that commit: lgtm-skills PR #48, merged as `a3350074a1df343b3bbd58a563f26bf0311a265a` (scratch file outside the scanned mirror; `candid` flagged).
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
| 1 vendor + wrapper | done (bf3f9d3) |
| 2–7 batches | done (B6 15f0f0a, B1 99243f4, B4 79e04a8, B2 d32a858, B5 a7d0874, B3 31d8eb7) |
| 8 gate | done |
| 9 validation, PR | validation round 1 done; repair round 1 (lgtm-skills #49 re-vendored, wrapper paths fix aebfb9e, wording 9450973); final recheck pending |

## Results

Per-file counts from the final scanner (lgtm-skills a335007) run on main 48e7736 (before) and on this branch (after). These counts are authoritative; the batch ledgers further down are the executors' narrative and their hand counts used the earlier pattern set.

| File | Ban before | Ban after | Watch before | Watch after |
|---|---|---|---|---|
| `README.md` | 0 | 0 | 2 | 1 |
| `_docs/00-setting-up.md` | 3 | 0 | 4 | 0 |
| `_docs/01-cloud-native-principles.md` | 2 | 0 | 2 | 0 |
| `_docs/02-communications.md` | 3 | 0 | 2 | 0 |
| `_docs/03-composition.md` | 0 | 0 | 2 | 0 |
| `_docs/04-data.md` | 2 | 0 | 3 | 1 |
| `_docs/05-event-driven.md` | 16 | 0 | 26 | 11 |
| `_docs/06-stream-processing.md` | 1 | 0 | 2 | 0 |
| `_docs/07-workflows-and-jobs.md` | 0 | 0 | 3 | 0 |
| `_docs/08-api-management.md` | 2 | 0 | 3 | 0 |
| `_docs/09-api-registry.md` | 1 | 0 | 0 | 0 |
| `_docs/10-api-metadata.md` | 0 | 0 | 2 | 0 |
| `_docs/11-observability.md` | 3 | 0 | 3 | 0 |
| `_docs/12-security.md` | 0 | 0 | 1 | 0 |
| `_docs/13-anti-patterns.md` | 0 | 0 | 3 | 0 |
| `_docs/14-appendix-a-protocols.md` | 4 | 0 | 4 | 0 |
| `_docs/15-appendix-b-versioning.md` | 1 | 0 | 9 | 5 |
| `_docs/16-appendix-c-websockets.md` | 5 | 0 | 2 | 0 |
| `_docs/17-appendix-d-sagas.md` | 1 | 0 | 3 | 0 |
| `_docs/18-appendix-e-errors.md` | 2 | 0 | 1 | 1 |
| `_docs/19-appendix-f-ddd-hexagonal.md` | 2 | 0 | 7 | 0 |
| `_docs/20-appendix-g-coupling.md` | 2 | 0 | 7 | 1 |
| `_docs/21-appendix-h-shutdown.md` | 1 | 0 | 4 | 0 |
| `_docs/22-appendix-i-l7-routing.md` | 4 | 0 | 10 | 1 |
| `_docs/23-appendix-j-dotnet-toolkit.md` | 10 | 0 | 6 | 1 |
| `_docs/24-appendix-k-monolith-to-microservices.md` | 5 | 0 | 8 | 3 |
| `_docs/25-appendix-l-caching.md` | 3 | 0 | 6 | 0 |
| `_docs/26-appendix-m-failure-modes.md` | 5 | 0 | 5 | 2 |
| `_docs/27-appendix-n-feature-flags.md` | 5 | 0 | 4 | 1 |
| `_docs/28-appendix-o-newman.md` | 3 | 0 | 8 | 2 |
| `_docs/29-appendix-p-dotnet-on-linux.md` | 0 | 0 | 1 | 0 |
| `_docs/29-glossary.md` | 0 | 0 | 2 | 1 |
| `_docs/31-appendix-r-minikube.md` | 0 | 0 | 19 | 19 |
| `_docs/32-appendix-s-openshift-local.md` | 0 | 0 | 20 | 20 |
| `_example_pages/index.md` | 0 | 0 | 1 | 1 |
| `_example_pages/prerequisites.md` | 0 | 0 | 6 | 5 |
| `assets/diagrams/04-cqrs.svg` | 1 | 0 | 0 | 0 |
| `assets/diagrams/04-db-per-service.svg` | 0 | 0 | 1 | 1 |
| `assets/diagrams/05-checkpoint-recovery.svg` | 1 | 0 | 0 | 0 |
| `assets/diagrams/05-sourcing-vs-streaming.svg` | 0 | 0 | 2 | 0 |
| `assets/diagrams/08-four-planes.svg` | 0 | 0 | 1 | 0 |
| `assets/diagrams/12-claim-check.svg` | 0 | 0 | 1 | 0 |
| `assets/diagrams/13-antipatterns-grid.svg` | 0 | 0 | 1 | 0 |
| `assets/diagrams/15-rest-versioning.svg` | 0 | 0 | 2 | 2 |
| `assets/diagrams/17-saga-state.svg` | 1 | 0 | 0 | 0 |
| `assets/diagrams/18-rest-errors.svg` | 0 | 0 | 2 | 1 |
| `assets/diagrams/19-strategic-ddd.svg` | 0 | 0 | 1 | 0 |
| `assets/diagrams/20-cynefin-coupling.svg` | 1 | 0 | 0 | 0 |
| `assets/diagrams/21-shutdown-sequence.svg` | 1 | 0 | 0 | 0 |
| `assets/diagrams/22-east-west.svg` | 1 | 0 | 1 | 0 |
| `assets/diagrams/22-hop-cost.svg` | 1 | 0 | 0 | 0 |
| `assets/diagrams/22-l7-layers.svg` | 0 | 0 | 2 | 0 |
| `assets/diagrams/22-sticky-sessions.svg` | 0 | 0 | 1 | 1 |
| `assets/diagrams/24-monolith-unit.svg` | 0 | 0 | 1 | 0 |
| `assets/diagrams/25-failure-taxonomy.svg` | 1 | 0 | 1 | 1 |
| `assets/diagrams/25-gray-failure.svg` | 0 | 0 | 1 | 0 |
| `assets/diagrams/25-istio-resilience.svg` | 1 | 0 | 0 | 0 |
| `assets/diagrams/27-ci-gate.svg` | 0 | 0 | 1 | 0 |
| `assets/diagrams/31-minikube-image-flow.svg` | 0 | 0 | 1 | 1 |
| `assets/diagrams/31-minikube-topology.svg` | 0 | 0 | 1 | 1 |
| `assets/diagrams/32-openshift-topology.svg` | 0 | 0 | 1 | 1 |
| `examples/02-communications/spring-boot/README.md` | 0 | 0 | 1 | 1 |
| `examples/05-event-driven/README.md` | 0 | 0 | 4 | 4 |
| `examples/05-event-driven/k8s/README.md` | 0 | 0 | 5 | 5 |
| `examples/05-event-driven/openshift/README.md` | 0 | 0 | 2 | 2 |
| `examples/12-security/cpp/README.md` | 0 | 0 | 1 | 1 |
| `examples/12-security/quarkus/README.md` | 0 | 0 | 1 | 1 |
| `examples/12-security/spring-boot/README.md` | 0 | 0 | 1 | 1 |
| `examples/16-websockets/spring-boot/README.md` | 0 | 0 | 1 | 1 |
| `examples/17-sagas/spring-boot/README.md` | 0 | 0 | 1 | 1 |
| `examples/19-ddd-hexagonal/cpp/README.md` | 0 | 0 | 1 | 0 |
| `examples/25-caching/quarkus/README.md` | 0 | 0 | 1 | 1 |
| `examples/25-caching/spring-boot/README.md` | 0 | 0 | 1 | 1 |
| `examples/PREREQUISITES.md` | 0 | 0 | 6 | 5 |
| **Total** | **95** | **0** | **239** | **109** |

Every remaining watch hit is kept with a reason code (literal minikube/OpenShift subjects, machine-subject "silently"/"lie", result tables and table data, survey terms, identifiers, idioms such as "easy to miss", one chapter opener per chapter, misconception contrasts, and "deliberate" where it names a planned stage).

## Batch ledgers

### B6 (15f0f0a) appendices R-S, example pages, READMEs
- ban 0 -> 0. watch: site files ~100 -> 49, examples md 24 -> 22 (all kept, reason-coded).
- Changed: README.md:62 (internal planning notes), _example_pages/prerequisites.md:331 + examples/PREREQUISITES.md:327 heading "NOT" -> "not" (slug unchanged), examples/19-ddd-hexagonal/cpp/README.md:34 "ONLY" -> "only".
- Kept: literal-subject (minikube/OpenShift in 31, 32, prerequisites, 05 READMEs, 31/32 SVG labels); table-data (31/32 result tables, 32:35, em-dash file lists in 7 READMEs, _example_pages/index.md:66); idiom (README.md:13 and 32:118 counts; "Release It!" title); identifier (UNIQUE SQL keyword).
### B1 chapter 05
- _docs/05: ban 16 -> 0, watch ~22 -> 11 kept (chapter-opener :10; machine-subject :243 :938; survey-term :297 :323; identifier :303; idiom :299; table-data :335; misconception-contrast :397; literal-subject :1294 :1297).
- 05-checkpoint-recovery: ban 1 -> 0 (svg + excalidraw + alt ~961). 05-sourcing-vs-streaming: watch 2 -> 0 (ALL-CAPS; svg + excalidraw).
- No heading changes. Rewrites to review: :459 "rest of this chapter" -> "which is the idea this chapter builds on"; "decisive choice"; "pays off"; "triggered by choice rather than by a crash".
### B4 appendices I-K
- 22: ban 4 lines file-level (7 incl. diagrams) -> 0, watch ~12 -> 1 kept (identifier :57 22-l7-journey). 23: ban 9 -> 0, watch 6 -> 1 kept (table-data :105 row/column count). 24: ban 7 -> 0, watch 7 -> 0. Diagrams: ban 2 -> 0, watch ~5 -> 0.
- Heading: 23 "What the .NET cloud-native story genuinely lacks" -> "... lacks" (no anchor links).
- Triples: 22-hop-cost ("pay for itself", alt + Figure I.7 caption), 22-east-west (svg+excalidraw), 22-l7-layers (svg+excalidraw+alt :43 + prose :53), 22-l7-journey alt/caption "path", 24-monolith-unit (svg+excalidraw; alt :36 em-dash split).
- Kept unflagged: 24 heading "The shared database — a deliberate intermediate state" (pre-existing, meaningful).
- Review: 23 ~166 "Simple DI", ~182 "The order matters", 24 ~354 "to keep the bytes intact".
### B2 chapters 00-13
- Batch total: ban ~28 -> 0, watch ~40 -> 1 kept (chapter-opener 04:14). Per-file counts not tracked by the executor (validator to recount from main).
- Headings: 00 "How the rest of the book is ordered" -> "How the book is ordered"; 11 "How correlation actually works" -> "How correlation works" (no inbound anchors).
- Triples (hand-edited svg+excalidraw): 04-cqrs, 12-claim-check, 08-four-planes, 04-db-per-service, 13-antipatterns-grid (+ alt 13:22). Caption Figure 8.1 rewritten; em-dash alts in 02, 06, 12 split.
- Review: 08 "never remove one without warning" (was "never silently remove one"; human subject).
### B5 appendices L-Q and glossary (a7d0874)
- 25: ban 3->0, watch 6->0. 26: ban 4->0, watch 4->2 kept (machine-subject "lie" :37 alt, :724). 27: ban 5->0, watch 3->0. 28: ban 6->0, watch 9->2 kept (misconception-contrast :229, idiom :244). 29-P: watch 1->0. 29-glossary: watch 2->1 kept (idiom :12). 30: no hits.
- SVG: 25-istio-resilience ban 1->0; 25-gray-failure watch 1->0; 25-failure-taxonomy kept (machine-subject "lie"); 27-ci-gate watch 1->0 (generator string, svg, hand-edited excalidraw, 28 alt).
- Headings (no inbound anchors): 25 "When NOT to cache, and what to watch for" -> "When not to cache, ..."; 29-P "CIL: what `dotnet build` actually produces" -> "CIL: what `dotnet build` produces".
- Also removed the positional "Below sits" in a 26 alt.
### B3 appendices A-H (31d8eb7)
- 14: ban 4->0, watch 4->0. 15: ban 1->0, watch 11->5 (idiom :22 :25 :31 :221; machine-subject :108). 16: ban 4->0, watch 1->0. 17: ban 1->0, watch 4->0. 18: ban 2->0, watch 1->1 (machine-subject :406). 19: ban 3->0, watch 8->0. 20: ban 2->0, watch 10->1 (machine-subject :184). 21: ban 1->0, watch 4->0. SVG: ban 4->0, watch 4->3 (15-rest-versioning idiom x2; 18-rest-errors literal-subject payload data).
- Heading: 14 "Three paradigms, three mental models" -> "Three paradigms and their mental models" (no anchors).
- Triples: 17-saga-state (+ alt D.1), 18-rest-errors, 19-strategic-ddd (+ alt), 20-cynefin-coupling (+ alt), 21-shutdown-sequence.
- Review: 16 opener rewrite; 16 "Test what the backplane provides."; 18 added "so nothing about the implementation leaks"; 21 "is evidence that graceful shutdown works".

### Repair round 1 (validator findings)
- Grammar: Appendix K "if you later need to split". Soft hype: Appendix O "powerful idea" removed.
- Scanner gaps fixed upstream (lgtm-skills #49, re-vendored at a335007): "the rest of the appendix/section" (ban), adjective "deliberate" and summary markers (watch). Five new ban hits rewritten (26 x2, 16, 20, 25-failure-taxonomy label); summary markers removed (14, 23, 26); "deliberate" rewritten except where it names a planned stage (24 heading, alt and caption; 27 "only a deliberate flip removes it").
- Claims restored to their original strength: Appendix L caching payoff, random eviction; Appendix J "Minimal built-in DI"; chapter 05 "most consequential choice"; Appendix B "without any error"; 04-db-per-service label "quietly fails" (machine subject).
- 27-ci-gate label "in CI as they do locally"; chapter 04 positional alt "A band below" -> "A second band".
- Wrapper: `voice-scan.sh <paths>` scans only those paths (examples/ paths as Markdown); examples output notes its relative paths.
- Heading changes across S11 (none with inbound anchors): 00, 11, 14, 23, 25, 29-P, plus the "NOT" lowercase headings in the two prerequisites pages (slug unchanged).
