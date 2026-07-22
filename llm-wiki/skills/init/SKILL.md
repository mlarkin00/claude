---
name: init
description: Use when the user invokes /llm-wiki:init or asks to create a new OKF knowledge bundle. Scaffolds the bundle directory with a root index.md, per-bundle CLAUDE.md, .gitignore, and optional raw/ directory, then installs discovery into the host repo's briefing files so the bundle is actually read.
---

# /llm-wiki:init — Scaffold a New OKF Bundle

Creates the directory structure and seed files for a new OKF v0.1 bundle.

## Usage

```
/llm-wiki:init [path]
```

`path` defaults to the current directory if not specified.

## Steps

1. **Create the bundle directory** (if it doesn't exist).

2. **Write `index.md`** — the root index (reserved file with `okf_version` frontmatter):

   Copy from `<plugin_root>/templates/root-index.md`, substituting the bundle name.

3. **Write `CLAUDE.md`** — the per-bundle "schema" file that disciplines future authoring:

   Copy from `<plugin_root>/templates/bundle-CLAUDE.md`, substituting the bundle name and directory.
   
   The owner SHOULD edit this file to:
   - Define the `type` vocabulary for this bundle
   - Describe the domain and directory structure conventions
   - Add any source-specific ingest instructions

4. **Write `.gitignore`**:
   ```
   viz.html
   *.pyc
   __pycache__/
   okf-crawl-state.json
   ```

5. **Optionally create `raw/`** — ask the owner whether they want a `raw/` directory for immutable source files (PDFs, notes, docs). If yes, create `raw/.gitkeep`.

6. **Optionally create `seeds.txt`** — copy `<plugin_root>/templates/seeds.example.txt` as `seeds.txt` if the owner plans to use web ingest.

7. **Install discovery** — see below. Ask first; it edits files outside the bundle.

8. **Report** what was created and suggest next steps:
   ```
   Bundle initialized at <path>/
     index.md      — root index (edit okf_version if needed)
     CLAUDE.md     — edit to define your type vocabulary and conventions
     .gitignore    — excludes viz.html and cache files
   Discovery installed in <host>/CLAUDE.md (import) and <host>/AGENTS.md (inlined).

   Next steps:
     Edit CLAUDE.md to define your domain and type vocabulary.
     Add sources:  /llm-wiki:ingest <source>
     Validate:     /llm-wiki:validate <path>
   ```

## Discovery — the step that decides whether the bundle is ever read

A bundle nobody reads is worse than a backlog nobody prunes. Do not settle for a
hand-written pointer in the host repo's briefing file: a prose instruction ("read
`.agents/wiki/index.md` before re-deriving history") is a passive trigger the
agent has to *decide* to act on, and it does not fire — "I am about to re-derive
history" is not a state an agent recognises about itself. Observed failing over a
full session in `local-minions`, 2026-07-21.

What works is content the harness loads whether the agent decides to or not: the
briefing file itself. The two runtimes load them differently (verified 2026-07-22,
Claude Code 2.1.218 and `agy` 1.1.5):

| Runtime | `CLAUDE.md` | `AGENTS.md` / `GEMINI.md` | `@path` import expanded |
|---|---|---|---|
| Claude Code | loaded | **not loaded** | yes |
| Antigravity (`agy`) | not read | loaded | **no** |

So there is no one line that works everywhere, and `okf_discover.py` picks per file:
a standalone `CLAUDE.md` gets a one-line `@<bundle>/index.md` import (never stales);
`AGENTS.md`/`GEMINI.md` — and any `CLAUDE.md` symlinked to one — get the catalog
**inlined**, since `agy` will not follow an import.

Ask the owner, then run:

```bash
python3 <plugin_root>/scripts/okf_discover.py <bundle_root>
```

It edits only the region between its own `<!-- llm-wiki:discovery … -->` markers,
so it is idempotent and safe to re-run. Read its output:

- `no briefing file …` — nothing reads the bundle on any runtime. Offer
  `--create` (writes a minimal `CLAUDE.md`).
- `warning: no CLAUDE.md …` — an `AGENTS.md`-only repo is invisible to Claude
  Code. Offer to add `CLAUDE.md` as a symlink to `AGENTS.md`; the inlined block
  then serves both runtimes from one file.

Because the inlined copy can drift, `/llm-wiki:index` re-runs this with `--sync`.
Check it any time with `okf_discover.py <bundle_root> --check` (exit 1 = missing
or stale).

## What NOT to do

- Do not create concept docs during init. The bundle starts empty except for the scaffold files.
- Do not run `okf_index.py` — the root `index.md` is seeded from the template, not generated.
- Do not commit `viz.html` or crawl state files.
