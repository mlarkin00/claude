---
name: memories-delete
description: Delete a specific memory by ID from the GCP Memory Bank. Use when the user explicitly asks to remove a memory. Always confirm the ID by listing first if uncertain.
---

Delete a memory from the GCP Memory Bank.

## Steps

1. If the memory ID is not provided, run `/memories-list` first to find it.
2. Confirm with the user: "Delete memory `<id>`: `<fact[:60]>…`?" — then proceed.
3. Run:
   ```bash
   python3 ~/.claude/scripts/memory-bank/delete_memory.py "<memory_id>"
   ```
4. Confirm: `✓ Deleted memory <id>`

## Rules

- Always confirm before deleting — deletion is irreversible.
- Never guess a memory ID — list first if uncertain.
