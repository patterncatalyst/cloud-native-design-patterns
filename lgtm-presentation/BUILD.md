# Designing Cloud-Native APIs — deck build record

Red Hat-branded 16:9 `.pptx` decks in the house style (Overpass / Red Hat Text /
Red Hat Mono, `#EE0000` accents, logo on every slide, thick speaker notes). One
deck per language; the cover, agenda, overview, section dividers, and every
diagram are language-agnostic and shared, so the decks differ only in their code
slides, language chips, code-specific captions, and per-language speaker notes.

| Deck | Language / stack | Slides | Rev | Build method |
|------|------------------|-------:|-----|--------------|
| `Designing-Cloud-Native-APIs-Python.pptx` | Python · FastAPI | 272 | r32 | pptxgenjs builder + OPC merge (App. N/O) — **canonical source** |
| `Designing-Cloud-Native-APIs-Spring.pptx` | Spring Boot | 276 | r32 | pptxgenjs builder + merge |
| `Designing-Cloud-Native-APIs-Quarkus.pptx` | Quarkus | 272 | r32 | pptxgenjs builder + merge |
| `Designing-Cloud-Native-APIs-DotNet.pptx` | .NET | 286 | r32 | pptxgenjs builder + merge (extra Appendix J) |
| `Designing-Cloud-Native-APIs-Cpp.pptx` | C++20/23 | 272 | r32 | pptxgenjs builder + merge |
| `Designing-Cloud-Native-APIs-Go.pptx` | **Go 1.26** | **272** | **r01.0** | **in-place retarget of the Python deck** |

Versioned deliverables ship as `<name>-rNN.x.pptx` to `/mnt/user-data/outputs/`;
these repo copies are the current bare-named builds. Python is r32; the four
sibling language decks track it; **Go is the newest deck and carries its own
counter starting at r01.0.**

## Go deck (r01.0) — how it was built

The Go deck was produced by copying the canonical Python deck and editing only
language-specific surfaces, leaving all shared slides byte-identical. Approach
chosen because Go's gap profile and appendix sequence (`A B C D E F G H I K L M N O`)
match C++ exactly, so no structural divergence was needed.

- **43 code slides** retargeted to idiomatic Go 1.26 (error-returning handlers and
  explicit `if err != nil`, not brevity-eliding). Each slide is a teaching
  fragment of **≤ 22 lines** so it renders inside the fixed code box at 10.5–12.5pt.
- **17 language-agnostic code slides** (Istio / KEDA / OPA YAML, proto, flagd /
  Postman JSON, HAProxy / nginx, GitHub Actions, newman) were left untouched.
- Language chips, code-specific captions, the acronym glossary (runtime row:
  `no WSGI/ASGI split`, `no GIL`, `go.mod`), the L7-routing appendix, and the
  speaker notes were all retargeted; no Python framework names remain.

### Locked Go stack (Robert-approved)

Go 1.26, idiomatic "Effective/Idiomatic Go"; **net/http** stdlib only (1.22
`ServeMux`, no chi/gin); **franz-go** (Kafka); **pgx v5** (Postgres); **go-redis v9**;
**gqlgen** (GraphQL, schema-first); **golang-jwt v5**; **OTel Go SDK + log/slog**
(otelhttp/otelslog, no auto-agent); **sony/gobreaker** + **cenkalti/backoff**;
**gopher-lua** (rule routing, parallels C++ sol2); **goka** (stream processing,
the Faust/Streams analogue — windowing is manual); **minio-go** (S3-compatible
object store, chosen over an AWS SDK for the no-managed-cloud constraint);
**coder/websocket**; **OpenFeature Go SDK + flagd**; `signal.NotifyContext` +
`atomic.Bool` for graceful shutdown; generics where they earn it (e.g.
`ReadThrough[T]`).

### Honest ecosystem framing (where Go has gaps)

- No Faust/Kafka-Streams-native windowing → goka with manual time-bucketing.
- No durable-rules engine → gopher-lua embedding a Lua ruleset (the sol2 parallel).
- No `-javaagent`-style OTel auto-attach → explicit `otelhttp` / `otelpgx` wrapping.

## QA (r01.0)

Full visual pass over all 272 slides + structural checks, all green:

- 0 code slides over 22 lines; no code-box clipping (every code slide rendered
  and inspected).
- 0 Python framework/library names in slide-visible text; 0 `python ·` chips.
- Edited prose / glossary slides checked for overflow — clean.
- Speaker notes present on 272/272 slides; the Red Hat logo on every slide.
- Comment coloring verified for `//` (Go/proto), `--` (Lua), and `#` (bash/graphql).
