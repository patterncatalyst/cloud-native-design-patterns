# Cloud-Native Design Patterns

A chaptered guide to designing cloud-native APIs — patterns, anti-patterns, and
runnable examples — with every code sample shown in **Spring Boot, Quarkus, .NET,
Python, C++, and Go** behind one set of language tabs. It is the companion site to
the *Designing Cloud-Native APIs* deck series; the decks themselves live in
[`lgtm-presentation/`](lgtm-presentation/).

**Live site:** <https://patterncatalyst.github.io/cloud-native-design-patterns/>

## What's inside

- **A setup guide, 13 chapters, 15 deep-dive appendices (A–O), and a glossary** —
  covering REST, gRPC, GraphQL, WebSockets, event-driven architecture, schemas and
  versioning, observability, resilience, and the patterns that tie them together.
- **Six languages, one set of tabs** — every code sample appears in Spring Boot,
  Quarkus, .NET, Python, C++, and Go, in that order, with no build plugin (the tabs
  are plain HTML + JS and work on GitHub Pages).
- **Paired diagrams** — every figure ships as a themed `name.svg` plus an editable
  `name.excalidraw` source under `assets/diagrams/`.
- **A companion deck series** — six Red Hat-branded conference decks (one per
  language) in [`lgtm-presentation/`](lgtm-presentation/).

## The running example

The whole guide builds one system — `order`, `payment`, `inventory`, `notification`,
and `shipping` services exchanging the `order.placed` fact — on infrastructure you can
run yourself: Podman locally and plain Kubernetes in production (no managed cloud),
with Kafka (Strimzi), PostgreSQL (CloudNativePG), Apicurio (schema registry), Istio,
KEDA, Debezium, and the Grafana LGTM observability stack.

## Run locally

```bash
bundle install
bundle exec jekyll serve --baseurl ""
```

Then open <http://localhost:4000>.

## Repository layout

| Path | What it holds |
|---|---|
| `_parts/` | the five Parts that form the homepage cards |
| `_docs/` | the setup guide, chapters, appendices A–O, and the glossary |
| `_includes/codetabs.html` + `assets/js/codetabs.js` | the multi-language code tabs (no plugin) |
| `assets/diagrams/` | paired `name.svg` + `name.excalidraw` figures |
| `lgtm-presentation/` | the six source decks + `BUILD.md` manifest |
| `_plans/` | the roadmap and the Phase-3 backlog |

## Deploy

Push to GitHub and set **Settings → Pages → Source: GitHub Actions** once. The
workflow in `.github/workflows/pages.yml` builds the site on every push and deploys
from `main`.

---

Open source · Apache 2.0
