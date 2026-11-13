# Publishing without the Artifact tool

Some Agent SDK hosts leave the Artifact tool out, and `claude -p` lacks it too, but an interactive `claude` has it. Start one in a tmux session in the build dir with the publish prompt as its argument, with the parent's `CLAUDE*` environment variables unset (`CLAUDECODE`, `CLAUDE_CODE_CHILD_SESSION` and the others make it report "Not logged in"). Confirm the folder-trust prompt, then read the url from `tmux capture-pane`.

Run it as the account the reviewer uses on claude.ai, since the artifact is private to the account that publishes it. Reading and marking comments needs ArtifactData, which has the same limits, so do that from the same interactive session.
