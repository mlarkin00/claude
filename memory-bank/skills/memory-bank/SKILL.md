---
name: memory-bank
description: Use this skill when the user says "save this to memory bank", "remember this permanently", "add to GCP memory", or explicitly asks to persist a high-priority fact to the long-term GCP Memory Bank. Saves a fact immediately at global scope (default) or project scope if requested.
---

Save the fact to the GCP Memory Bank immediately. Do NOT ask for confirmation — the invocation is the permission.

## Steps

1. Determine scope: `global` (default) unless the user explicitly says "project memory" or "project scope".
2. Locate the scripts directory — it differs per runtime:
   ```bash
   ls -d ~/.claude/scripts/memory-bank ~/.gemini/config/plugins/memory-bank/scripts ~/.claude/plugins/cache/*/memory-bank/*/scripts 2>/dev/null
   ```
   Use the first that exists **in the order listed above**, not the order `ls`
   prints — it sorts. Call it `<SCRIPTS>`.
3. Run:
   ```bash
   python3 <SCRIPTS>/add_memory.py "<fact>" --scope <global|project>
   ```
4. Confirm with one line: `✓ Saved to Memory Bank: <fact[:60]>… (<scope>)`

## Rules

- Default scope is ALWAYS `global`.
- Only use `project` if the user explicitly requests project-level memory.
- Do not re-print the full fact — keep the confirmation to one line.
