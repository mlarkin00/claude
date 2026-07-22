---
name: managing-agent-instructions
description: Use when the user asks to "write a doc", "create agent instructions", "update AGENTS.md", "sync context files", "refine project rules", "update the TODO", "add a task to the backlog", "update DESIGN.md", or "record a lesson learned". Use this skill to manage persistent, high-signal project-specific context in AGENTS.md, GEMINI.md, CLAUDE.md, the project task backlog in .agents/TODO.md, the design system specification in DESIGN.md, and the runtime-evidence knowledge bundle in .agents/wiki/.
---

# Managing Agent Instructions

This skill manages the lifecycle of agent-facing documentation:

- **Briefing files** — `AGENTS.md`, `GEMINI.md`, `CLAUDE.md` at project root: what the agent needs to act correctly on day one (commands, conventions, constraints).
- **Design system** — `DESIGN.md` at project root: machine-readable design tokens (colors, typography, spacing, components) plus human-readable rationale, in the [google/design.md](https://github.com/google-labs-code/design.md) format. Only relevant for projects with a visual UI.
- **Architecture snapshot** — `ARCH.md` (or `docs/designs/ARCH.md`) at project root: the current, load-bearing system design (component maps, data flows, invariants) an agent should reason from.
- **Task backlog** — `<project_root>/.agents/TODO.md`: pending work a future session should pick up.
- **Knowledge bundle** — `<project_root>/.agents/wiki/`: the runtime-evidence store. An OKF v0.1 bundle, one concept per fact, `@`-imported by the briefing file. Holds the non-obvious findings behind the rules — how each was established and against which version. Supersedes the flat `.agents/INSIGHTS.md`. See `references/knowledge-bundle.md`.

## Core Mandates

- **Minimalism**: Keep briefing files (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`) under 100 lines. `DESIGN.md` may be longer but MUST stay under ~300 lines — split detail into `docs/designs/` if it grows past that. Strip introductory filler, paragraphs, and pleasantries. See `references/content-guidelines.md`.
- **Target Audience**: Only `README.md` and `ARCH.md` should be structured for human understanding (using narrative flow and conceptual descriptions). Briefing files (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`) and backlogs (`.agents/TODO.md`) MUST be structured for optimal machine understanding and token efficiency (highly-dense checklist formats, raw command lines, zero prose or filler).
- **Reference, Don't Embed**: Point to existing configuration files (e.g., `.eslintrc.json`, `tsconfig.json`, `Makefile`). Never duplicate rules defined in code or tool configurations.
- **Progressive Disclosure**: Briefing files point to `DESIGN.md`, which points to `docs/` for detail. Use `@docs/api-style.md`-style pointers (Claude Code and Gemini CLI both support `@file` imports).
- **Surgical Specificity**: Use exact command strings (e.g., `pnpm test:unit --filter "@shared/*"`) rather than general descriptions.
- **Standalone Files**: `AGENTS.md`, `GEMINI.md`, and `CLAUDE.md` MUST be standalone, individual regular files — never symlinks (and never symlinked to each other). They are not mirrors of each other: each file contains instructions specific to that agent/environment (e.g., `GEMINI.md` for Gemini CLI/Jetski, `CLAUDE.md` for Claude Code, `AGENTS.md` for general or other coding agents). If any briefing file is already a symlink, de-symlink it before editing: run `scripts/analyze-agent-docs.sh --fix`, which dereferences each link into a standalone file with the same content and removes the link (the link's former target is left untouched). Do this even for whole-repo setups where all three currently point at one file — split them into three independent files.
- **Design Token Coherence**: `DESIGN.md` MUST reflect the design system currently implemented in the UI. When token values, component specs, or section content diverge from shipped code, update `DESIGN.md` in the same PR or add a `.agents/TODO.md` item to sync. Run `npx @google/design.md lint` after every edit — broken token references (`{category.name}`) are silent bugs.
- **Architecture ↔ Code Coherence**: `ARCH.md` MUST reflect current shipped architecture. When implementation diverges, update `ARCH.md` in the same PR or add a `.agents/TODO.md` item to sync.
- **Memory Discipline**: If the project uses the agentic-minions T0-T4 memory system (see detection rules in `references/memory-discipline.md`), `AGENTS.md` MUST contain a **Memory Discipline** section sourced from that template. The section's mandate that `MEMORY.md` is loaded into every session is non-negotiable and MUST appear verbatim. Note: the user-level agent-memory plugin (`~/.claude/memory/`) is a separate concern — it is auto-managed by hooks and requires no per-project documentation.
- **Bundle Import**: Whenever `.agents/wiki/` exists, the briefing files MUST `@`-import its root index (`@.agents/wiki/index.md`). This is non-negotiable and is not satisfied by a prose pointer — an import is content the harness loads; prose is a decision the agent must make and was observed not making. A bundle without the import is drift and MUST be fixed on sight.
- **Evidence Discipline**: A finding that **cost investigation to establish and is not derivable from the code** goes in `.agents/wiki/` as its own concept, version-pinned. Rules go in `AGENTS.md`, open work in `.agents/TODO.md`, shipped design in `ARCH.md`. Never restate a bundle concept's body in a briefing file — link to it. See Phase 6.
- **TODO Hygiene**: Keep `.agents/TODO.md` current — prune items made obsolete by recent changes before adding new ones. Every item MUST carry a `[P0]`, `[P1]`, or `[P2]` tag (see Phase 5 for the scheme). An un-prioritized item is treated as invalid and MUST be fixed on sight.

## Instructions

### 1. Phase 1: Discovery & Baseline

[ ] **Identify Existing Docs**: Locate `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `DESIGN.md`, and any `.claude.local.md` or `.gemini.local.md`.
[ ] **Detect & De-Symlink Briefing Files**: Run `scripts/analyze-agent-docs.sh <project_root>` to inspect the three briefing files. If any of `AGENTS.md`, `GEMINI.md`, or `CLAUDE.md` is reported as a symlink, run `scripts/analyze-agent-docs.sh --fix <project_root>` to reestablish them as standalone individual files (it dereferences each link's current content into a regular file and removes the link; a dangling link becomes an empty standalone file you must repopulate). Confirm with `ls -l <project_root>` that none of the three remains a symlink before editing any of them. Do this once, up front — never edit a briefing file while it is still a symlink.
[ ] **Check TODO Backlog**: Read `.agents/TODO.md` if it exists. Note any items that may have been completed or made obsolete by recent code changes.
[ ] **Check Knowledge Bundle**: Look for `.agents/wiki/index.md`. If it exists, `grep` the briefing files for `@.agents/wiki/index.md` — a bundle with no `@`-import is **drift**, and is the exact failure this phase exists to catch; report it and fix it in Phase 3. Read the root index (titles and descriptions only) to know what evidence already exists before re-deriving it. Note any `.agents/INSIGHTS.md` for migration (Phase 6).
[ ] **Check Design Drift**: Read `DESIGN.md` (and any `docs/designs/` files it points to). Cross-reference against the current codebase — note divergence (renamed modules, new/removed components, state machine changes).
[ ] **Analyze Tooling**: Check `package.json`, `Makefile`, or `README.md` for the "Golden Path" commands (build, lint, test).
[ ] **Spot Redundancy**: Identify any rules in current docs that are already strictly enforced by linters or clearly visible in tool configs.

### 2. Phase 2: Quality Assessment & Gap Resolution Planning

[ ] **Perform Assessment**: Evaluate each file against the rubric in `references/quality-assessment.md`.
[ ] **Output Quality Report**: Generate the Quality Report using the template below.
[ ] **Plan Fixes**: For every issue or recommended change identified in the report, plan the exact updates needed to resolve it. You MUST NOT stop at reporting the gaps; immediately proceed to Phase 3 to execute the fixes.

**Quality Report Template (ALWAYS output before executing updates):**

```markdown
## Agent Instruction Quality Report

### Summary

- Files found: X
- Average score: X/100
- Sync status: [Synced / Drift detected]

### File Assessment: [Filename] (e.g., ./AGENTS.md, ./CLAUDE.md, ./GEMINI.md)

**Score: XX/100 (Grade: X)**

| Criterion                 | Score | Notes |
| ------------------------- | ----- | ----- |
| Project Goal Alignment    | X/10  | ...   |
| Operational Commands      | X/15  | ...   |
| Architecture & Tech Stack | X/15  | ...   |
| Style & Conventions       | X/15  | ...   |
| Minimalism & Conciseness  | X/15  | ...   |
| Currency & Sync           | X/15  | ...   |
| Actionability             | X/15  | ...   |

**Issues:**

- [List specific problems]

**Recommended Additions/Deletions:**

- [List specific improvements]
```

### 3. Phase 3: Structure Engineering & Execution

The document MUST follow this 5-section hierarchy, plus the conditional **Memory Discipline** section:

1. **Project Goal**: The stated goal of the project. This goal MUST be the top/first element in the project-level `AGENTS.md`. It MUST be reviewed and revisited when designing the project and when evaluating whether the project is complete. All designs, plans, and implementations MUST be in line with this stated goal. If there is a discrepancy between the ongoing work and this goal, the agent MUST prompt the user to clarify whether the goal needs to be updated/clarified, or if the discrepancy needs to be revisited.
2. **Project Context**: One-sentence purpose + high-level tech stack map.
3. **Operational Commands**: Exact strings for building, linting, and verifying changes (including per-module commands).
4. **Style & Conventions**: Specific preferences NOT covered by linters (e.g., "Prefer functional components," "Named exports only").
5. **Architecture & Constraints**: Design patterns (e.g., "Repository pattern for DB") and "Never" rules.
6. **Memory Discipline** (CONDITIONAL — required only for projects using the agentic-minions T0-T4 memory system): Sourced from `references/memory-discipline.md`. The mandate that `MEMORY.md` loads into every session MUST NOT be softened or omitted. Do NOT add this section for the user-level agent-memory plugin — that system manages itself via hooks and requires no project-level documentation.

[ ] **Execute Fixes**: Apply all recommended edits, additions, or deletions to the briefing files (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`) to resolve all identified quality issues.
[ ] **Draft/Update**: Use third-person imperative language ("The agent MUST...", "Never use...").
[ ] **Propagate Shared Changes**: The briefing files are independent standalone files — never symlinks, and not required to be byte-identical. When a change genuinely applies to more than one agent (e.g., a build command that changed), apply it to each relevant file individually so they never drift into contradiction. Keep agent-specific instructions confined to that agent's own file. Never re-link the files together to "keep them in sync" — propagate by editing each file.
[ ] **Verify**: Ensure every command added actually works by running it with `--help` or in a dry-run mode.

### 4. Phase 4: DESIGN.md Management

> **Format spec**: [google/design.md](https://github.com/google-labs-code/design.md) · package `@google/design.md` v0.1.1 · **alpha** — token categories and section list may change.

`DESIGN.md` lives at the project root and defines the project's **design system**: machine-readable tokens agents can consume, plus human-readable rationale for every design decision. It is distinct from `AGENTS.md` (operational briefing), `ARCH.md` (system architecture), and `docs/designs/` (proposals and history).

**Only create `DESIGN.md` for projects with a visual UI surface** — CLI tools, libraries, and infra-only repos do not need it.

---

**Two-layer format**

The file MUST open with a YAML front matter block (delimited by `---`) containing design tokens, followed by a markdown body with prose sections.

**YAML front matter — valid token categories:**

| Category     | Value format                                                                  | Example             |
| ------------ | ----------------------------------------------------------------------------- | ------------------- |
| `colors`     | Hex string                                                                    | `"#1A1C1E"`         |
| `typography` | Object: `fontFamily`, `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing` | —                   |
| `spacing`    | Dimension with unit                                                           | `"8px"`, `"1.5rem"` |
| `rounded`    | Dimension with unit                                                           | `"4px"`             |
| `components` | Named groups: `backgroundColor`, `textColor`, `padding`, `size`               | —                   |

Tokens may reference other tokens using `{category.name}` syntax (e.g., `{colors.primary}`). Broken references are a silent bug — always lint.

**Markdown body — canonical section order** (sections may be omitted; ordering is enforced when present):

1. Overview (also: "Brand & Style")
2. Colors
3. Typography
4. Layout (also: "Layout & Spacing")
5. Elevation & Depth (also: "Elevation")
6. Shapes
7. Components
8. Do's and Don'ts

**Skeleton:**

```markdown
---
name: "My Design System"
version: "alpha"
colors:
  primary: "#1A1C1E"
  surface: "#FFFFFF"
typography:
  body:
    fontFamily: "Google Sans"
    fontSize: "16px"
    fontWeight: 400
spacing:
  base: "8px"
  lg: "24px"
components:
  button:
    backgroundColor: "{colors.primary}"
    padding: "{spacing.lg}"
---

## Overview

One paragraph on the design system's purpose and audience.

## Colors

Prose rationale — why these colors, what they signal.

## Components

Usage examples and constraints per component.

## Do's and Don'ts

Concrete examples of correct vs. incorrect token application.
```

---

**CLI tooling (`@google/design.md` — binary: `design.md`)**

```bash
npx @google/design.md lint DESIGN.md     # validate structure + broken refs + WCAG contrast
npx @google/design.md diff HEAD~1 DESIGN.md  # detect token regressions between versions
npx @google/design.md export --format tailwind DESIGN.md  # emit Tailwind config
npx @google/design.md spec               # inject format spec into agent context
```

**What belongs in `DESIGN.md`:**

- All design tokens (colors, typography, spacing, rounded, components) in YAML front matter.
- Prose rationale for each token category — the _why_ behind design decisions.
- Usage guidance and do's and don'ts for applying tokens to UI components.

**What does NOT belong:**

- System architecture, component maps, data flows, or invariants → `ARCH.md` or `docs/designs/ARCH.md`.
- Operational commands or project conventions → `AGENTS.md`.
- Speculative or future design explorations → `docs/designs/YYYY-MM-DD-*.md`.

**Lifecycle rules:**

- Update `DESIGN.md` in the same PR that changes design tokens or design system decisions.
- Run `npx @google/design.md lint` after every edit — do not skip.
- If `DESIGN.md` exceeds ~300 lines, extract the deepest section prose to `docs/designs/` and leave a pointer.

[ ] **Create `DESIGN.md`** only if the project has a visual UI and no design system file exists yet.
[ ] **Lint `DESIGN.md`** (`npx @google/design.md lint`) after every edit.
[ ] **Cross-check token references** when updating — stale `{category.name}` refs silently break agent reasoning.

### 5. Phase 5: TODO.md Management

The `.agents/TODO.md` file is the canonical backlog for project tasks visible to agents. It lives in `<project_root>/.agents/TODO.md` (create the directory if absent).

**What belongs here**: new features, bug fixes, refactors, recommended improvements, open questions, and any task a future agent session should pick up. Anything project-related that hasn't been addressed yet.

**What does NOT belong here**: tasks that are already done, notes duplicated from `AGENTS.md`, or items so vague they can't be acted on.

#### Priority scheme (MANDATORY)

Every item MUST be tagged with one of exactly three priorities. The priority is the first thing inside the checkbox text, in square brackets, so it's visible at a glance and survives grep / copy-paste / reordering:

- **`[P0]` — highest priority; must be addressed immediately.** Reserved for bugs and broken contracts (e.g., a failing production flow, a corrupted data path, a missing file referenced by active instructions). P0s block everything else. If you're about to add a P0, ask whether it should be worked on **now** instead of queued.
- **`[P1]` — important fixes and tasks that unblock other work.** This is where the bulk of items go: feature implementations, refactors that unblock downstream changes, follow-ups agreed during design, test coverage for shipped code, documentation gaps for active surfaces.
- **`[P2]` — low-priority fixes and nice-to-haves.** Code maintenance, tidy-ups, speculative improvements, small DX wins, optional polish. It is acceptable for P2 items to sit indefinitely; if a P2 has been there for months and nobody cares, prune it.

An item without a `[P0]` / `[P1]` / `[P2]` tag is malformed. When encountering one, repair it in place — either assign a priority or delete the item if it's stale. Never leave an untagged item in the file.

**Lifecycle rules:**

- When updating any project documentation, first read the current `TODO.md` and prune items that are now stale or made obsolete by recent changes — a feature that was just implemented, a bug that was fixed, an improvement that landed in another PR.
- Add new items as they surface during work: gaps noticed in code quality, missing tests, follow-up improvements, feature ideas raised by the user.
- Keep each item actionable: one clear sentence, enough context for a future agent to act without asking follow-up questions.
- Assign a priority honestly. Over-tagging everything as `[P0]` is the fastest way to destroy the signal — if everything is urgent, nothing is.

**Format:**

```markdown
# TODO

## P0 — Address Immediately

- [ ] **[P0]** <task> — <one-line context or motivation>

## P1 — Important / Unblocking

- [ ] **[P1]** <task> — <one-line context or motivation>

## P2 — Nice-to-Have

- [ ] **[P2]** <task> — <one-line context or motivation>
```

Grouping headings are recommended when there are 5+ items so the backlog is scannable. For small backlogs a flat list is fine, but every item still carries its `[P0]` / `[P1]` / `[P2]` tag — the heading is secondary, the tag is load-bearing.

Thematic sub-groupings (e.g., `## Setup follow-ups`) may live inside a priority section or as sibling headings when items naturally cluster; the tag on the item disambiguates regardless.

[ ] **Review TODO.md** at the start of every doc update session — prune obsolete items first, then add new ones.
[ ] **Create `.agents/TODO.md`** if it doesn't exist and there are tasks worth capturing.
[ ] **Audit priorities** when reviewing: anything tagged `[P0]` that isn't actually a bug or broken contract should be re-tagged `[P1]`; anything untagged MUST be tagged or removed.

### 6. Phase 6: Knowledge Bundle Management (`.agents/wiki/`)

Full model, concept-doc shape, and anti-patterns: **`references/knowledge-bundle.md`** — read it before minting or editing a concept.

`.agents/wiki/` is the project's **runtime-evidence** store: an OKF v0.1 bundle, one concept per fact. `AGENTS.md` carries the rules; the bundle carries the evidence behind them — how each was established, against which version, and the symptom that exposed it. It replaces the flat `.agents/INSIGHTS.md`, which loaded whole every session and rotted silently.

**Scope test (MANDATORY)** — a fact belongs in the bundle only if it **cost investigation to establish and is not derivable from the code**. Rules → `AGENTS.md`. Open work → `.agents/TODO.md`. Shipped design → `ARCH.md`. Without this test the bundle becomes a second, worse README.

**Dependency on `llm-wiki` — decided; do not re-litigate.** Always scaffold the bundle. The format is markdown with YAML frontmatter, and the `@`-import plus one-concept-per-fact discipline are the entire value — neither needs the plugin. With `llm-wiki` installed, use `/llm-wiki:init` and the lifecycle commands below; without it, hand-write `index.md`, `CLAUDE.md`, and the concepts to the same shape and note in the bundle's `CLAUDE.md` that the index is hand-maintained. Absence of the plugin is NOT a reason to fall back to a flat file.

**Minting a concept** — one fact per doc. Frontmatter requires a non-empty `type`; always also write `title` and a one-sentence `description` stating a **claim, not a topic** (the description is all a future session sees in the index before deciding to open the doc). State the evidence — the command, the measurement, the symptom — and **pin the claim to the version it was verified against**. Cross-link file-relative only.

**Lifecycle commands** (when `llm-wiki` is available):

```bash
/llm-wiki:index      # regenerate index.md — after every add, rename, or delete
/llm-wiki:validate   # §9 conformance — after every edit
/llm-wiki:lint       # contradictions and stale claims — periodically, and after dependency upgrades
/llm-wiki:stats      # orphans, broken links, citation coverage
```

[ ] **Scaffold the bundle** if the project has runtime findings worth keeping and none exists (`/llm-wiki:init .agents/wiki`, or by hand).
[ ] **Add the `@`-import** to the briefing files whenever a bundle exists — this is the mechanism, not a nicety.
[ ] **Migrate `.agents/INSIGHTS.md`** if present: split into concepts (applying the scope test — most flat-file entries fail it), then delete the file. Never maintain both.
[ ] **Regenerate and validate** after any concept is added, renamed, or deleted.
[ ] **Lint for staleness** when reviewing docs — stale claims are this file type's expected failure mode, not broken links.

## Gotchas & Anti-Patterns

| Excuse / Failure                                                                     | Reality                                                                                                                                                                                                         |
| :----------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "I'll copy the whole architecture section so the agent has full context."            | Pointers save tokens. Reference the doc, don't embed it.                                                                                                                                                        |
| "I'll just add this one rule here; it's fine if the others drift."                   | Contradictions between briefing files cause hallucinations. When a rule applies to multiple agents, edit each file — they're independent standalone files, propagated by hand, never symlinked.                  |
| "I'll symlink `CLAUDE.md` → `AGENTS.md` so they stay in sync automatically."          | Symlinks are banned: they block per-agent tailoring and break silently as dangling links. Keep each file standalone; de-symlink existing links with `scripts/analyze-agent-docs.sh --fix` before editing.        |
| "The agent can figure out the test command from package.json."                       | Providing the exact command saves turns and prevents guesswork.                                                                                                                                                 |
| "I'll add a section for basic Git usage."                                            | Agents know Git. Only document project-specific Git hooks or branch naming rules.                                                                                                                               |
| "I'll use 'should' or 'consider' for flexibility."                                   | Using "should" allows agents to rationalize skipping rules. Use "MUST."                                                                                                                                         |
| "I'll skip reading TODO.md; I already know what's pending."                          | TODOs go stale silently. Always read before adding or pruning items.                                                                                                                                            |
| "I finished the feature so I don't need to update TODO.md."                          | Completed items left in the backlog mislead future agents. Remove them.                                                                                                                                         |
| "This task idea is obvious; I don't need to write it down."                          | Future agents start cold. If it's not in TODO.md, it won't be picked up.                                                                                                                                        |
| "I'll skip the priority tag — it's obvious from context which is which."             | Tags are the contract. Context rots. Every item carries `[P0]` / `[P1]` / `[P2]`; an untagged item is malformed and MUST be fixed on sight.                                                                     |
| "I'll mark it `[P0]` to make sure someone looks at it."                              | P0 is reserved for bugs and broken contracts. Inflating priorities destroys the signal — if everything is P0, nothing is. Most items are P1.                                                                    |
| "I'll leave this `[P2]` in here forever in case someone eventually cares."           | P2 is for things the project actually wants, just later. If it's been there for months and nobody cares, prune it — don't hoard dead tasks.                                                                     |
| "I'll add a pointer sentence to CLAUDE.md so the agent knows about the wiki."     | Prose pointers were observed **not firing** — a pointer sat in context for a full session unread, because "I am about to re-derive history" is not a state an agent recognises about itself. The `@`-import is the mechanism; it is content the harness loads, not a decision the agent must make. |
| "This project doesn't have `llm-wiki`, so I'll put the finding in INSIGHTS.md."   | The bundle format is markdown with YAML frontmatter. Scaffold it anyway and hand-maintain the index; the plugin makes it maintainable at scale, it is not a prerequisite. Never maintain a flat lessons file alongside a bundle.                                                                    |
| "I'll note the version this was verified against later."                          | An unpinned claim is indistinguishable from a stale one the moment the runtime updates. Runtime facts rotting is the expected failure mode, not a hypothetical. Pin on write.                                                                                                                       |
| "This finding is small — I'll append it to an existing concept."                  | One concept per fact. Merged facts cannot be individually version-pinned, invalidated, or linked to from a rule.                                                                                                                                                                                    |
| "The bundle explains the rule, so I'll paste the explanation into AGENTS.md too." | Duplication drifts into contradiction and costs the context the bundle exists to save. Keep the rule terse in `AGENTS.md` and link to the concept.                                                                                                                                                 |
| "DESIGN.md is close enough — I'll update it next sprint."                            | Stale token values or broken `{category.name}` refs silently corrupt agent reasoning. Update in the same PR or file a TODO, and always run `npx @google/design.md lint`.                                        |
| "I'll skip lint — it's just a style file."                                           | Broken token cross-references and WCAG contrast failures are silent bugs. Lint is mandatory after every edit.                                                                                                   |
| "I'll put architecture diagrams and component maps in DESIGN.md."                    | DESIGN.md is a design system (tokens + rationale), not an architecture snapshot. Architecture belongs in `ARCH.md` or `docs/designs/ARCH.md`.                                                                   |
| "This project has no UI, but I'll create DESIGN.md anyway."                          | DESIGN.md is only for projects with a visual UI surface. CLI tools, libraries, and infra repos MUST NOT have one.                                                                                               |
| "T4 isn't live yet; I'll add Memory Discipline later."                               | The mandate is forward-compatible for agentic-minions projects. Apply mandates #1–#3 now against the seed index; #10–#11 activate on rollout. Late addition means agents ship bad habits.                       |
| "Dropping mandate #1 just this once — the task is tiny."                             | Mandate #1 (MEMORY.md loads every session) is load-bearing for the agentic-minions T0-T4 tier system. Skipping it once normalizes skipping it. Do not soften.                                                   |
| "The user has the agent-memory plugin, so I should add a Memory Discipline section." | The user-level agent-memory plugin (`~/.claude/memory/`) is auto-managed by hooks — it requires no per-project Memory Discipline section in AGENTS.md. Only add the section for agentic-minions T0-T4 projects. |

## Maintenance Rule (The "Second Mistake" Rule)

The agent MUST propose an update to these instructions the second time a specific project mistake is made across sessions. Proactive maintenance is mandatory to prevent recurring friction.
