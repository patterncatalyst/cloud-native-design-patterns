# Final QA pass — r70

A mechanical sweep across the whole site after the Phase-3 enrichment (items 4–9),
the Go six-language parity, the nav and GitHub-link fixes, and the Chapter 05
substrate-architecture expansion.

## Scope

All 30 documents in `_docs/`, every figure in `assets/diagrams/`, the six decks in
`lgtm-presentation/`, and `_config.yml`.

## Checks and results

| Check | Result |
|---|---|
| Front-matter parses; `title` / `order` / `duration` present | ✅ all 30 |
| Liquid raw-guard balance (`{% raw %}` / `{% endraw %}`) | ✅ balanced everywhere |
| No unguarded `{{` outside raw guards | ✅ 0 |
| Codetab block count matches `langs=` count | ✅ all 39 codetabs |
| Codetab language order is the canonical six | ✅ all 39 use `Spring Boot \| Quarkus \| .NET \| Python \| C++ \| Go` |
| Figure captions unique and sequential per doc | ✅ all docs |
| Every `file=` figure has both `.svg` and `.excalidraw` | ✅ no missing files |
| SVG ↔ Excalidraw pairing | ✅ no unpaired files either direction |
| Orphaned diagrams (on disk, unreferenced) | ✅ 0 |
| Positional language (`above` / `below` / `next slide` / `see slide`) | ✅ none in rendered content |
| Stale markers (`TODO`, `FIXME`, `PLACEHOLDER`, `RobertSedor`) | ✅ none |
| Include partials (`excalidraw.html`, `codetabs.html`) present | ✅ |
| `_config.yml` GitHub owner | ✅ `patterncatalyst/cloud-native-design-patterns` |

## Inventory

- **30 docs**: a setup guide, 13 chapters (01–13), 15 appendices (A–O), and the glossary.
- **39 codetabs**, all six-language and in canonical order.
- **126 figures**, each a paired `.svg` + `.excalidraw`, zero orphans.
- **6 decks** in `lgtm-presentation/` with a `BUILD.md` manifest.

## Conclusion

The site is publish-clean — no structural, Liquid, codetab, figure, or link defects
found. The top-level `README.md` was rewritten to match this state (six languages,
six decks, the running-example system, the live-site URL, and the current layout).
