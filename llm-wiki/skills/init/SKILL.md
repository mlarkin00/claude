---
name: init
description: Use when the user invokes /llm-wiki:init or asks to create a new OKF knowledge bundle. Scaffolds the bundle directory with a root index.md, per-bundle CLAUDE.md, .gitignore, and optional raw/ directory.
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

7. **Report** what was created and suggest next steps:
   ```
   Bundle initialized at <path>/
     index.md      — root index (edit okf_version if needed)
     CLAUDE.md     — edit to define your type vocabulary and conventions
     .gitignore    — excludes viz.html and cache files

   Next steps:
     Edit CLAUDE.md to define your domain and type vocabulary.
     Add sources:  /llm-wiki:ingest <source>
     Validate:     /llm-wiki:validate <path>
   ```

## What NOT to do

- Do not create concept docs during init. The bundle starts empty except for the scaffold files.
- Do not run `okf_index.py` — the root `index.md` is seeded from the template, not generated.
- Do not commit `viz.html` or crawl state files.
