# Vendored professional-voice scanner

`scan.sh` and `patterns.tsv` are byte-identical copies from the lgtm-skills repository. They back
`scripts/voice-scan.sh`, which CI runs in the `content-ok` check.

| | |
|---|---|
| Source | https://github.com/patterncatalyst/lgtm-skills |
| Path | `skills/lgtm-professional-voice/scripts/{scan.sh,patterns.tsv}` |
| Commit | `a3350074a1df343b3bbd58a563f26bf0311a265a` (2026-10-11, lgtm-skills PRs #48 and #49) |
| License | the upstream repository has no LICENSE file; both repositories have the same owner (patterncatalyst), who vendored the copy here |

Do not edit these files here. Fix the scanner or its patterns upstream, merge, then re-vendor:

```bash
SHA=<new lgtm-skills commit>
P=skills/lgtm-professional-voice/scripts
git -C ../lgtm-skills show "${SHA}:${P}/scan.sh"      > scripts/voice/scan.sh
git -C ../lgtm-skills show "${SHA}:${P}/patterns.tsv" > scripts/voice/patterns.tsv
```

Then update the commit in this table. To confirm the copy still matches its source:

```bash
for f in scan.sh patterns.tsv; do
  diff <(git -C ../lgtm-skills show "${SHA}:${P}/$f") "scripts/voice/$f" && echo "$f matches"
done
```
