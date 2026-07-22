---
name: verify-memory
description: This skill should be used when the user asks to check memory health, says memory isn't loading or saving, reports something seems wrong with memory, or when you want to verify the memory system is intact at session start. Runs automated health checks and applies minor self-repairs silently.
---

Run the verify-memory health check script:

The script lives in a different place per runtime, so find it first, then run it.

**Step 1 — locate it:**

```bash
ls -d ~/.claude/scripts/verify-memory.sh \
      ~/.gemini/config/plugins/agent-memory/scripts/verify-memory.sh \
      ~/.claude/plugins/cache/*/agent-memory/*/scripts/verify-memory.sh 2>/dev/null
```

**Step 2 — run the first match in this precedence order**, which is *not* the
order `ls` prints (it sorts):

1. `~/.claude/scripts/verify-memory.sh` — the version-free symlink Claude Code's
   `install-symlinks.sh` maintains.
2. `~/.gemini/config/plugins/agent-memory/scripts/verify-memory.sh` — where
   Antigravity installs the plugin.
3. anything under `~/.claude/plugins/cache/` — last resort if the symlink was
   never created; prefer the highest version number.

```bash
bash <the path you chose>
```

If step 1 printed nothing, stop and report that the agent-memory plugin does not
appear to be installed.

Two constraints worth knowing before you "simplify" this: `$CLAUDE_PLUGIN_ROOT`
is set for hooks only and is **empty** in a command you run, and a one-liner
using `$(…)` command substitution gets auto-denied in a headless Antigravity
session — two plain commands are what survive a permission allowlist.

Interpret the output:

- **No output:** All checks passed. Memory system is healthy.
- **`[verify-memory] ⚠ ...` lines:** Structural problem found. Tell the user exactly what was reported, then **offer to run bootstrap yourself** — do not just tell them to run it. If they agree, use the Agent tool to invoke the `bootstrap-memory` subagent with this prompt: `"Bootstrap the agent memory system. The verify-memory check reported these issues: <paste the warning lines>. Work through all 8 steps and report status for each."` Use `subagent_type: "agent-memory:bootstrap-memory"`. **Antigravity has no plugin subagents** — if that agent is not available to you, do not report failure: read `agents/bootstrap-memory.md` from the plugin directory alongside this skill and work through its steps yourself.
- **Tier 1 fixes applied silently:** The script fixed minor issues (symlink recreation, missing MEMORY.md) without output. No action needed.
- **Git output on stderr but no `[verify-memory] ⚠` lines:** A Tier 1 fix ran and committed/pushed to GitHub. Normal — no user action needed.

After running, confirm whether memory is healthy or what action is needed.
