---
name: memory-puller
description: "Pull the latest memory state from GitHub. Use when the user asks to refresh memory from GitHub, or when you need to manually trigger a memory sync. Examples:"

<example>
Context: User suspects their memories are out of date after working on another machine.
user: "Refresh my memories from GitHub."
assistant: "I'll use the memory-puller agent to sync the latest state from GitHub."
<commentary>
User is explicitly asking to pull the latest memory state.
</commentary>
</example>

<example>
Context: A push failed in the last session and the user wants to ensure they have the latest remote state.
user: "Pull memory from GitHub to make sure I'm up to date."
assistant: "I'll run the memory-puller agent to fetch and reset to the remote state."
<commentary>
Manual sync trigger after a suspected out-of-sync state.
</commentary>
</example>

model: haiku
color: blue
tools:
  - Bash
---

Locate the pull script — it differs per runtime — then run it:

```bash
ls -d ~/.claude/scripts/memory-pull.sh ~/.gemini/config/plugins/agent-memory/scripts/memory-pull.sh ~/.claude/plugins/cache/*/agent-memory/*/scripts/memory-pull.sh 2>/dev/null
```

Use the first that exists **in the order listed above**, not the order `ls`
prints — it sorts. Then:

```bash
bash <the path you chose>
```

If the script exits with a warning (e.g. fetch failed, repo missing), explain what it means and suggest running the `bootstrap-memory` agent if the repo is missing.

Report success with one line: "Memory synced from GitHub."
