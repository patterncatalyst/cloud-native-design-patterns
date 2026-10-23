# S12 plan — deck refresh (lgtm-presentation/)

Approved by the user 2026-10-12. Opus plans and validates; Sonnet executes; one commit per deck; a single push at the end.

## User decisions (2026-10-12)

1. Commit a Markdown text copy of every deck and docx (`lgtm-presentation/text/`) and gate it in CI (`deck_text.py --check` in `content-ok`; decks join the voice scan, the positional and old-engine checks, and a stale-stack denylist).
2. Exclude `lgtm-presentation/` from the Jekyll build (the site links to the GitHub tree).
3. Where a site codetab is stale against `examples/`, fix the site in this PR (separate `docs(site)` commit). `examples/` is the authority.
4. No PowerPoint check: rely on LibreOffice conversion and python-pptx reload checks.
5. Defaults kept: MassTransit removed from the .NET deck entirely (Appendix J included); the C++ deck gets Appendix R only (C++ is not in OpenShift Local), with one note line saying so.

6. Manifest decisions (2026-10-12): the Spring deck matches the example's hand-rolled saga orchestrator (Spring Statemachine mentioned only as archived upstream, not offered as an option); the Go valet-key / claim-check slides follow `examples/` (golang-jwt ticket) and the site codetab is fixed to match; the C++ deck's library and compendium references are verified upstream and kept only where they hold up; `examples/21-graceful-shutdown/cpp` gets an async-signal-safe SIGTERM handler (atomic flag, log from the main loop) in this PR; StackRox / OKD are not added to the network advisory.

7. Vendor-neutral content (user, 2026-10-12): nothing relies on ACS, OpenShift or AWS, and only maintained open-source libraries are used (`aws-sdk-go-v2`, `boto3`, the AWS SDK for .NET and any other cloud SDK are out).
   - Valet key and claim check, on the site (`_docs/12-security.md`, all six codetabs and prose) and in every language deck: follow `examples/12-security/<lang>` (signed tickets from the service itself); describe object storage generically, with no S3, STS or AWS framing.
   - All other AWS mentions in the decks (about 13–20 per language deck) and on the site (`_docs/12`, glossary, Appendix M) are rewritten vendor-neutrally.
   - Network-Policy-Process-Advisory deck and its `.md`/`.docx`: reworked to upstream Kubernetes and open-source tools (NetworkPolicy, upstream AdminNetworkPolicy/ClusterNetworkPolicy, a CNI that enforces them such as Cilium or Calico, Kyverno or OPA Gatekeeper for admission policy, Trivy for scanning, Falco for runtime), keeping the same process and phases.
   - Appendix S (OpenShift Local) stays on the site as merged in S10, but the decks get no Appendix S slides; Appendix R (minikube) is added to all six language decks. Remaining OpenShift mentions in the language decks are rewritten.
   - The stale-stack denylist gains AWS SDKs (`aws-sdk`, `boto3`, `AWSSDK`, `IAmazonS3`, `software.amazon`, `@aws-sdk`), `minio-go`, and ACS / Advanced Cluster Security / OpenShift for the deck text copies.

## Findings

- No deck generator source exists anywhere (claude.ai builder for the language decks; python-pptx from a Red Hat template for the policy decks, whose `.md` companions are the source of their `.docx`). Precedent for in-place edits: `scripts/add_appendix_p_slides.py`.
- No CI touches `lgtm-presentation/`; `validate_site.py` skips it for the old-engine check; `voice-scan.sh` has a `# S12:` placeholder. No LFS; `.git` is 263 MB, `lgtm-presentation/` 82 MB; Jekyll publishes the decks into the Pages artifact today.
- Inventory (slides / ban / watch / main stale items):
  - Python 272 / 58 / 231: Poetry (10, 14), `@app.on_event` (221, 223), "Faust" (43), Newman CI on the old container engine (261–272).
  - Quarkus 272 / 54 / 232: "Quarkus 3.35".
  - Spring 276 / 49 / 224: Spring Boot 4.0, Jackson 2 serializer (219), topic `order-placed` (36).
  - .NET 303 / 65 / 270: MassTransit on 21 slides and 25 notes; 17 slides without notes (287–303); old-engine compose (301).
  - Go 272 / 57 / 233: code almost never matches the site's Go codetabs; graphql-go and pyproject leftovers.
  - C++ 272 / 38 / 150: modern-cpp-kafka (12 slides, 15 notes), c++20 chips, GCC 14 / CMake 3.27 notes.
  - K8s-Environment-Access-Policies 18 / 1 / 15: kubeval (now kubeconform v0.8.0).
  - Network-Policy-Process-Advisory 20 / 0 / 15: OpenShift doc URLs at 4.16/4.18 (pin is 4.22.14); ANP/BANP status to confirm.
  - BUILD.md: 1 ban phrase, Go 1.26, C++20/23, sandbox paths, stale counts.
