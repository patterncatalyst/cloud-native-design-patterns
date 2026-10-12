# K8s-Environment-Access-Policies.pptx

18 slides (sldIds 256–273). Edit file: `lgtm-presentation/edits/K8s-Environment-Access-Policies.json`
(no `_shared.json`). 26 ops: 18 `replace` (voice 11, positional 1, stack 6, all `expect` 1 with
`sldIds`) and 8 `replace_picture`. No slides added, no notes missing.

Before → after (voice scanner over the text copy): ban 1 → 0, watch 16 → 8. The 8 survivors are
"em-dash pileup" on notes paragraphs whose dashes sit in separate sentences, one per sentence
(`notes-paragraph`; notes of slides 3, 5, 6, 7, 12, 13, 15, 17). Positional 1 → 0. kubeval 4 → 0.

## Changes

| Slide | sldId | Title | Category | Change |
|---|---|---|---|---|
| 1 | 256 | Kubernetes Environment Access Policies | voice | notes: "This deck covers …" opener → "The subject is …" |
| 2 | 257 | Why environment governance matters | voice | body and notes: two-dash aside → parentheses |
| 3 | 258 | Three environments, three risk profiles | voice | title → "Risk profiles by environment" (parallel-number title); notes "in the rest of the deck" (ban) → "in the model" |
| 3 | 258 | | stack | figure → `k8s-policy-env-rbac.png` (ASCII arrows; the embedded PNG shows missing-glyph boxes) |
| 4 | 259 | RBAC: the Kubernetes gate | voice, positional | notes: two-dash aside rewritten; "The next slide maps these verbs …" → "The environment-specific RBAC matrix maps these verbs to each environment." |
| 7 | 262 | NetworkPolicy by environment | stack | figure → `k8s-policy-namespace-isolation.png` |
| 8 | 263 | Policy-as-code with OPA Gatekeeper | stack | figure → `k8s-12-policy-as-code.png` (current site wording) |
| 9 | 264 | GitOps-gated production changes | stack | body "CI validates (kubeval, conftest)" → kubeconform; notes: kubeconform v0.8.0 against the Kubernetes and CRD schemas; figure → `k8s-policy-gitops-flow.png` (CI Lint box: kubeconform, conftest) |
| 10 | 265 | The four-layer L7 stack | voice, stack | notes: two dash asides → parentheses; figure → `k8s-22-l7-layers.png` (S11 wording "the path is observable") |
| 11 | 266 | Istio AuthorizationPolicy | voice | notes: "particularly powerful" sentence → "In production this guarantees …" |
| 12 | 267 | Traffic steering for safe rollouts | stack | figure → `k8s-22-traffic-steering.png` |
| 13 | 268 | Namespace isolation architecture | stack | figure → `k8s-policy-namespace-isolation.png` |
| 14 | 269 | CI/CD validation pipeline | stack, voice | body "Schema validation (kubeval)" → kubeconform; notes: dash aside → parentheses, "kubeval or kubeconform" → "kubeconform v0.8.0 … including custom resources through the CRDs-catalog schemas"; figure → `k8s-policy-ci-pipeline.png` (Schema Check: kubeconform v0.8.0; last box "Prod"; caption "Fail at any stage: PR blocked.") |
| 15 | 270 | Audit & compliance | voice | notes: "— allow or deny —" → commas |
| 18 | 273 | References | voice | "ArgoCD — … · Flux — …" → colons; notes: PSP sentence now says PodSecurityPolicy was removed in Kubernetes 1.25 |

Eyebrows (`THREE ENVIRONMENTS`, `CI/CD PIPELINE`, …) stay: `design-label`.

## Figures

Every content figure of this deck has a source in `assets/diagrams/` (`policy-env-rbac`,
`policy-namespace-isolation`, `12-policy-as-code`, `policy-gitops-flow`, `22-l7-layers`,
`22-traffic-steering`, `policy-ci-pipeline`). The embedded PNGs were rendered without a font that
has `→`/`←`/`✓`, so they show boxes (for example "RoleBinding ▮ view only", "PR ▮ CI ▮ review ▮
sync"), and two of them name kubeval. The replacements are rendered with cairosvg 2.9.1 at 1400 px
from copies in `lgtm-presentation/edits/png/src/k8s-*.svg`: arrows written as `->` / `<-` / `<->`,
`✓` as "Prod", and the kubeval labels changed. `replace_picture` fits each into the old frame.
`pptx_bg.png` and the logos are unchanged.

Site follow-up (for the `docs(site)` commit, not applied here): `assets/diagrams/policy-ci-pipeline.{svg,excalidraw}`
("kubeval / kubeconform" → "kubeconform v0.8.0") and `assets/diagrams/policy-gitops-flow.{svg,excalidraw}`
("kubeval, conftest" → two lines "kubeconform", "conftest", as in `edits/png/src/k8s-policy-gitops-flow.svg`)
still name kubeval in both the `text` and `originalText` of the Excalidraw files. No chapter
includes these two figures; they exist for the deck.

## Sources

- kubeconform v0.8.0 and CRDs-catalog commit 63669a570e231d4f1f8396d229a1de512bcf0a34:
  `_plans/modernization-plan.md`, Target pins. kubeval is unmaintained upstream; the slides no longer
  name it.
- PodSecurityPolicy removed in Kubernetes 1.25 (Kubernetes deprecation guide).

## Unresolved

None.

## Decision 7 check (vendor-neutral, 2026-10-12)

Checked for ACS, OpenShift (Routes, SCCs, OperatorHub, `oc`, OpenShift GitOps), AWS, Azure and Google Cloud
reliance in the deck text, notes, figures (`k8s-*` PNGs) and `k8s-environment-policies.{md,docx}`: none. The deck
is built on RBAC, NetworkPolicy, OPA Gatekeeper, conftest, kubeconform, Argo CD and Istio. No change; the
decision-7 denylist entries report 0 hits on its text copy.
