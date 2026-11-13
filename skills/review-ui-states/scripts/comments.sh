#!/bin/bash
# Prints the canvas comments as JSON, reading the artifact as the account in PUBLISH_CONFIG_DIR
# (default ~/.claude). Use it when the session itself runs on another account.
#
#   comments.sh <artifact url>
set -euo pipefail

URL=${1:?artifact url}
CONFIG_DIR=${PUBLISH_CONFIG_DIR:-$HOME/.claude}
CLAUDE_BIN=${CLAUDE_CODE_EXECPATH:-$(command -v claude)}

PROMPT="Call ArtifactData with action 'list', collection 'comments', url '$URL', query {\"limit\": 1000}. Reply with only a JSON array of every document, each with id, version, flow, state, x, y, text, done, at, kind, related, parent. No prose, no code fence."

printf %s "$PROMPT" | CLAUDE_CONFIG_DIR="$CONFIG_DIR" "$CLAUDE_BIN" -p --permission-mode bypassPermissions --allowedTools "ArtifactData" 2>/dev/null | sed -n '/^\[/,$p'
