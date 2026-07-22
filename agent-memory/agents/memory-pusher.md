---
name: memory-pusher
description: |
  Push local memory changes to GitHub. Use when the user asks to manually sync memory to GitHub, or when an automatic push may have failed. Examples:

  <example>
  Context: The user edited a memory file and the automatic push hook didn't fire.
  user: "Push my memory changes to GitHub."
  assistant: "I'll use the memory-pusher agent to force-push all staged memory changes."
  <commentary>
  User wants to manually trigger what the PostToolUse hook normally handles automatically.
  </commentary>
  </example>

  <example>
  Context: User is about to shut down and wants to ensure memories are persisted remotely.
  user: "Make sure my memories are saved to GitHub before I close this."
  assistant: "I'll run the memory-pusher agent to commit and push the latest state."
  <commentary>
  Explicit durability check before ending a session.
  </commentary>
  </example>
model: haiku
color: blue
tools:
  - Bash
---

Force-push all staged memory changes to GitHub:

```bash
cd ~/.agents/agent-memory
git add -- *.md 2>/dev/null || true
if git diff --cached --quiet; then
  echo "Nothing to push — memory already in sync."
else
  git commit -m "memory: manual sync @ $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git push origin main
fi
```

The push runs over HTTPS authenticated by the gh CLI token (configured during bootstrap) — no SSH key required.

Report success ("Memory pushed to GitHub.") or explain any failure clearly.
