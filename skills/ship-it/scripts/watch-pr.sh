#!/bin/bash
# watch-pr.sh <pr-number> [--repo owner/name] [--sha <head-sha>] [--since <iso8601>]
#             [--trigger] [--no-barista] [--timeout <seconds>] [--interval <seconds>]
#
# Streams bot review activity on a PR: one line per new or edited greptile /
# barista item. Exits 0 when the round is complete:
#   - a greptile-apps comment names <sha>, AND
#   - a barista-for-frappe comment was created after <since>.
# Exit 2 on timeout, exit 3 if the gh queries fail. Both print what was seen.
#
# Barista runs only in repos that install the workflow. The script detects it
# and, where it is absent, skips the trigger and waits for greptile alone.
# --no-barista forces that mode.
#
# --trigger posts `/barista review` first and takes <since> from the created
# comment's server timestamp. Use it on every round after the first: barista
# does NOT re-review on push, and a locally computed cutoff gets the timezone
# wrong.
#
# Claude Code: run through the Monitor tool (persistent: true) so each event
# re-invokes you. Codex: run in the foreground with a long timeout.

set -u -o pipefail

PR="${1:?usage: watch-pr.sh <pr-number> [--repo o/r] [--sha x] [--since iso] [--trigger] [--no-barista] [--timeout s] [--interval s]}"
shift
REPO="" SHA="" SINCE="" TRIGGER=0 BARISTA=auto TIMEOUT=900 INTERVAL=30
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --sha) SHA="$2"; shift 2 ;;
    --since) SINCE="$2"; shift 2 ;;
    --trigger) TRIGGER=1; shift ;;
    --no-barista) BARISTA=no; shift ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Always resolve REPO, so no command expands an empty array (bash 3.2 + set -u).
[ -n "$REPO" ] || REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
# Full 40-char OID. Greptile names the full SHA; a short one never matches.
[ -n "$SHA" ] || SHA=$(gh pr view "$PR" -R "$REPO" --json headRefOid --jq .headRefOid)

# Barista is per-repo: only repos with the workflow run it.
# Posting `/barista review` where nothing listens only adds noise to the PR.
if [ "$BARISTA" = "auto" ]; then
  if gh api "repos/$REPO/contents/.github/workflows" --jq '.[].name' 2>/dev/null \
       | grep -qE '^barista-review\.ya?ml$'; then
    BARISTA=yes
  else
    BARISTA=no
  fi
fi
[ "$BARISTA" = "yes" ] || echo "NOTE $REPO has no barista-review workflow: greptile only"

if [ "$TRIGGER" = "1" ] && [ "$BARISTA" = "yes" ]; then
  SINCE=$(gh api "repos/$REPO/issues/$PR/comments" -f body='/barista review' --jq .created_at)
  echo "TRIGGER posted /barista review at $SINCE"
fi

SEEN=$(mktemp)
trap 'rm -f "$SEEN"' EXIT

# REST logins carry a [bot] suffix; GraphQL (gh pr view) does not. Match both.
BOTS='^(greptile-apps|barista-for-frappe)(\[bot\])?$'

# REST only. `gh pr view --json comments` has no updated_at, which is what broke
# every --since round. Bots post ISSUE comments, so reviewDecision stays "none".
snapshot() {
  {
    gh api "repos/$REPO/issues/$PR/comments" --paginate \
      --jq '.[]|{who:.user.login, at:.created_at, edited:.updated_at, url:.html_url, kind:"summary", body:.body}'
    gh api "repos/$REPO/pulls/$PR/comments" --paginate \
      --jq '.[]|{who:.user.login, at:.created_at, edited:.updated_at, url:.html_url, kind:"inline", body:.body}'
    gh api "repos/$REPO/pulls/$PR/reviews" --paginate \
      --jq '.[]|select(.submitted_at != null)|{who:.user.login, at:.submitted_at, edited:.submitted_at, url:.html_url, kind:"review", body:.body}'
  } 2>/dev/null | jq -c --arg bots "$BOTS" 'select(.who|test($bots))'
}

START=$(date +%s)
while true; do
  if ! SNAP=$(snapshot); then
    echo "ERROR gh query failed for $REPO#$PR"
    exit 3
  fi

  # Key on url+edited so an edited greptile summary re-emits as a new event.
  while IFS= read -r item; do
    [ -n "$item" ] || continue
    KEY=$(printf '%s' "$item" | jq -r '.url + "@" + .edited')
    grep -qxF "$KEY" "$SEEN" 2>/dev/null && continue
    printf '%s\n' "$KEY" >> "$SEEN"
    printf '%s' "$item" | jq -r '
      (if (.who|startswith("greptile")) then "GREPTILE" else "BARISTA" end) as $bot
      | (.body // "") as $b
      # Prefer a verdict line (✅/💬/🛑 ...); fall back to an old-style n/5 score.
      | ([$b|capture("(?<v>(✅|💬|🛑)[^\\n]*)").v][0]
         // ([$b|capture("(?<s>[0-5])/5").s][0] | if . then . + "/5" else null end)
         // "-") as $verdict
      | "\($bot) [\($verdict)] \(.kind) \(.at) \(.url) :: "
        + ((.body // "")|gsub("\\s+"; " ")|.[0:200])'
  done <<< "$SNAP"

  # Greptile edits one summary comment in place, so match on the SHA it names.
  GREPTILE_OK=$(printf '%s' "$SNAP" | jq -s --arg sha "$SHA" \
    '[.[]|select(.who|startswith("greptile"))|select(.body|contains($sha))]|length>0')
  # Barista posts a NEW comment each round: compare created_at, never updated_at.
  if [ "$BARISTA" = "yes" ]; then
    BARISTA_OK=$(printf '%s' "$SNAP" | jq -s --arg since "$SINCE" \
      '[.[]|select(.who|startswith("barista"))|select($since=="" or .at > $since)]|length>0')
  else
    BARISTA_OK=true
  fi

  if [ "$GREPTILE_OK" = "true" ] && [ "$BARISTA_OK" = "true" ]; then
    echo "ROUND COMPLETE sha=${SHA:0:8} since=${SINCE:-none}"
    exit 0
  fi

  ELAPSED=$(( $(date +%s) - START ))
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "TIMEOUT ${ELAPSED}s greptile=$GREPTILE_OK barista=$BARISTA_OK sha=${SHA:0:8} since=${SINCE:-none}"
    printf '%s' "$SNAP" | jq -sr 'sort_by(.at)|reverse|.[0:3][]|"  last: \(.who) \(.at) \(.url)"'
    echo "  A timeout is not an answer. Read the comments before you conclude anything."
    [ "$BARISTA" = "yes" ] && \
      echo "  If barista is missing: gh pr comment $PR -R $REPO --body '/barista review'"
    exit 2
  fi
  sleep "$INTERVAL"
done
