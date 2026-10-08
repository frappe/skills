#!/usr/bin/env bash
# Propose the release lines of a Frappe app: the branches a security fix must reach.
#
#   release_lines.sh <app-checkout> [max-age-days]      (default 120)
#
# REMOTE (default: upstream) names the remote that tracks the official repository.
#
# For every development or release branch on the remote it prints: last commit date, the
# frappe range from [tool.bench.frappe-dependencies], the newest release tag on that line, and
# a verdict. A branch is a CANDIDATE when it is a development branch (develop, main,
# master) or a release branch, and has commits within max-age-days.
#
# Where an app keeps both `version-N` and `version-N-hotfix`, PRs go to the hotfix branch and
# releases are cut from it into `version-N`; the hotfix branch is the fix target.
#
# This proposes; a human confirms. Which lines a project still supports is a policy, and an
# active branch is evidence of it, not proof.
set -uo pipefail
repo="${1:?usage: release_lines.sh <app-checkout> [max-age-days]}"
max_age="${2:-120}"
remote="${REMOTE:-upstream}"
[ -d "$repo/.git" ] || { echo "no git checkout at $repo" >&2; exit 2; }
git -C "$repo" fetch "$remote" --tags -q 2>/dev/null || echo "WARN: fetch from '$remote' failed" >&2

now=$(date +%s)
printf '%-28s %-11s %-30s %-16s %s\n' BRANCH LAST-COMMIT FRAPPE NEWEST-TAG VERDICT
git -C "$repo" for-each-ref --format='%(refname:short)' "refs/remotes/${remote}" |
	grep -E "^${remote}/(develop|main|master|version-[0-9]+(-hotfix)?|v[0-9]+(\.x)*(-hotfix)?)$" |
	while IFS= read -r ref; do
		branch="${ref#"${remote}"/}"
		ts=$(git -C "$repo" log -1 --format=%ct "$ref")
		day=$(git -C "$repo" log -1 --format=%cs "$ref")
		age=$(( (now - ts) / 86400 ))
		frappe=$(git -C "$repo" show "${ref}:pyproject.toml" 2>/dev/null |
			awk '/^\[tool\.bench\.frappe-dependencies\]/{f=1;next} /^\[/{f=0} f && /frappe/{sub(/^[^=]*= */,""); print; exit}')
		# Release tags are cut on the release branch, so a hotfix line reports its partner's tag.
		tagref="$ref"
		case "$branch" in
			*-hotfix) git -C "$repo" rev-parse -q --verify "${ref%-hotfix}" >/dev/null && tagref="${ref%-hotfix}" ;;
		esac
		tag=$(git -C "$repo" tag --merged "$tagref" --sort=-v:refname 2>/dev/null | head -1)
		verdict="stale (${age}d)"
		if [ "$age" -le "$max_age" ]; then
			case "$branch" in
				develop|main|master) verdict="CANDIDATE: development" ;;
				*-hotfix) verdict="CANDIDATE: release line, fix target" ;;
				*)
					if git -C "$repo" rev-parse -q --verify "${ref}-hotfix" >/dev/null; then
						verdict="release branch (fix goes to ${branch}-hotfix)"
					else
						verdict="CANDIDATE: release line"
					fi ;;
			esac
		fi
		printf '%-28s %-11s %-30s %-16s %s\n' "$branch" "$day" "${frappe:--}" "${tag:--}" "$verdict"
	done
