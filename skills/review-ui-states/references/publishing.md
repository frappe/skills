# Publishing from another account

The canvas must belong to the Claude account the reviewer uses on claude.ai, because an artifact is private to the account that publishes it. Use this page when the session cannot publish there with its own Artifact tool.

## The session runs on a different account

A session whose `CLAUDE_CONFIG_DIR` points at a second account publishes to that account, where the reviewer cannot see it. Run the scripts instead; each starts a headless `claude -p` with `CLAUDE_CONFIG_DIR` set to `PUBLISH_CONFIG_DIR` (default `~/.claude`):

- `scripts/publish.sh <build dir> [url]` publishes the build and prints the url. Pass the url on every later publish so the link stays the same.
- `scripts/comments.sh <url>` prints every comment as JSON.
- `scripts/mark-done.sh <url> <ids…>` marks comments done and prints the ids it updated.

## The session has no Artifact tool

Some Agent SDK hosts leave the Artifact tool out, and `claude -p` lacks it too, but an interactive `claude` has it. Start one in a tmux session in the build dir with the publish prompt as its argument, with the parent's `CLAUDE*` environment variables unset (`CLAUDECODE`, `CLAUDE_CODE_CHILD_SESSION` and the others make it report "Not logged in"). Confirm the folder-trust prompt, then read the url from `tmux capture-pane`.
