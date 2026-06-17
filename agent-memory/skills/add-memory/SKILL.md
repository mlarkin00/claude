---
name: add-memory-cc
description: Use when the user invokes `/add-memory-cc`, says "remember that …", "save this to memory", "add to long-term memory", or otherwise explicitly asks for information to be persisted across sessions. Saves the memory immediately without asking for confirmation or clarifying questions — classifies the type, writes the file, and updates the MEMORY.md index in one shot.
---

Save the memory details provided by the user **immediately**. Do NOT ask for confirmation, clarification, or the user's permission — the invocation itself is the permission.

Memory directory: `~/.claude/memory/` (symlink managed by the agent-memory plugin; writes here are committed and pushed to GitHub automatically by the PostToolUse hook).

## Steps

### 1. Classify the memory

Pick the type that best fits the content:

| Type        | Use for                                                                                |
| ----------- | -------------------------------------------------------------------------------------- |
| `user`      | Facts about the user: role, preferences, responsibilities, domain knowledge            |
| `feedback`  | How to approach work: rules to follow, things to avoid, validated approaches to repeat |
| `project`   | Initiative/bug/incident state: who's doing what, why, deadlines, motivations           |
| `reference` | Pointers to external systems: Linear projects, Slack channels, dashboards, docs        |

If the user explicitly named a type in the invocation, use that. Otherwise infer from the content.

### 2. Check for duplicates

Read `~/.claude/memory/MEMORY.md`. If an existing entry covers the same topic, **update that file** rather than creating a new one (read the existing file with the Read tool first, then use Edit). Only create a new file when no existing memory covers the topic.

### 3. Pick a slug

Format: `<type>_<short_topic>.md` — lowercase, underscores, no spaces. Keep it short and semantic.

Examples: `user_role_data_scientist.md`, `feedback_no_db_mocks.md`, `project_auth_rewrite.md`, `reference_ingest_linear.md`.

### 4. Write the memory file

Write `~/.claude/memory/<slug>.md` with this structure:

```markdown
---
name: <short title — human-readable, 3–8 words>
description: <one-line — specific enough that future-you can judge relevance>
type: <user|feedback|project|reference>
---

<body>
```

For `feedback` and `project` types, structure the body as:

```
<the rule or fact — one crisp sentence>

**Why:** <reason, constraint, or incident that motivated it>

**How to apply:** <when/where this kicks in; edge cases>
```

For `user` and `reference` types, one or two sentences of prose is fine — no Why/How-to-apply required.

Convert relative dates in the user's message ("tomorrow", "next week", "Thursday") to absolute ISO dates (`2026-04-23`) so the memory stays interpretable later.

### 5. Update MEMORY.md

Append a single-line index entry to `~/.claude/memory/MEMORY.md`:

```
- [<short title>](<slug>.md) — <one-line hook, <120 chars>
```

Keep the hook specific and action-oriented — the index is always in context, so each line must pay its weight.

If you **updated** an existing file in step 2, also update its MEMORY.md line if the title or hook changed.

### 6. Confirm

Print one line to the user:

```
✓ Saved memory: <slug>.md (<type>)
```

Do not re-print the memory body, do not explain what you did — the checkmark is the confirmation.

## Rules

- **No questions asked.** Never respond with "should I…?" or "can you clarify…?" — infer from the provided details and save.
- **No duplicate files.** Always check MEMORY.md first; prefer updating an existing entry.
- **Never save to `~/.claude/projects/.../memory/`** — that's a per-project path the plugin does not sync. Always use `~/.claude/memory/`.
- **Don't include this task's conversation context** in the memory body (e.g., "user asked me to save this on 2026-04-21"). Save the durable fact, not the meta.
- **The PostToolUse hook handles git.** Do not manually `git add`, commit, or push — writing the file is enough; the memory-push hook commits and pushes automatically.
