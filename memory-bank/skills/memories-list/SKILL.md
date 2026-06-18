---
name: memories-list
description: List memories stored in the GCP Reasoning Engine Memory Bank. Use when the user wants to see what's in their memory bank, filter by scope, or look up a memory ID before updating or deleting.
---

List memories from the GCP Memory Bank.

## Steps

1. Run:
   ```bash
   python3 ~/.claude/scripts/memory-bank/list_memories.py [--scope current|all]
   ```
   Default: `--scope current` (shows global + project memories for the current workspace).
2. Format the output as a Markdown table: `| # | ID | Scope | Fact |`

## Rules

- Use `--scope all` only if the user explicitly asks to see all memories regardless of project.
- Truncate the Fact column at 80 characters in the table; offer to show full text on request.
