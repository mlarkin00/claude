# Knowledge Bundle (`.agents/wiki/`)

The project's store for **runtime evidence**: facts that cost investigation to
establish and are not derivable from the code. An OKF v0.1 bundle — a directory of
markdown files with YAML frontmatter, one concept per fact.

`AGENTS.md` carries the *rules*. The bundle carries the *evidence* behind them: how
each was established, against which version, and the symptom that exposed it.

## Dependency on `llm-wiki` (decided — do not re-litigate per session)

**Always scaffold the bundle.** The format is plain markdown with YAML frontmatter;
the `@`-import and the one-concept-per-fact discipline are the entire value, and
neither needs tooling. The `llm-wiki` plugin makes the bundle *maintainable at
scale* — `index`, `validate`, `lint`, `stats` — but its absence is not a reason to
fall back to a flat file.

- **`llm-wiki` installed** → use `/llm-wiki:init` to scaffold, and the slash
  commands below for lifecycle.
- **Not installed** → hand-write `index.md`, `CLAUDE.md`, and the concept docs to
  the same shape. Maintain `index.md` by hand (it is small: one bullet per concept).
  Note in the bundle's `CLAUDE.md` that the index is hand-maintained.

`.agents/INSIGHTS.md` is **superseded**. When one exists, migrate its entries into
concepts (one per fact, applying the scope test — most flat-file entries fail it),
then delete the file. Do not maintain both.

## The scope test

A fact belongs in the bundle only if it **cost investigation to establish and is not
derivable from the code**.

| Content | Home |
| :--- | :--- |
| Rules, conventions, commands | `AGENTS.md` |
| Open work | `.agents/TODO.md` |
| System design as shipped | `ARCH.md` |
| Why a rule exists / what broke without it | `.agents/wiki/` |

Without this test the bundle silently becomes a second, worse README.

## Discoverability — the `@`-import is the mechanism

The briefing file MUST `@`-import the generated root index whenever a bundle exists:

```markdown
Runtime evidence — how each rule below was established, and against which
version — is an OKF bundle: `@.agents/wiki/index.md`
```

A prose pointer ("read `.agents/wiki/index.md` before re-deriving history") was
observed sitting in context for a full session without ever being opened — "I am
about to re-derive history" is not a state an agent recognises about itself. An
`@`-import is content the harness loads, not prose the agent must decide to act on.
**A bundle with no import is drift; report and fix it.**

It also costs *less* context than a flat file: the index lists titles and
descriptions only. Measured on `mlarkin00/plugins` — 823 bytes for 12 concepts,
against the 4,369-byte `INSIGHTS.md` it replaced, which loaded whole every session.
Titles in context, bodies on disk.

## Layout

```
.agents/wiki/
├── index.md          # auto-generated catalog — okf_version: "0.1" frontmatter
├── CLAUDE.md         # domain, scope test, type vocabulary, authoring conventions
└── <topic>/          # one subdirectory per topic, each with its own index.md
    └── <concept>.md
```

Root `index.md` frontmatter is the bundle-root marker — never remove it:

```yaml
---
okf_version: "0.1"
---
```

## Concept doc shape

```markdown
---
type: Runtime Behaviour        # REQUIRED, non-empty. Others: Pitfall, Convention
title: $CLAUDE_PLUGIN_ROOT does not exist in Antigravity
description: The variable is undefined in agy and empty in any model-run command,
  so it cannot be used to locate plugin files.
tags: [antigravity, hooks, paths]
timestamp: '2026-07-22T21:49:59+00:00'
---

The claim, stated up front, with the evidence that established it — the command,
the measurement, the observed symptom.

## Why it matters

The failure it causes, concretely.

## What to do instead

The rule adopted in response (which also lives in `AGENTS.md`).

# Citations

[1] [Source Title](https://example.com/...)
```

Rules:

- **`type` is the only required key**; always also write `title` and `description`.
  The description is what a future session reads in the index before deciding to
  open the doc — make it a **claim, not a topic**.
- Frontmatter key order: `type, resource, title, description, tags, timestamp`.
- **Version-pin every claim** — name the version it was verified against. Runtime
  facts rot; that is their expected failure mode, not a hypothetical.
- **Evidence over assertion.** A claim with no evidence cannot be re-checked when a
  runtime updates.
- **Cross-links are file-relative** (`[x](../antigravity/x.md)`), never absolute —
  absolute paths break GitHub rendering. Link only to concepts that exist.
- Concept ID = path minus `.md`, relative to bundle root. Segments match
  `[A-Za-z0-9_][A-Za-z0-9_.\-]*`.
- Never hand-edit `index.md` when `llm-wiki` is available — regenerate it.

## Lifecycle

| When | Do |
| :--- | :--- |
| A fact passes the scope test | Mint a concept — do not append to an existing one unless it is the same fact |
| After adding/renaming/deleting a doc | Regenerate the index (`/llm-wiki:index`, or `okf_index.py`) |
| After any edit | `/llm-wiki:validate` — §9 conformance, exit non-zero = violation |
| Periodically, and after a dependency upgrade | `/llm-wiki:lint` — contradictions and stale claims; `/llm-wiki:stats` — orphans, broken links, citation coverage |
| A rule in `AGENTS.md` gains evidence | Link the rule to its concept; keep the rule terse |

Where the bundle lives inside a repo that ships `llm-wiki`, its `PostToolUse`
validator additionally blocks a malformed concept doc at write time.

## Anti-patterns

| Excuse | Reality |
| :--- | :--- |
| "I'll add a pointer sentence to `CLAUDE.md` so the agent knows about the wiki." | Prose pointers were observed not firing. The `@`-import is the mechanism; a pointer is not a substitute. |
| "This project doesn't have `llm-wiki`, so I'll use `INSIGHTS.md`." | The format is markdown + YAML. Scaffold the bundle; hand-maintain the index. |
| "It's one small fact, I'll append it to an existing concept." | One concept per fact. Merged facts cannot be individually version-pinned or invalidated. |
| "I'll write the doc now and pin the version later." | An unpinned claim is indistinguishable from a stale one the moment the runtime updates. |
| "The index is generated, I'll just add a line by hand." | Hand edits are lost on the next regenerate. Regenerate instead — unless the project has no `llm-wiki`, in which case say so in the bundle's `CLAUDE.md`. |

## Worked reference

`mlarkin00/plugins@b77e3cf` — 12 concepts, 20 cross-links, 0 orphans, 0 broken
links, 12/12 citation coverage, §9 conformant, with `.agents/wiki/CLAUDE.md`
recording the scope test and stating that removing the `@`-import stops the bundle
being read.
