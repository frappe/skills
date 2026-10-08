#!/usr/bin/env bash
# Is each branch's bench free to take a fix? Read-only: fetches, never checks out.
#
#   bench_status.sh <app> <branch>=<bench-path> [<branch>=<bench-path> ...]
#
#   bench_status.sh my_app develop=~/bench-dev version-15-hotfix=~/bench-v15
#   bench_status.sh my_app main=~/bench-main
#
# REMOTE (default: upstream) names the remote that tracks the official repository.
#
# A bench is READY only when its app checkout is on the target branch, clean, and not
# ahead of the remote. Anything else means work is in flight there: ask whoever owns it,
# do not reuse it.
set -uo pipefail
app="${1:?usage: bench_status.sh <app> <branch>=<bench-path> ...}"; shift
remote="${REMOTE:-upstream}"
[ $# -gt 0 ] || { echo "give at least one <branch>=<bench-path>" >&2; exit 2; }

status=0
for pair in "$@"; do
	target="${pair%%=*}"
	root="${pair#*=}"
	root="${root/#\~/$HOME}"
	repo="$root/apps/$app"
	printf '=== %-20s %s\n' "$target" "$repo"
	if [ ! -d "$repo/.git" ]; then
		echo "    MISSING  no $app checkout"
		status=1
		continue
	fi
	git -C "$repo" fetch "$remote" --tags -q 2>/dev/null || echo "    WARN     fetch from '$remote' failed"
	on=$(git -C "$repo" rev-parse --abbrev-ref HEAD)
	dirty=$(git -C "$repo" status --porcelain | wc -l | tr -d ' ')
	ahead=$(git -C "$repo" rev-list --count "${remote}/${target}..HEAD" 2>/dev/null || echo "?")
	behind=$(git -C "$repo" rev-list --count "HEAD..${remote}/${target}" 2>/dev/null || echo "?")
	fw=$(git -C "$root/apps/frappe" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "-")
	printf '    %-8s %s at %s\n' "$app" "$on" "$(git -C "$repo" rev-parse --short HEAD)"
	printf '    frappe   %s\n' "$fw"
	printf '    drift    behind %s, ahead %s of %s/%s\n' "$behind" "$ahead" "$remote" "$target"
	verdict="READY"
	if [ "$on" != "$target" ]; then verdict="BUSY: parked on '$on'"; fi
	if [ "$dirty" != "0" ]; then verdict="BUSY: $dirty uncommitted file(s)"; fi
	if [ "$ahead" != "0" ] && [ "$ahead" != "?" ]; then verdict="BUSY: $ahead unpushed commit(s)"; fi
	if [ "$ahead" = "?" ]; then verdict="UNKNOWN: no ${remote}/${target}"; fi
	[ "$verdict" = "READY" ] || status=1
	printf '    verdict  %s\n' "$verdict"
done
exit "$status"
