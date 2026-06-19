# Memories Curate Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use agent-workflow:subagent-driven-development (recommended) or agent-workflow:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a curator subagent that silently deduplicates and rewrites all memories for agent-readability after every `memories-add` invocation.

**Architecture:** A new agent definition (`agents/memories-curate.md`) encodes all dedup and rewrite rules. The `memories-add` skill spawns it silently via the `Agent` tool after adding. A thin standalone skill (`skills/memories-curate/SKILL.md`) surfaces the same agent with a user-facing summary for on-demand invocation.

**Tech Stack:** Claude Code agent definitions (markdown frontmatter), SKILL.md, `list_memories.py`, `update_memory.py`, `delete_memory.py` (all existing scripts)

---

## File Map

| Action | Path |
|--------|------|
| Create | `agents/memories-curate.md` |
| Create | `skills/memories-curate/SKILL.md` |
| Modify | `skills/memories-add/SKILL.md` |

---

## Task 1: Create the curator agent definition

**Files:**
- Create: `agents/memories-curate.md`

No unit tests apply — this is an agent definition file, not Python code. Verification is behavioral (Task 3).

- [ ] **Step 1: Create `agents/memories-curate.md`**

```markdown
---
name: memories-curate
description: "Silently deduplicates and rewrites all GCP Memory Bank facts for the current user. Runs after memories-add. Applies scope-priority dedup rules (global wins) and rewrites facts for agent-readability."
model: sonnet
tools:
  - Bash
---

You are curating the GCP Memory Bank. Work silently — produce no user-facing output during the run. Return only the final JSON summary.

## Step 1 — Identify current user

```bash
python3 ~/.claude/scripts/memory-bank/list_memories.py --scope current 2>&1 | head -1
```

Parse the 8-character user hash suffix from the output line:
`Memories for current scope (user …XXXXXXXX, project …YYYYYYYY or global):`

Save as `USER_SUFFIX`.

## Step 2 — List all memories

```bash
python3 ~/.claude/scripts/memory-bank/list_memories.py --scope all
```

Parse each memory block. Each block has the form:
```
[N] ID: <memory_id>
    Created:  <timestamp>
    Scope:    user=…<8chars>  project=…<8chars>
    Fact:     <fact text>
```

Filter to only memories where `user=…<8chars>` matches `USER_SUFFIX`. Discard all others — never modify memories belonging to other users.

## Step 3 — Group by scope

From the filtered memories, build two groups:

- **global**: memories where the project field suffix is `"global"` (i.e. `project=…lobalXXX` — the last 8 chars of the string `"global"`)
- **per_project**: a dict keyed by the full 8-char project suffix, containing arrays of memories

To reliably identify global memories: the `project` scope value is literally the string `"global"`. The display shows `project=…<last 8 chars>`. Cross-check: global memories will have the same last-8-chars suffix across all users.

Simpler approach: run `list_memories.py --scope current` and note the `project=…YYYYYYYY` suffix shown in the header — that is the current project hash suffix. Any memory NOT matching that suffix AND not matching the global suffix is from a different project.

## Step 4 — Deduplicate

Apply these rules in order. "Same fact" means semantically equivalent content — same preference, rule, or constraint, even if worded differently. Related-but-distinct facts are NOT duplicates.

**Rule 1 — Global vs. global:** If two global memories express the same fact, delete the less complete/clear one. Keep one.

**Rule 2 — Project vs. global:** If a project-scoped memory (any project) is fully covered by a global memory, delete the project-scoped one. Global wins.

**Rule 3 — Same-project vs. same-project:** If two memories in the same project scope express the same fact, delete the less complete/clear one. Keep one.

**Rule 4 — Cross-project:** If memories in different project scopes express the same fact, leave both — they are never co-loaded and are not duplicates.

To delete a memory:
```bash
python3 ~/.claude/scripts/memory-bank/delete_memory.py "<memory_id>"
```

## Step 5 — Rewrite for agent-readability

For each surviving memory, evaluate its fact text:

**Rewriting principles (in priority order):**
1. Use imperative/instructional voice: `"Always respond under 3 sentences"` not `"User prefers short responses"`.
2. Remove filler words, hedging (`"might"`, `"usually"`, `"kind of"`), and vague qualifiers.
3. Never lose semantic content — if tightening would lose nuance, leave the fact unchanged.
4. Only update if the rewrite is substantively different from the original. Skip trivial rewording.

To update a memory:
```bash
python3 ~/.claude/scripts/memory-bank/update_memory.py "<memory_id>" "<new_fact_text>"
```

## Step 6 — Return summary

Return exactly this JSON (no other output):
```json
{"reviewed": N, "updated": N, "deleted": N}
```

Where N is the count of memories reviewed, updated (rewritten), and deleted (duplicates removed).

## Error handling

- If Step 1 or Step 2 fails (bash error or empty output): stop immediately, return `{"reviewed": 0, "updated": 0, "deleted": 0}`.
- If any individual `update_memory.py` or `delete_memory.py` call fails: log the error to stderr, continue with remaining memories.
- Never let a failure block progress on other memories.
```

