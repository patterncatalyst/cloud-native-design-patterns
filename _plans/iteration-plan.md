---
title: "Iteration plan"
---

# Iteration plan

A chaptered companion to the *Designing Cloud-Native APIs* deck series. The book
mirrors the decks: every section and appendix becomes a chapter, the code is
shown for all five languages behind one set of tabs, and each hands-on chapter
gets a runnable example per language.

## r01 — scaffold + pattern proof (this iteration)

- Jekyll site scaffolded in the house style; homepage, parts, nav, theme.
- All five source decks committed under `lgtm-presentation/`.
- Multi-language **code tabs** built and wired (`_includes/codetabs.html`,
  `assets/js/codetabs.js`): Spring Boot / Quarkus / .NET / Python / C++, synced
  across the page and remembered across pages. Plugin-free, GitHub-Pages-safe.
- Five Parts (0–4) and a chapter stub for every section, appendix, and the
  glossary — the full card map is navigable.
- One chapter authored end to end as the pattern proof: **04 · Data**, with the
  reused outbox/CDC diagram and real five-language code from the decks.

## Phase 2 — author the chapters

Work the stubs into full chapters, one section at a time, reusing each deck
section's diagrams and rewriting its speaker notes into prose. Order of attack:
Part 0 setup, then Part 1 foundations, then the operational platform, security
and anti-patterns, and finally the appendices. Appendix J is .NET-only.

Each chapter: intro, the patterns with diagrams, the code behind the language
tabs, a "how the code works" walkthrough, and a cross-check. Unverified until the
matching example runs.

## Phase 3 — runnable examples and demos

One runnable example per hands-on chapter, per language, under `examples/` —
e.g. `examples/04-data/spring-boot`, `.../quarkus`, `.../dotnet`, `.../python`,
`.../cpp`. Each with a run script and a README that mirrors the chapter. On
Podman locally and plain Kubernetes in production. Running an example is what
moves its chapter from unverified to verified.

## Open decisions

- GitHub account/owner for the repo (the `github_username` in `_config.yml` is a
  placeholder).
- Demo directory convention: `examples/NN-name/<language>` is assumed above to
  fit the tutorial template; confirm before Phase 3.
