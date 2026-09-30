# A10 — Realtime / SocketIO authorization

**Scope:** socket event handlers, room joins, and server-side `publish_realtime` calls.

**Why:** realtime events fan out to subscribers through a path with weaker checks than the HTTP
one.

## Find
- `rg -n "publish_realtime|publish_progress" --type py` — check the `room`, `doctype`,
  `docname`, `user`, and `after_commit` arguments. A call with no room scoping broadcasts to
  everyone.
- Socket handlers in `realtime/` and app JS: every `socket.on(...)` that joins a room.
  Does joining verify permission on the referenced document?
- Guest connections: can an unauthenticated socket claim a `user` identity?
- Event payload contents — a "document updated" event that carries the document body leaks
  regardless of room correctness.

## Confirm
- Room name derived from client input without a permission check is the core bug.
- Note nginx CORS config only as context; the fix belongs in the deployment, not the app.

## Report
Per handler: room, who can join, what is broadcast.
