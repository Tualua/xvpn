#!/usr/bin/env bash
# Wait for the CI run of the pushed HEAD and succeed only when that exact run concludes success.
# Usage: ci_watch.sh <workflow> [--dispatch]
#   --dispatch  dispatch the workflow on main first (for workflows that run only on workflow_dispatch /
#               pull_request / cron, such as molecule-vm) and wait for that dispatched run.
# A run cancelled by concurrency cancel-in-progress is not a code defect: it is re-selected (max 3 times).
set -euo pipefail

WORKFLOW="${1:?usage: ci_watch.sh <workflow> [--dispatch]}"
DISPATCH=0
[ "${2:-}" = "--dispatch" ] && DISPATCH=1

S="$(git rev-parse HEAD)"
REMOTE_HEAD="$(git ls-remote origin refs/heads/main | cut -f1)"
if [ "$REMOTE_HEAD" != "$S" ]; then
  echo "ci-watch: HEAD $S is not pushed to origin/main" >&2
  exit 1
fi

START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

dispatch() {
  START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  gh workflow run "$WORKFLOW" --ref main
}

# Print the id of the newest run of this workflow for HEAD, empty when none.
select_run() {
  local event="push"
  [ "$DISPATCH" -eq 1 ] && event="workflow_dispatch"
  gh run list --workflow "$WORKFLOW" --commit "$S" --limit 30 --json databaseId,createdAt,event \
    | START="$START" EVENT="$event" DISPATCH="$DISPATCH" python3 -c '
import json, os, sys
runs = [r for r in json.load(sys.stdin) if r["event"] == os.environ["EVENT"]]
if os.environ["DISPATCH"] == "1":
    runs = [r for r in runs if r["createdAt"] >= os.environ["START"]]
runs.sort(key=lambda r: r["createdAt"], reverse=True)
print(runs[0]["databaseId"] if runs else "")
'
}

wait_for_run() {
  local id=""
  for _ in $(seq 1 60); do
    id="$(select_run)"
    [ -n "$id" ] && break
    sleep 10
  done
  printf '%s' "$id"
}

[ "$DISPATCH" -eq 1 ] && dispatch

CANCELLED=0
while :; do
  ID="$(wait_for_run)"
  if [ -z "$ID" ]; then
    echo "ci-watch: no $WORKFLOW run for $S" >&2
    exit 1
  fi
  # The exit status of the watch is not trusted alone; the conclusion is read back below.
  gh run watch "$ID" --exit-status --interval 30 || true
  RESULT="$(gh run view "$ID" --json conclusion,headSha --jq '.conclusion + " " + .headSha')"
  CONCLUSION="${RESULT%% *}"
  SHA="${RESULT##* }"
  if [ "$SHA" != "$S" ]; then
    echo "ci-watch: run $ID is for $SHA, not $S" >&2
    exit 1
  fi
  case "$CONCLUSION" in
    success)
      echo "ci-watch: $WORKFLOW run $ID success for $S"
      exit 0
      ;;
    cancelled)
      CANCELLED=$((CANCELLED + 1))
      if [ "$CANCELLED" -gt 3 ]; then
        echo "ci-watch: $WORKFLOW runs for $S keep getting cancelled" >&2
        exit 1
      fi
      echo "ci-watch: run $ID cancelled, re-selecting"
      sleep 30
      if [ "$DISPATCH" -eq 1 ]; then
        NEWER="$(select_run)"
        [ "$NEWER" = "$ID" ] && dispatch
      fi
      ;;
    *)
      echo "ci-watch: $WORKFLOW run $ID concluded '$CONCLUSION' for $S" >&2
      exit 1
      ;;
  esac
done
