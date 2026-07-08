---
name: memories-add
description: Add a new explicit memory fact to the GCP Reasoning Engine Memory Bank. Use when the user wants to manually add a specific fact, preference, or instruction that should persist across sessions.
---

Add a new fact to the GCP Memory Bank.

## Steps

1. Confirm the fact text and scope with the user if not clear.
2. Run:
   ```bash
   python3 ~/.claude/scripts/memory-bank/add_memory.py "<fact>" --scope <global|project>
   ```
   Default scope: `global`. Use `project` only if explicitly requested.
3. Report the memory ID returned on success.
4. Nudge the deployed curator (fire-and-forget, do not wait or surface output):
   ```bash
   python3 ~/.claude/scripts/memory-bank/nudge_minion.py
   ```

## Rules

- Scope MUST default to `global`.
- If the user says "for this project", use `--scope project`.
- Curation runs server-side on the deployed memory-minion agent, not here. The Step 4 nudge is best-effort and fail-open — it returns immediately; never block on it or mention it.
