#!/bin/bash
# Marks canvas comments done, writing as the account in PUBLISH_CONFIG_DIR (default ~/.claude).
#
#   mark-done.sh <artifact url> <comment id> [<comment id>…]
#
# Read the ids with comments.sh first. Prints the ids the update touched.
set -euo pipefail

URL=${1:?artifact url}; shift
[ $# -gt 0 ] || { echo "no comment ids" >&2; exit 2; }
CONFIG_DIR=${PUBLISH_CONFIG_DIR:-$HOME/.claude}
CLAUDE_BIN=${CLAUDE_CODE_EXECPATH:-$(command -v claude)}

IDS=$(printf '"%s",' "$@"); IDS="[${IDS%,}]"
PROMPT="Call ArtifactData once with action 'batch', url '$URL', and one 'update' operation per id in $IDS on collection 'comments' setting data {\"done\": true}. Then reply with only a JSON array of the ids that were updated. No prose, no code fence."

printf %s "$PROMPT" | CLAUDE_CONFIG_DIR="$CONFIG_DIR" "$CLAUDE_BIN" -p --permission-mode bypassPermissions --allowedTools "ArtifactData" 2>/dev/null | sed -n '/^\[/,$p'
