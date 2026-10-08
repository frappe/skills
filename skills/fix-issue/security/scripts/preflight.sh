#!/usr/bin/env bash
# Put one app checkout on its target branch, fresh from the remote, and cut a fix branch.
#
#   preflight.sh <app-checkout> <target-branch> <fix-branch>
#
#   preflight.sh ~/bench-v15/apps/my_app version-15-hotfix fix/report-permission-check
#
# REMOTE (default: upstream) names the remote that tracks the official repository.
#
# Refuses, and changes nothing, when the checkout has uncommitted files or commits the
# remote does not have: that is someone's work in flight. It does not verify the flaw;
# that is the next step, done by reading the function at the new head.
set -uo pipefail
repo="${1:?usage: preflight.sh <app-checkout> <target-branch> <fix-branch>}"
target="${2:?target branch}"
fix="${3:?fix branch name}"
remote="${REMOTE:-upstream}"

[ -d "$repo/.git" ] || { echo "STOP: no git checkout at $repo" >&2; exit 2; }
dirty=$(git -C "$repo" status --porcelain | wc -l | tr -d ' ')
if [ "$dirty" != "0" ]; then
	echo "STOP: $dirty uncommitted file(s) in $repo. Work is in flight; ask its owner." >&2
	exit 1
fi
git -C "$repo" fetch "$remote" --tags -q || { echo "STOP: fetch from '$remote' failed" >&2; exit 1; }
git -C "$repo" rev-parse -q --verify "${remote}/${target}" >/dev/null ||
	{ echo "STOP: no ${remote}/${target}" >&2; exit 1; }
on=$(git -C "$repo" rev-parse --abbrev-ref HEAD)
ahead=$(git -C "$repo" rev-list --count "${remote}/${target}..HEAD")
if [ "$on" != "$target" ] && [ "$ahead" != "0" ]; then
	echo "STOP: '$on' has $ahead commit(s) not on ${remote}/${target}. Ask its owner before moving it." >&2
	exit 1
fi
git -C "$repo" switch -q -c "$fix" "${remote}/${target}" || exit 1

base=$(git -C "$repo" rev-parse --short HEAD)
echo "on $fix, cut from ${remote}/${target} at $base"
major=$(printf '%s' "$target" | grep -oE '[0-9]+' | head -1)
if [ -n "$major" ]; then
	echo "latest v${major} tag: $(git -C "$repo" tag -l "v${major}.*" | sort -V | tail -1)"
fi
echo "next: re-verify the flaw at this head before writing anything."