- Code drift vs site codetabs (best match ≥0.5 / ≥0.95): Spring 27/6, Quarkus 20/3, .NET 19/4, Python 28/7, C++ 25/2, Go 1/0. About 17 code slides per deck are language-agnostic (YAML, proto, JSON, Actions) and shared. Notes are largely shared across decks.
- No deck has minikube or OpenShift Local slides. Page numbers are static text boxes; R and S are appended at the end.
- Tooling: soffice, pdftoppm, pdftotext, lxml present; python-pptx, python-docx, cairosvg go in a scratchpad venv. Brand fonts (Red Hat Text, Red Hat Display, Overpass) must be installed by the user before rendering: `sudo dnf install -y redhat-text-fonts redhat-display-fonts overpass-fonts`.

## Approach

Edit every file in place with a small committed toolkit; new slides are clones of existing slides in the same deck.

- `scripts/deck_text.py` (stdlib only): pptx/docx → `lgtm-presentation/text/<name>.md` (one `## [NNN] EYEBROW · Title (sldId N)` section per slide, code shapes as fenced blocks tagged with the chip language, notes as a `>` block). `--write` regenerates; `--check` diffs in memory and fails on staleness or on notes ≠ slides.
- `scripts/deck_edit.py` (python-pptx + lxml, venv): applies `lgtm-presentation/edits/<deck>.json` (shared fixes in `_shared.json`). Operations: `replace` (scope slide or notes, exact text, expected count, fails on mismatch, logs cross-run matches), `set_notes`, `set_code` (keeps box formatting, colours comment lines like the existing comment runs, fails over ~22 lines / ~95 columns or the box capacity), `clone_slide` (by sldId; own notes slide, relationships and content types), `set_text`, `replace_picture`, `set_page_number`. Slides are addressed by sldId; dry run prints the text diff.
- `scripts/deck_render.sh`: soffice → PDF → `pdftoppm -png -r 90` for listed pages; aborts if the brand fonts are missing.

Rejected: rebuilding pptxgenjs sources (≈1,690 slides, visual drift, notes re-entry); merging separately built R/S decks (fragile across masters); regenerating docx from md (no converter; edit docx in place and check text equality); introducing LFS (does not shrink history; Pages friction).

## Steps

1. Plan status (S11 done, S12 in progress) and this file.
2. Environment: fonts (user), venv, baseline text and renders of all decks under the session scratchpad `s12/before/`; record python-pptx / python-docx / cairosvg versions.
3. Toolkit (Sonnet) + baseline text copy commit; Opus validates round-trip (empty edit = same parts, same media hashes, same text), clone_slide on a scratch copy (opens, own notes), failing `replace` guard.
4. Manifest (Opus): per deck and slide (sldId, title) the category (version, stack, code, voice, positional, notes, new) and the exact target text or authoritative source; code map deck slide → site codetab → example file; watch-tier ledger; R and S outlines (R in all six language decks, S in five; figures from `assets/diagrams/31-*`, `32-*` via cairosvg; agenda gains "Appendices R–S").
5. Shared fixes `_shared.json` (Sonnet; Opus checks match counts).
6–13. One Sonnet batch per deck, sequential (B1 K8s policies + md/docx, B2 network advisory + md/docx, B3 Python, B4 Quarkus, B5 Spring, B6 .NET, B7 Go, B8 C++): apply shared and deck edits, append R/S, complete notes, regenerate text copy, render changed and new slides, self-check (voice ban 0, validate_site, deck_text --check), commit `docs(deck): refresh <name> (S12)`. Opus validates each batch; repairs as `git commit --fixup`, folded with `git rebase --autosquash` before the single push.
14. Surrounding docs: BUILD.md (method, toolkit, R/S, real counts), README.md and CLAUDE.md deck wording, `_config.yml` exclude, and `docs(site)` codetab fixes found during the batches.
15. Gate on: `content.yml` runs `deck_text.py --check`; `voice-scan.sh` adds `lgtm-presentation`; `validate_site.py` runs the positional check over `lgtm-presentation/*.md` and `text/*.md`, stops skipping `lgtm-presentation` for the old-engine check, and adds the stale-stack denylist for the text copy.
16. Full validation (Opus), push once, PR, three green checks, squash-merge, record evidence.

