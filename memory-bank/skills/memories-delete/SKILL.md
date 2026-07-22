---
name: memories-delete
description: Delete a specific memory by ID from the GCP Memory Bank. Use when the user explicitly asks to remove a memory. Always confirm the ID by listing first if uncertain.
---

Delete a memory from the GCP Memory Bank.

## Steps

1. If the memory ID is not provided, run `/memories-list` first to find it.
2. Confirm with the user: "Delete memory `<id>`: `<fact[:60]>…`?" — then proceed.
3. Locate the scripts directory — it differs per runtime:
   ```bash
   ls -d ~/.claude/scripts/memory-bank ~/.gemini/config/plugins/memory-bank/scripts ~/.claude/plugins/cache/*/memory-bank/*/scripts 2>/dev/null
   ```
   Use the first that exists **in the order listed above**, not the order `ls`
   prints — it sorts. Call it `<SCRIPTS>`.
4. Run:
   ```bash
   python3 <SCRIPTS>/delete_memory.py "<memory_id>"
   ```
5. Confirm: `✓ Deleted memory <id>`

## Rules

- Always confirm before deleting — deletion is irreversible.
- Never guess a memory ID — list first if uncertain.
