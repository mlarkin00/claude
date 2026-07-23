---
type: Runtime Behaviour
title: Each runtime reads a different briefing file, and only one expands imports
description: Claude Code loads CLAUDE.md and expands `@` imports but never reads AGENTS.md;
  agy loads AGENTS.md/GEMINI.md but ignores imports — so no single line reaches both.
tags:
- cross-runtime
- context
---

Briefing files are the only channel that reaches a session unconditionally, so
what each runtime loads decides whether anything is read at all. The two do not
agree, verified 2026-07-22 against **Claude Code 2.1.218** and **agy 1.1.5**.

## The matrix

| | `CLAUDE.md` | `AGENTS.md` / `GEMINI.md` | `@path` expanded |
|---|---|---|---|
| Claude Code | loaded | **not loaded** | **yes** |
| Antigravity (`agy`) | not read | loaded | **no** |

A backticked `` `@path` `` is **not** expanded on either — Claude Code treats it
as prose, so pointers written inside code spans are inert.

## How it was established

A fixture repo with two codewords: one written directly into the briefing file,
one only in `wiki/index.md`, referenced as `@wiki/index.md`. Each runtime was
asked, with tools disabled, to report both from context.

```
CLAUDE.md   → claude -p  : direct BANJO-2210, imported XYLOPHONE-4471   (both)
AGENTS.md   → claude -p  : ABSENT, ABSENT                               (file unread)
AGENTS.md   → agy -p     : direct BANJO-2210, imported ABSENT           (no expansion)
GEMINI.md   → agy -p     : direct BANJO-2210, imported ABSENT           (no expansion)
```

`agy -p` ignores the process working directory — it resolved the workspace to
`$HOME` and its shell tool listed that instead. Pass `--add-dir <repo>` or the
test measures nothing.

## Consequence

There is no one line that works on both runtimes. A symlinked `CLAUDE.md` with
**inlined** pointers satisfies both from one file, but forfeits per-runtime
instructions and is banned by the `managing-agent-instructions` convention. This
repo therefore keeps two standalone twins, hand-propagated, differing only in the
discovery mode: `@`-import in `CLAUDE.md`, inlined catalog in `AGENTS.md`.
`llm-wiki/scripts/okf_discover.py` picks the mode per file and `--check` fails
when the inlined copy drifts.

Hand propagation is what makes the twins drift, and a drifted convention is
invisible for the same reason the mechanism is: each runtime only ever sees the
file it reads. `.agents/scripts/check-briefing-twins.py` compares the two after
masking the only two regions allowed to differ — the twin-pointer sentence and
the discovery block — and also asserts each file carries the discovery mode its
runtime can use, since swapping them compiles fine and reaches no one. The
`Check briefings` workflow runs it alongside `okf_discover.py --check`; between
them the prose and the generated catalog are both covered. It is deliberately
not part of `release.yml`: drifted prose does not make a plugin release unsafe,
and a docs check that blocks releases gets bypassed.

This bundle was unreachable on **both** runtimes until 2026-07-22: `AGENTS.md`
carried the pointer as a backticked `` `@.agents/wiki/index.md` ``, which Claude
Code would not have expanded even if it had read the file, and which `agy` read
as ordinary prose. The visible symptom was nothing at all — the failure of a
context mechanism is silent, so verify it in a live session rather than by
reading the file.

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