## Acceptance criteria

1. `deck_text.py --check` exits 0; notes = slides in all 8 decks.
2. `voice-scan.sh` 0 ban-tier with `lgtm-presentation` in scope; surviving watch hits in the S12 ledger with reasons.
3. `validate_site.py` 0 errors including positional and old-engine checks over `lgtm-presentation/`.
4. Text copies have 0 denylist hits; every version on a slide equals a pin in the modernization plan (pin table in this plan).
5. Every language-specific code slide is mapped to a codetab and/or example file with status "matches" (Opus sign-off), ≤22 lines, no overflow in the render.
6. Appendix R in all six language decks, S in five (not C++); every slide has notes, the 31-/32- figures, pins equal to the site appendices; the agenda lists R–S.
7. Every changed or new slide rendered with the brand fonts and inspected (log of slide ids in this plan).
8. docx text equals the companion `.md` text, ignoring formatting.
9. BUILD.md slide counts match; BUILD.md, README.md and CLAUDE.md describe the eight decks and the in-place method.
10. One commit per deck; PR checks `site`, `content-ok`, `examples-ok` green; squash-merged.
11. `modernization-plan.md` shows S11 done (PR #69, 2d8c2a8) and S12 done with evidence.

## Status

| Step | Status |
|---|---|
| 1 plan status | done |
| 2 environment | done (brand fonts installed; venv pinned, see "Tooling") |
| 3 toolkit | done (8c86d61, e4126d5, 6709b2c) |
| 4 manifest | done (`s12-manifest/`) |
| 5–13 batches | done (one commit per deck plus `fixup!` commits, folded with `git rebase --autosquash` before the push) |
| fix round A (colours, caps, accuracy, cross-deck) | done (`s12-manifest/README.md`, "Fix round A") |
| 14 surrounding docs | done (BUILD.md, README.md, CLAUDE.md, `_config.yml`, `docs(site)` codetab fixes) |
| 15 CI gate | done (`content.yml`, `voice-scan.sh`, `validate_site.py`, `scripts/deck-denylist.json`) |
| 16 final validation | done locally 2026-10-12 (`s12-manifest/README.md`, "Final validation"); push, PR, checks and merge pending |

### Render log (acceptance criterion 7)

Every language deck was rendered in full with the brand fonts (soffice 26.2.6.3, one PDF per deck) and checked with
`scripts/deck_fit.py` (0 flags on all six) after the final-validation fix files; earlier rounds rendered and inspected
the slides their edit files touched (`s12-manifest/README.md`, batch and fix-round sections). Slides whose text,
notes or picture changed in the final validation (slide numbers of the current decks); every one with a visible change
(code, caption, figure) was rendered and read, the rest changed only in the speaker notes:

| Deck | Slides |
|---|---|
| Python | 28, 36, 38, 39, 55, 63, 69, 122, 125, 155, 164, 190, 221, 232, 241, 280 |
| Quarkus | 28, 38, 39, 43, 55, 63, 69, 122, 125, 155, 190, 232, 280 |
| Spring | 18, 28, 36, 38, 39, 55, 63, 69, 115, 122, 125, 159, 168, 192, 194, 236, 284 |
| .NET | 8, 30, 38, 40, 41, 65, 68, 71, 118, 123, 125, 126, 129, 163, 197, 198, 205, 207, 210, 235, 246, 293, 311 |
| Go | 28, 38, 39, 55, 63, 69, 122, 125, 155, 190, 221, 232, 280 |
| C++ | 14, 36, 38, 39, 55, 85, 128, 155, 164, 190, 221, 232, 280 |

## Tooling

Scratchpad venv (`/tmp/claude-1000/-home-user-Dev/0dea024d-0bf0-4ae5-bddd-7dec0cf60b22/scratchpad/s12/venv`, Python 3.14.7, never global), newest stable on PyPI 2026-10-12, pinned exactly:

| Package | Version |
|---|---|
| python-pptx | 1.0.2 |
| python-docx | 1.2.0 |
| cairosvg | 2.9.1 |

(lxml 6.1.3 comes in as the python-pptx dependency.) Run `deck_edit.py` with the venv python; `deck_text.py` is stdlib only and runs with the system python3 (CI: ubuntu-latest, 3.14). Set `DECK_BACKUP_DIR` to keep in-place edit backups in the scratchpad (default `~/.cache/deck_edit/backup`); `LO_PROFILE` sets the LibreOffice profile for `deck_render.sh`. `KNOWN_MISSING_NOTES` in `deck_text.py` lists the .NET slides 287-303 that lack notes; the .NET batch empties it.
