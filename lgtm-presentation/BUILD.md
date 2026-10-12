# Designing Cloud-Native APIs — deck build record

Red Hat-branded 16:9 `.pptx` decks in the house style (Overpass / Red Hat Text /
Red Hat Mono, `#EE0000` accents, logo on every slide, thick speaker notes). There is
one deck per language; the cover, agenda, overview, section dividers and every
diagram are language-agnostic and shared, so the decks differ only in their code
slides, language chips, code-specific captions and per-language speaker notes. Two
policy decks and their Markdown and Word companions sit beside them.

## The eight decks

| Deck | Language / stack | Slides |
|------|------------------|-------:|
| `Designing-Cloud-Native-APIs-Python.pptx` | Python 3.14 · FastAPI, aiokafka, faust-streaming | 281 |
| `Designing-Cloud-Native-APIs-Spring.pptx` | Spring Boot 4.1.1 · Java 25 | 285 |
| `Designing-Cloud-Native-APIs-Quarkus.pptx` | Quarkus 3.40.1 · Java 25 | 281 |
| `Designing-Cloud-Native-APIs-DotNet.pptx` | .NET 10.0.12 · C# 14 (extra Appendices J, P, Q) | 312 |
| `Designing-Cloud-Native-APIs-Go.pptx` | Go 1.27.2 | 281 |
| `Designing-Cloud-Native-APIs-Cpp.pptx` | C++23 · GCC 15 · rdkafka++ | 281 |
| `K8s-Environment-Access-Policies.pptx` | Kubernetes environment access policies | 18 |
| `Network-Policy-Process-Advisory.pptx` | Network policy process advisory | 20 |

The slide counts are the number of `## [NNN]` sections in the matching file under
`text/`. The two policy decks are accompanied by `k8s-environment-policies.md` and
`network-policy-process-advisory.md` (the source of the `.docx` of the same name).

Every language deck ends with Appendix R (Example 05 on minikube: a divider and eight
numbered slides) and its agenda lists it; the .NET deck lists Appendices P–R. There are no Appendix S slides:
OpenShift Local stays on the site, and nothing in the decks depends on it.

## How the decks are maintained

No generator source exists for these decks, so every change is an in-place edit of the
committed `.pptx` and `.docx` files with a small toolkit under `scripts/`:

