#!/bin/bash
# Publishes a built canvas as an artifact owned by the Claude account in PUBLISH_CONFIG_DIR
# (default ~/.claude: the account the reviewer's browser is signed in to), through a headless claude -p.
#
#   publish.sh <build dir> [artifact url]
#
# The build dir is what canvas/build.mjs wrote: canvas.html, files.json and the screenshots.
# Pass the url to update an existing artifact in place. Prints the artifact url.
set -euo pipefail

BUILD_DIR=$(cd "${1:?build dir}" && pwd)
URL=${2:-}
CONFIG_DIR=${PUBLISH_CONFIG_DIR:-$HOME/.claude}
CLAUDE_BIN=${CLAUDE_CODE_EXECPATH:-$(command -v claude)}

FILES=$(python3 -c "import json;print(json.dumps(json.load(open('$BUILD_DIR/files.json'))))")
URL_PART=""
[ -n "$URL" ] && URL_PART="First call Artifact with action 'read' on url '$URL'. Then publish with url '$URL', "

PROMPT="Publish $BUILD_DIR/canvas.html as an Artifact. ${URL_PART}Call Artifact publish exactly once with: file_path '$BUILD_DIR/canvas.html', root '$BUILD_DIR', icon 'map', capabilities {\"db\": {}, \"user\": {\"scopes\": [\"profile\"]}}, description 'Every captured screen state, laid out as a tree per flow, with pinned review comments and a copy-prompt button.', and files = $FILES. Do not edit the file and do not open it. Reply with only the published URL on its own line."

cd "$BUILD_DIR"
printf %s "$PROMPT" | CLAUDE_CONFIG_DIR="$CONFIG_DIR" "$CLAUDE_BIN" -p --permission-mode bypassPermissions --allowedTools "Artifact,Read" 2>/dev/null | grep -o 'https://claude.ai/artifact/[A-Za-z0-9]*' | tail -1
