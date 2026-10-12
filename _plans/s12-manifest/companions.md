# Companion documents: edits

The two policy decks have a Markdown companion and a Word document built from it:
`lgtm-presentation/k8s-environment-policies.{md,docx}` and
`lgtm-presentation/network-policy-process-advisory.{md,docx}`. The `.md` is edited directly; the
`.docx` is edited in place with python-docx 1.2.0 (S12 venv). No converter regenerates the docx.

## Equality today

Word-level comparison (docx paragraphs and table cells in body order against the md with Markdown
markers, link targets and fence tags removed) shows only formatting differences today: list and
heading numbers (`1.` … rendered as numbered headings), fence language tags, the `!` of image
markers and `[ ]` checkboxes. The docx keeps the md's hard line wraps: one md line is one docx
paragraph, so each md line edit has a docx paragraph edit. The docx has no hyperlinks (the
References list holds the labels only), so URL edits apply to the md alone. After the edits the
comparison shows the same formatting-only differences (24 and 23 blocks, none textual), so
acceptance criterion 8 holds. Proof: the edits were applied to scratch copies
(`s12/manifest/fork-policy/comp/`) and compared; every md find matched exactly once and every docx
anchor matched its expected old text.

Voice scan of the patched md copies: 0 ban; one watch hit left, the `Change velocity` table row in
`k8s-environment-policies.md` (three em dashes in three cells, `table-data`). Positional terms 0;
kubeval, OpenShift 4.16/4.18 links and ACS 3.69 links 0.

Em dashes in the companions follow S11's line rule (split prose lines with three or more), not the
deck's sentence rule, because the companion is hard-wrapped prose and the docx mirrors each line.

## k8s-environment-policies.md (3 edits)

| # | Find (whole line, exactly once) | Replace with | Why |
|---|---|---|---|
| 1 | `## 2. Three environments, three risk profiles` | `## 2. Risk profiles by environment` | parallel-number title; matches deck slide 3 |
| 2 | ``2. **CI validates** — `kubeval` checks schema, `conftest` runs OPA policies, a`` | ``2. **CI validates** — `kubeconform` checks schema, `conftest` runs OPA policies, a`` | kubeconform v0.8.0 pin |
| 3 | `\| **Schema validation** \| kubeval, kubeconform \| Invalid YAML, unknown fields, wrong API versions \|` | `\| **Schema validation** \| kubeconform v0.8.0 \| Invalid YAML, unknown fields, wrong API versions \|` | kubeconform v0.8.0 pin |

## k8s-environment-policies.docx (3 edits)

Indices are `Document.paragraphs` / `Document.tables` positions in the committed file. Replace the
text of the named run only; the run keeps its formatting.

| # | Location | Run | Old run text | New run text |
|---|---|---|---|---|
| 1 | paragraph 15 (Heading 2) | 0 | `2. Three environments, three risk profiles` | `2. Risk profiles by environment` |
| 2 | paragraph 91 (List Number) | 2 (Consolas) | `kubeval` | `kubeconform` |
| 3 | table 3, row 1, cell 1, paragraph 0 | 0 | `kubeval, kubeconform` | `kubeconform v0.8.0` |

## network-policy-process-advisory.md (decision 7: reworked to upstream Kubernetes and open source)

Supersedes the nine find/replace edits and the docx edits of the 0aeddfc manifest. The companion is rewritten
to the same process, phases and section structure with upstream APIs and open-source tools (facts and
citations: `Network-Policy-Process-Advisory.md`):

- ACS (network graph, baselines, `stackrox-generated-*` policies, build-time tools, anomalous-flow alerts) →
  the CNI's flow logs (Hubble with Cilium; Goldmane/Whisker with Calico), Inspektor Gadget's
  `advise_networkpolicy` gadget for generated NetworkPolicy, Calico StagedNetworkPolicy for a preview,
  a baseline diff in CI, Falco for runtime egress alerts.
- AdminNetworkPolicy / BaselineAdminNetworkPolicy on OVN-Kubernetes → upstream ClusterNetworkPolicy
  (`policy.networking.k8s.io/v1alpha2`, network-policy-api v0.2.0) in its Admin and Baseline tiers; priority
  0-1000; Accept/Deny/Pass. One paragraph records that ANP/BANP (v1alpha1) are previous upstream APIs and that
  Calico 3.32 no longer enforces them.
- EgressFirewall → egress rules: Admin-tier CNP `networks` peers (standard), `domainNames` (experimental,
  Accept only), Cilium `toFQDNs` for DNS-based egress.
