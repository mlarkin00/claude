---
name: memories-update
description: Update the fact content of an existing memory in the GCP Memory Bank by ID. Use when the user wants to correct or refine an existing memory. Usually preceded by a memories-list to find the ID.
---

Update an existing memory's fact content.

## Steps

1. If the memory ID is not provided, run `/memories-list` first to find it.
2. Locate the scripts directory — it differs per runtime:
   ```bash
   ls -d ~/.claude/scripts/memory-bank ~/.gemini/config/plugins/memory-bank/scripts ~/.claude/plugins/cache/*/memory-bank/*/scripts 2>/dev/null
   ```
   Use the first that exists **in the order listed above**, not the order `ls`
   prints — it sorts. Call it `<SCRIPTS>`.
3. Run:
   ```bash
   python3 <SCRIPTS>/update_memory.py "<memory_id>" "<new_fact>"
   ```
4. Confirm: `✓ Updated memory <id>`

## Rules

- Never guess a memory ID — always list first if uncertain.
