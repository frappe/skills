#!/bin/bash
# watch-pr.sh <pr-number> --bot <login> [--bot <login> ...] [--repo owner/name]
#             [--since <iso8601>] [--trigger <comment> ...] [--quiet <seconds>]
#             [--timeout <seconds>] [--interval <seconds>]
#
# Streams review bot activity on a PR: one line per new or edited comment or
# review from a watched bot. Exits 0 when the round is complete:
#   - every --bot has posted or edited something at or after <since>, AND
#   - no watched bot has posted or edited anything for --quiet seconds,
#     so a bot that edits a "reviewing..." placeholder is not cut off.
# Exit 2 on timeout, exit 3 if the gh queries fail. Both print what was seen.
#
# <since> defaults to the current UTC time: start the watch right after the
# push. Each --trigger posts its <comment> first (for bots that review only
# when asked), and <since> becomes the first posted comment's server timestamp.
#
# Claude Code: run through the Monitor tool (persistent: true) so each event
# re-invokes you. Codex: run in the foreground with a long timeout.

set -u -o pipefail

USAGE="usage: watch-pr.sh <pr-number> --bot <login> [--bot <login> ...] [--repo o/r] [--since iso] [--trigger comment ...] [--quiet s] [--timeout s] [--interval s]"
PR="${1:?$USAGE}"
shift
REPO="" SINCE="" QUIET=60 TIMEOUT=900 INTERVAL=30
BOTS=() TRIGGERS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --bot) BOTS+=("${2%\[bot\]}"); shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --since) SINCE="$2"; shift 2 ;;
    --trigger) TRIGGERS+=("$2"); shift 2 ;;
    --quiet) QUIET="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done
[ "${#BOTS[@]}" -gt 0 ] || { echo "$USAGE" >&2; exit 1; }

[ -n "$REPO" ] || REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
BOTS_JSON=$(printf '%s\n' "${BOTS[@]}" | jq -R . | jq -sc .)

# Comments post in order, so the first one has the earliest timestamp.
if [ "${#TRIGGERS[@]}" -gt 0 ]; then
  SINCE=""
  for TRIGGER in "${TRIGGERS[@]}"; do
    AT=$(gh api "repos/$REPO/issues/$PR/comments" -f body="$TRIGGER" --jq .created_at)
    echo "TRIGGER posted \"$TRIGGER\" at $AT"
    [ -n "$SINCE" ] || SINCE=$AT
  done
fi
# GitHub timestamps are UTC with a Z suffix, so plain string comparison works.
[ -n "$SINCE" ] || SINCE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

SEEN=$(mktemp)
trap 'rm -f "$SEEN"' EXIT

# REST logins carry a [bot] suffix; strip it so --bot accepts either form.
# `edited` is updated_at: a bot that edits one summary comment in place
# shows up as activity, as does a bot that posts a new comment each round.
snapshot() {
  {
    gh api "repos/$REPO/issues/$PR/comments" --paginate \
      --jq '.[]|{who:.user.login, at:.created_at, edited:.updated_at, url:.html_url, kind:"summary", body:.body}'
    gh api "repos/$REPO/pulls/$PR/comments" --paginate \
      --jq '.[]|{who:.user.login, at:.created_at, edited:.updated_at, url:.html_url, kind:"inline", body:.body}'
    gh api "repos/$REPO/pulls/$PR/reviews" --paginate \
      --jq '.[]|select(.submitted_at != null)|{who:.user.login, at:.submitted_at, edited:.submitted_at, url:.html_url, kind:"review", body:.body}'
  } 2>/dev/null | jq -c --argjson bots "$BOTS_JSON" \
    '.who |= sub("\\[bot\\]$"; "") | select(.who as $w | $bots | index($w))'
}

START=$(date +%s)
LAST_EVENT=$START
while true; do
  if ! SNAP=$(snapshot); then
    echo "ERROR gh query failed for $REPO#$PR"
    exit 3
  fi

  # Key on url+edited so an edited summary re-emits as a new event.
  while IFS= read -r item; do
    [ -n "$item" ] || continue
    KEY=$(printf '%s' "$item" | jq -r '.url + "@" + .edited')
    grep -qxF "$KEY" "$SEEN" 2>/dev/null && continue
    printf '%s\n' "$KEY" >> "$SEEN"
    LAST_EVENT=$(date +%s)
    printf '%s' "$item" | jq -r \
      '"\(.who) \(.kind) \(.edited) \(.url) :: " + ((.body // "")|gsub("\\s+"; " ")|.[0:200])'
  done <<< "$SNAP"

  WAITING=$(printf '%s' "$SNAP" | jq -sr --argjson bots "$BOTS_JSON" --arg since "$SINCE" \
    '[.[]|select(.edited >= $since)|.who] as $active | $bots - $active | join(" ")')
  QUIET_FOR=$(( $(date +%s) - LAST_EVENT ))

  if [ -z "$WAITING" ] && [ "$QUIET_FOR" -ge "$QUIET" ]; then
    echo "ROUND COMPLETE since=$SINCE"
    exit 0
  fi

  ELAPSED=$(( $(date +%s) - START ))
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "TIMEOUT ${ELAPSED}s since=$SINCE waiting for: ${WAITING:-none (still active)}"
    printf '%s' "$SNAP" | jq -sr 'sort_by(.edited)|reverse|.[0:3][]|"  last: \(.who) \(.edited) \(.url)"'
    echo "  A timeout is not an answer. Read the comments before you conclude anything."
    exit 2
  fi
  sleep "$INTERVAL"
done
