# Cloud-Native Design Patterns

A chaptered guide to designing cloud-native APIs — patterns, anti-patterns, and
runnable examples — shown in **Spring Boot, Quarkus, .NET, Python, C++, and Go**
behind one set of code tabs. It is the companion site to the *Designing
Cloud-Native APIs* deck series; the decks themselves live in
[`lgtm-presentation/`](lgtm-presentation/).

## Run locally

```bash
bundle install
bundle exec jekyll serve --baseurl ""
```

Then open <http://localhost:4000>.

## Layout

- `_parts/` — the five Parts (homepage cards).
- `_docs/` — one chapter per deck section + appendix + glossary.
- `_includes/codetabs.html` + `assets/js/codetabs.js` — the multi-language code
  tabs (no plugin; works on GitHub Pages).
- `assets/diagrams/` — paired `name.svg` + `name.excalidraw`.
- `lgtm-presentation/` — the five source decks.
- `_plans/iteration-plan.md` — the roadmap.

## Deploy

Push to GitHub and set **Settings → Pages → Source: GitHub Actions** once. The
workflow in `.github/workflows/pages.yml` builds on push and deploys from `main`.

Open source · Apache 2.0