| Tool | Role |
|------|------|
| `scripts/deck_text.py` | pptx/docx to Markdown (standard library only); `--write` regenerates `text/`, `--check` fails on drift, a missing or extra copy, or a slide without notes |
| `scripts/deck_edit.py` | applies an edit file to a deck in place (python-pptx and lxml): `replace`, `set_notes`, `set_code`, `set_text`, `clone_slide`, `replace_picture` and layout operations; slides are addressed by `sldId`; `--dry-run` prints the text diff |
| `scripts/deck_render.sh` | soffice to PDF to PNG for selected slides; refuses to run without the brand fonts |
| `scripts/deck_fit.py` | checks a render for text outside its frame, over the page number or logo, off the slide, or on top of other text |
| `lgtm-presentation/edits/` | the committed edit files: `_shared.json` (replacements that match in all six language decks), `<deck>.json` (the rest of that deck's edits in apply order), `<deck>.fixN.json` (later repairs, each applied once) and `png/` with the replacement figures and their SVG sources in `png/src/` |

Rules for an edit:

- Edit files are applied once, to the committed deck. Every `replace` carries the exact
  match count it expects, so a second run fails instead of changing anything.
- New slides are clones of existing slides of the same deck; their figures come from
  `assets/diagrams/` or `png/src/`, rendered with cairosvg.
- `examples/` is the authority for code. A code slide is an excerpt of an example file
  (at most 22 lines, 95 columns) and names the example in its first comment line.
- After an edit run `python3 scripts/deck_text.py --write`, then the CI checks (`validate_site.py`, `voice-scan.sh`, `deck_text.py --check`), and
  render every changed slide with the brand fonts installed
  (`sudo dnf install -y redhat-text-fonts redhat-display-fonts overpass-fonts`).

Run the tools from the repository root. `deck_edit.py` and `deck_fit.py` need
python-pptx 1.0.2 (lxml comes with it); the figure renders use cairosvg 2.9.1; keep them
in a virtual environment, never global. `deck_text.py` runs with the system Python.
`DECK_BACKUP_DIR` keeps the pre-edit backup somewhere other than the default, and
`LO_PROFILE` selects the LibreOffice profile for rendering.

## The text copies and the CI gate

`text/<name>.md` is a Markdown copy of every deck and document: one section per slide
(`## [NNN] EYEBROW · Title (sldId N)`), code boxes as fenced blocks tagged with the chip
language, speaker notes as a `>` block. The `content-ok` job runs
`python3 scripts/deck_text.py --check`, the voice scan (ban tier) over `lgtm-presentation`
and `scripts/validate_site.py`, which applies the positional and old-engine checks and
the stale-stack denylist (`scripts/deck-denylist.json`) to the text copies, so a
deck cannot drift from its text, regress to a replaced library, or reintroduce hype or
positional language unnoticed.

## Pins

The decks name the same versions as the site and `examples/`:

- Languages and frameworks: Python 3.14 (FastAPI 0.143.0, aiokafka 0.14.0, faust-streaming
  0.15.3), Spring Boot 4.1.1 with Jackson 3, Quarkus 3.40.1, Java 25, .NET 10.0.12 with
  Confluent.Kafka 2.16.0 and Streamiz 1.8.2, Go 1.27.2 (franz-go 1.22.1, pgx 5.11.0,
  golang-jwt 5.3.1, goka 1.1.17), C++23 on GCC 15 with CMake 4.4.4 and librdkafka 2.14.2.
- Platform: Kafka 4.3.1, Postgres 18, Redis 8.10.2 (AGPLv3 option), Debezium 3.7.0.Final,
  Apicurio Registry 3.3.3, flagd v0.17.0, grafana/otel-lgtm 0.36.0, Envoy v1.39.3.
- Kubernetes: minikube v1.39.0 with Kubernetes v1.36.5, Strimzi 1.2.0, Helm v4.3.0,
  kubeconform v0.8.0.
- Tests and CI: newman 6.2.3, `actions/checkout@v7`, `actions/upload-artifact@v7`.
- Container runtime: Docker Engine with `docker compose`; images are UBI 10 with Java 25
  and Python 3.14 (UBI 9 for .NET, which has no UBI 10 image).

The locked language stacks are listed in `CLAUDE.md`; the full pin table is in
`_plans/modernization-plan.md`.

## Language stacks

- **Go** uses `net/http` (1.22 `ServeMux`), franz-go, pgx v5, go-redis v9, gqlgen,
  golang-jwt v5, the OTel Go SDK with `log/slog`, sony/gobreaker v2 and cenkalti/backoff,
  gopher-lua, goka, coder/websocket and the OpenFeature Go SDK with flagd. Windowing in
  goka is manual time-bucketing, and OTel is wired explicitly with `otelhttp` and `otelpgx`.
- **C++** uses C++23, Drogon, grpc++, cppgraphqlgen, the librdkafka C++ API (`rdkafka++`),
  libpq, redis-plus-plus, jwt-cpp, boost::sml, sol2 with Lua, and OpenTelemetry C++ with spdlog.
- **Valet key and claim check** follow `examples/12-security/<lang>` in every deck: a
  signed ticket the service mints and verifies itself (an HMAC-SHA256 token, an HS256 JWT in
  Go and C++), with object storage described generically. No cloud SDK appears anywhere.

## QA record

- `deck_text.py --check` passes for all eight decks, and every slide has notes.
- The voice scan reports no ban-tier hits over `lgtm-presentation`; the watch-tier hits
  that remain are recorded in `_plans/s12-manifest/watch-ledger.md` with a reason each.
- Every changed or added slide was rendered with the brand fonts and inspected;
  `deck_fit.py` is the layout check for a render.
- Code slides stay within 22 lines and their box; comment colouring is checked for `//`,
  `#`, `--` and `/* */` comments.