- `oc apply`, `oc adm must-gather`, OpenShift GitOps → `kubectl apply`, `cilium sysdump` /
  `calicoctl cluster diags`, Argo CD (self-heal, prune).
- CI lint adds `kyverno test`, `gator verify` and `trivy config`; golden-path provisioning names Kyverno's
  `add-network-policy` generate rule.
- "Red Hat's recommended approach", "What Red Hat typically sees", "Red Hat recommends", "lessons Red Hat
  hears", "escalation to Red Hat support" and the "Red Hat Advisory" title → neutral wording (the
  recommendations now name upstream projects, so they are not attributed to a vendor); "Palo Alto,
  Fortinet" → "a traditional perimeter firewall appliance".
- References: the OpenShift and ACS documentation links → network-policy-api (site, v0.2.0 release,
  implementations), Calico v3.32 release notes, Cilium network policy, Inspektor Gadget, Kyverno
  add-network-policy; the Kubernetes, CNCF and RBAC links stay.

The exact target text is the file `_plans/s12-manifest/companions/network-policy-process-advisory.md`: copy it
over `lgtm-presentation/network-policy-process-advisory.md` (whole-file replacement; same section order, same
fenced blocks, same three figure references).

## network-policy-process-advisory.docx (decision 7: paragraph-level edits, generated)

The docx keeps one paragraph per md line, so the md change maps to paragraph operations.
`tools/companion_docx.py` derives them: it parses both md revisions into the docx paragraph model, checks that
the committed md reproduces the committed docx text exactly (353 blocks before: 351 paragraphs and 2 tables; 371
after), aligns old and new with difflib and applies:

| Operation | Count | What |
|---|---|---|
| `set` | 128 | paragraph text replaced; runs rebuilt from the md's `**bold**`, `` `code` `` and `*italic*` spans with the formatting of the paragraph's own runs of that kind (or the first run of that kind in the document) |
| `insert_after` | 18 | new paragraph, a clone of the first paragraph of the same style (Normal, List Bullet, List Number), inserted after the preceding block |
| `delete` | 0 | |
| `set_cell` | 4 | table cells (ownership table row 1; governance table rows Network segmentation, GitOps, Audit) |
| `replace_image` | 3 | `rId9` (image1, tier evaluation), `rId10` (image2, CI/CD pipeline), `rId11` (image3, ownership) get `lgtm-presentation/edits/png/net-advisory-*.png`; the inline extent height is rescaled to the new aspect ratio, width unchanged |

The full list (old block index, style, new text) is
`_plans/s12-manifest/companions/network-policy-process-advisory.docx-ops.json`. Apply with the S12 venv python:

```bash
V=/tmp/claude-1000/-home-rsedor-Dev/0dea024d-0bf0-4ae5-bddd-7dec0cf60b22/scratchpad/s12/venv/bin/python
P=lgtm-presentation/edits/png
$V _plans/s12-manifest/tools/companion_docx.py \
   lgtm-presentation/network-policy-process-advisory.md \
   _plans/s12-manifest/companions/network-policy-process-advisory.md \
   lgtm-presentation/network-policy-process-advisory.docx lgtm-presentation/network-policy-process-advisory.docx \
   --png rId9=$P/net-advisory-tier-evaluation.png rId10=$P/net-advisory-ci-pipeline.png \
         rId11=$P/net-advisory-team-ownership.png
cp _plans/s12-manifest/companions/network-policy-process-advisory.md lgtm-presentation/network-policy-process-advisory.md
```

Run the docx step before copying the md (it reads the committed md as the old revision). The script re-reads
its output and fails unless every docx paragraph and table cell equals the new md's text (acceptance
criterion 8); on the scratch copy it printed `{"ok": true, "set": 128, "set_cell": 4, "insert": 18,
"delete": 0, "images": 3, "blocks": 371}`, and a LibreOffice PDF of the result (15 pages) contains no
OpenShift, ACS, OVN or EgressFirewall. Known formatting carry-over (as in the original): a `**bold**` span
that crosses an md line break stays as literal asterisks in the docx (`**default-deny at` /
`the Baseline tier**`), exactly like the committed docx's `**default-deny at` / `the BANP tier**`.

## After applying

`python3 scripts/deck_text.py --write` regenerates `lgtm-presentation/text/k8s-environment-policies.md`
and `network-policy-process-advisory.md`; then run the voice scan, `validate_site.py` (positional
check over `lgtm-presentation/*.md` from step 15) and the word-level md/docx comparison.
