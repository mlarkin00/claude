---
name: verify-memory-cc
description: This skill should be used when the user asks to check memory health, says memory isn't loading or saving, reports something seems wrong with memory, or when you want to verify the memory system is intact at session start. Runs automated health checks and applies minor self-repairs silently.
---

Run the verify-memory health check script:

```bash
bash ~/.claude/scripts/verify-memory.sh
```

Interpret the output:

- **No output:** All checks passed. Memory system is healthy.
- **`[verify-memory] ⚠ ...` lines:** Structural problem found. Tell the user exactly what was reported, then **offer to run bootstrap yourself** — do not just tell them to run it. If they agree, use the Agent tool to invoke the `bootstrap-memory` subagent with this prompt: `"Bootstrap the agent memory system. The verify-memory check reported these issues: <paste the warning lines>. Work through all 8 steps and report status for each."` Use `subagent_type: "agent-memory:bootstrap-memory"`.
- **Tier 1 fixes applied silently:** The script fixed minor issues (symlink recreation, missing MEMORY.md) without output. No action needed.
- **Git output on stderr but no `[verify-memory] ⚠` lines:** A Tier 1 fix ran and committed/pushed to GitHub. Normal — no user action needed.

After running, confirm whether memory is healthy or what action is needed.
