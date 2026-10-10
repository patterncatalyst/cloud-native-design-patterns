#!/usr/bin/env bash
# Bring each example up with docker compose, run its verify.sh, and tear it
# down again, one at a time. Results go to a TSV so a long run can be resumed
# and summarised.
#
#   scripts/verify-matrix.sh                       # every example, every language
#   scripts/verify-matrix.sh go python             # only these languages
#   scripts/verify-matrix.sh 05-event-driven/go    # one target
#   OUT=/path/to/dir scripts/verify-matrix.sh ...  # where logs and results go
#   SKIP_PASSED=1 scripts/verify-matrix.sh ...     # skip targets already PASS in results.tsv
#
# A target is examples/<NN-name>/<lang>/ with a compose.yaml, or an example
# with a compose.yaml at its root (09, 28). verify.sh always runs from the
# example directory.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

OUT="${OUT:-${TMPDIR:-/tmp}/cndp-matrix}"
mkdir -p "$OUT/logs"
RESULTS="$OUT/results.tsv"
touch "$RESULTS"

LANGS=(spring-boot quarkus dotnet python cpp go)

targets=()
filters=("$@")
for ex in examples/[0-9][0-9]-*/; do
  ex="${ex%/}"; ex="${ex#examples/}"
  if [ -f "examples/$ex/compose.yaml" ]; then
    targets+=("$ex")
  fi
  for lang in "${LANGS[@]}"; do
    [ -f "examples/$ex/$lang/compose.yaml" ] && targets+=("$ex/$lang")
  done
done

selected=()
for t in "${targets[@]}"; do
  if [ "${#filters[@]}" -eq 0 ]; then selected+=("$t"); continue; fi
  for f in "${filters[@]}"; do
    case "$t" in
      "$f"|*/"$f"|"$f"/*) selected+=("$t"); break ;;
    esac
  done
done

running="$(docker ps -q | wc -l)"
if [ "$running" -ne 0 ]; then
  echo "refusing to start: $running container(s) already running (one workshop at a time)" >&2
  docker ps --format '  {{.Names}}' >&2
  exit 2
fi

echo "targets: ${#selected[@]}   results: $RESULTS"
for t in "${selected[@]}"; do
  if [ "${SKIP_PASSED:-0}" = 1 ] && grep -qP "^\Q$t\E\tPASS\t" "$RESULTS"; then
    echo "skip   $t (already PASS)"; continue
  fi
  ex="${t%%/*}"
  dir="examples/$t"
  log="$OUT/logs/${t//\//_}.log"
  start=$(date +%s)
  printf '%-45s ' "$t"

  status=PASS
  if ! (cd "$dir" && timeout 2700 docker compose up -d --build --wait --wait-timeout 600) >"$log" 2>&1; then
    status=UP-FAIL
  elif ! (cd "examples/$ex" && timeout 900 ./verify.sh) >>"$log" 2>&1; then
    status=VERIFY-FAIL
  fi
  if [ "$status" != PASS ]; then
    (cd "$dir" && docker compose ps -a && docker compose logs --tail 80) >>"$log" 2>&1
  fi
  (cd "$dir" && docker compose down -v --remove-orphans) >>"$log" 2>&1

  secs=$(( $(date +%s) - start ))
  # Prefer the standard "==> Results:" line; fall back to a plain "Result:" line.
  summary="$(grep -E '==> Results:' "$log" | tail -1 | sed 's/.*Results: //' || true)"
  if [ -z "$summary" ]; then
    summary="$(grep -E '^ *Result:' "$log" | tail -1 | sed 's/.*Result: //' || true)"
  fi
  printf '%-12s %4ss  %s\n' "$status" "$secs" "$summary"
  # Replace any earlier row for this target.
  grep -vP "^\Q$t\E\t" "$RESULTS" >"$RESULTS.tmp" || true
  printf '%s\t%s\t%s\t%s\t%s\n' "$t" "$status" "$secs" "$summary" "$(date -Iseconds)" >>"$RESULTS.tmp"
  mv "$RESULTS.tmp" "$RESULTS"
done

echo
awk -F'\t' '{c[$2]++} END {for (s in c) printf "%s=%d  ", s, c[s]; print ""}' "$RESULTS"
! grep -qvP '\tPASS\t' "$RESULTS"
