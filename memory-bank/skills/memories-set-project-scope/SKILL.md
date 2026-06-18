---
name: memories-set-project-scope
description: Re-scope an existing global memory to the current project in the GCP Memory Bank. Use when a memory that was saved globally should be narrowed to only apply to the current workspace.
---

Re-scope a global memory to the current project.

## Steps

1. If the memory ID is not provided, run `/memories-list` first to find it.
2. Run:
   ```bash
   python3 ~/.claude/scripts/memory-bank/set_project_scope.py "<memory_id>"
   ```
   This fetches the fact, creates a project-scoped copy, and deletes the global original.
3. Confirm: `✓ Re-scoped: <old_id> → <new_id> (project scope)`

## Rules

- This operation changes the memory's ID — the old ID will no longer exist.
- Only re-scope if the user explicitly requests project-level narrowing.
