#!/bin/bash
# watch-pr.sh <pr-number> --bot <login> [--bot <login> ...]
#             [--trigger <comment> ...] [--since <iso8601>] [--timeout <seconds>]
#
# Streams review bot responses on a PR: one line per new or edited comment or
# review from a watched bot, polled every 30 seconds in the current repo.
# Before it posts any --trigger, it records every watched bot item it can see.
# An item is a response when it is not in that starting set, or when it was
# edited after <since>. A starting item edited exactly at <since> does not count.
# Exits 0 when the round is complete:
#   - every --bot has a response, AND
#   - no watched bot has posted or edited anything for 60 seconds.
# Exit 2 after --timeout seconds (default 900), exit 3 when any gh request
# fails. Both print what was seen.
#
# <since> defaults to the current UTC time: start the watch right after the
# push. Each --trigger posts its <comment> first (for bots that review only
# when asked), and <since> becomes the first posted comment's server timestamp.

set -u -o pipefail

USAGE="usage: watch-pr.sh <pr-number> --bot <login> [--bot <login> ...] [--trigger comment ...] [--since iso] [--timeout s]"
PR="${1:?$USAGE}"
shift
SINCE="" TIMEOUT=900
QUIET=60 INTERVAL=30
BOTS=() TRIGGERS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --bot) BOTS+=("${2%\[bot\]}"); shift 2 ;;
    --since) SINCE="$2"; shift 2 ;;
    --trigger) TRIGGERS+=("$2"); shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done
[ "${#BOTS[@]}" -gt 0 ] || { echo "$USAGE" >&2; exit 1; }

REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner) ||
  { echo "ERROR gh could not find the repo. Run from inside the checkout."; exit 3; }
BOTS_JSON=$(printf '%s\n' "${BOTS[@]}" | jq -R . | jq -sc .)

STARTING=$(mktemp) SEEN=$(mktemp)
trap 'rm -f "$STARTING" "$SEEN"' EXIT

# REST logins carry a [bot] suffix; strip it so --bot accepts either form.
# `edited` is updated_at: a bot that edits one summary comment in place
# shows up as activity, as does a bot that posts a new comment each round.
# `key` is url@edited, so an edited item gets a new key.
# The group runs in a subshell, so `exit 1` ends only the group, and
# pipefail makes snapshot fail when any of the three requests fails.
snapshot() {
  {
    gh api "repos/$REPO/issues/$PR/comments" --paginate \
      --jq '.[]|{who:.user.login, at:.created_at, edited:.updated_at, url:.html_url, kind:"summary", body:.body}' || exit 1
    gh api "repos/$REPO/pulls/$PR/comments" --paginate \
      --jq '.[]|{who:.user.login, at:.created_at, edited:.updated_at, url:.html_url, kind:"inline", body:.body}' || exit 1
    gh api "repos/$REPO/pulls/$PR/reviews" --paginate \
      --jq '.[]|select(.submitted_at != null)|{who:.user.login, at:.submitted_at, edited:.submitted_at, url:.html_url, kind:"review", body:.body}'
  } 2>/dev/null | jq -c --argjson bots "$BOTS_JSON" \
    '.who |= sub("\\[bot\\]$"; "") | select(.who as $w | $bots | index($w)) | .key = .url + "@" + .edited'
}

SNAP=$(snapshot) || { echo "ERROR gh query failed for $REPO#$PR"; exit 3; }
printf '%s' "$SNAP" | jq -r .key > "$STARTING"

# Comments post in order, so the first one has the earliest timestamp.
if [ "${#TRIGGERS[@]}" -gt 0 ]; then
  SINCE=""
  for TRIGGER in "${TRIGGERS[@]}"; do
    AT=$(gh api "repos/$REPO/issues/$PR/comments" -f body="$TRIGGER" --jq .created_at) ||
      { echo "ERROR gh could not post \"$TRIGGER\" on $REPO#$PR"; exit 3; }
    echo "TRIGGER posted \"$TRIGGER\" at $AT"
    [ -n "$SINCE" ] || SINCE=$AT
  done
fi
# GitHub timestamps are UTC with a Z suffix, so plain string comparison works.
[ -n "$SINCE" ] || SINCE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

START=$(date +%s)
LAST_EVENT=$START
RESPONDED=" "
while true; do
  if ! SNAP=$(snapshot); then
    echo "ERROR gh query failed for $REPO#$PR"
    exit 3
  fi

  while IFS= read -r item; do
    [ -n "$item" ] || continue
    IFS=$'\t' read -r KEY EDITED WHO <<< "$(printf '%s' "$item" | jq -r '[.key, .edited, .who] | @tsv')"
    grep -qxF "$KEY" "$SEEN" && continue
    if grep -qxF "$KEY" "$STARTING" && [[ ! "$EDITED" > "$SINCE" ]]; then continue; fi
    printf '%s\n' "$KEY" >> "$SEEN"
    LAST_EVENT=$(date +%s)
    RESPONDED="$RESPONDED$WHO "
    printf '%s' "$item" | jq -r \
      '"\(.who) \(.kind) \(.edited) \(.url) :: " + ((.body // "")|gsub("\\s+"; " ")|.[0:200])'
  done <<< "$SNAP"

  WAITING=""
  for BOT in "${BOTS[@]}"; do
    case "$RESPONDED" in *" $BOT "*) ;; *) WAITING="${WAITING:+$WAITING }$BOT" ;; esac
  done
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