- [ ] **Step 2: Commit**

```bash
git add agents/memories-curate.md
git commit -m "feat: add memories-curate agent definition"
```

---

## Task 2: Create the standalone skill

**Files:**
- Create: `skills/memories-curate/SKILL.md`

- [ ] **Step 1: Create the skill directory and file**

```bash
mkdir -p skills/memories-curate
```

Contents of `skills/memories-curate/SKILL.md`:

```markdown
---
name: memories-curate
description: Curate all GCP Memory Bank memories for the current user — deduplicates and rewrites facts for agent-readability. Safe to run at any time; changes are applied silently and a summary is reported.
---

Curate all memories in the GCP Memory Bank.

## Steps

1. Use the Agent tool with subagent_type `memory-bank:memories-curate`.
2. When the agent returns its JSON summary, report to the user:
   "Curated {reviewed} memories: {updated} rewritten, {deleted} duplicates removed."

## Rules

- Always surface the summary — this skill is invoked explicitly by the user.
- If the agent returns an error or empty result, report: "Curation completed with no changes."
```

- [ ] **Step 2: Commit**

```bash
git add skills/memories-curate/SKILL.md
git commit -m "feat: add memories-curate standalone skill"
```

---

## Task 3: Update `memories-add` to spawn the curator

**Files:**
- Modify: `skills/memories-add/SKILL.md`

Current content:
```markdown
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

## Rules

- Scope MUST default to `global`.
- If the user says "for this project", use `--scope project`.
```

- [ ] **Step 1: Append the curator step to `skills/memories-add/SKILL.md`**

Replace the file content with:

```markdown
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
4. Silently spawn the curator: use the Agent tool with subagent_type `memory-bank:memories-curate`. Do NOT await its result or surface any output to the user.

## Rules

- Scope MUST default to `global`.
- If the user says "for this project", use `--scope project`.
- The curator in Step 4 runs in the background — do not block the user or mention it.
```

- [ ] **Step 2: Verify the diff looks correct**

```bash
git diff skills/memories-add/SKILL.md
```

Expected: Step 4 and its rule added, nothing else changed.

- [ ] **Step 3: Commit**

```bash
git add skills/memories-add/SKILL.md
git commit -m "feat: spawn memories-curate agent after every memories-add"
```

---

## Task 4: Behavioral verification

No automated tests apply to agent/skill definitions. Verify manually.

- [ ] **Step 1: Confirm the agent is registered**

Start a new Claude Code session and run:
```
What agent types are available from the memory-bank plugin?
```

Expected: `memory-bank:memories-curate` appears in the list alongside `memory-bank:bootstrap-memory-bank`.

- [ ] **Step 2: Test standalone skill**

```
/memories-curate
```

Expected output (values will vary):
```
Curated 12 memories: 2 rewritten, 1 duplicate removed.
```

Or if no changes needed:
```
Curation completed with no changes.
```

- [ ] **Step 3: Test automatic trigger via memories-add**

```
/memories-add "Always use Python 3 stdlib only — no pip installs" --scope global
```

Expected: Claude reports the memory ID, then no further visible output. The curator runs silently in the background.

- [ ] **Step 4: Confirm curator ran by checking memory count**

```
/memories-list
```

Verify there are no obvious duplicates of the just-added fact and that existing facts are written in imperative voice.
