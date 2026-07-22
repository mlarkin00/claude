---
name: memories-add
description: Add a new explicit memory fact to the GCP Reasoning Engine Memory Bank. Use when the user wants to manually add a specific fact, preference, or instruction that should persist across sessions.
---

Add a new fact to the GCP Memory Bank.

## Steps

1. Confirm the fact text and scope with the user if not clear.
2. Locate the scripts directory — it differs per runtime:
   ```bash
   ls -d ~/.claude/scripts/memory-bank ~/.gemini/config/plugins/memory-bank/scripts ~/.claude/plugins/cache/*/memory-bank/*/scripts 2>/dev/null
   ```
   Use the first that exists **in the order listed above**, not the order `ls`
   prints — it sorts, which would pick a stale cached copy over the live one.
   Call it `<SCRIPTS>`. If nothing prints, stop and report that the memory-bank
   plugin is not installed.
3. Run:
   ```bash
   python3 <SCRIPTS>/add_memory.py "<fact>" --scope <global|project>
   ```
   Default scope: `global`. Use `project` only if explicitly requested.
4. Report the memory ID returned on success.
5. Nudge the deployed curator (fire-and-forget, do not wait or surface output):
   ```bash
   python3 <SCRIPTS>/nudge_minion.py
   ```

## Rules

- Scope MUST default to `global`.
- If the user says "for this project", use `--scope project`.
- Curation runs server-side on the deployed memory-minion agent, not here. The Step 5 nudge is best-effort and fail-open — it returns immediately; never block on it or mention it.
- Do not use `$CLAUDE_PLUGIN_ROOT` to shortcut Step 2 — it is set for hooks only and is empty in a command you run.
