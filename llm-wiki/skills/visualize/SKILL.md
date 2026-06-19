---
name: visualize
description: Use when the user invokes /llm-wiki:visualize or asks to generate a graph visualization of an OKF bundle. Runs okf_visualize.py to produce a self-contained HTML file.
---

# /llm-wiki:visualize — Generate Bundle Visualization

Generates a self-contained `viz.html` — a Cytoscape.js force-directed graph where nodes are concepts and edges are cross-links. Zero runtime dependencies; opens in any browser.

## Usage

```
/llm-wiki:visualize [path] [--out <file>] [--name <label>]
```

`path` defaults to the nearest bundle root. `--out` defaults to `<bundle_root>/viz.html`. `--name` overrides the bundle display name.

## Steps

Run:
```bash
python3 <plugin_root>/scripts/okf_visualize.py <bundle_root> [--out <file>] [--name <label>]
```

Prints JSON stats on stdout: `{"concepts": N, "edges": M, "bytes": K}`.
Prints a summary on stderr: `Wrote N concept(s), M edge(s), K bytes → viz.html`.

## What the viewer shows

- **Nodes**: one per concept. Colored by type (BigQuery Dataset = purple, BigQuery Table = blue, Reference = green, others = slate). Size proportional to body length.
- **Edges**: directed arrows for each `[text](../target.md)` link in the body.
- **Detail panel** (right): click a node to see its frontmatter (type, description, resource, tags) and rendered body. Backlinks ("Cited by") list concepts that link to it.
- **Controls**: search (title/id/tag), filter by type, layout selector (cose, concentric, breadth-first, circle, grid), reset view button.

## Type color palette

The visualizer uses these colors for known types; unknown types get slate:

| Type | Color |
|---|---|
| BigQuery Dataset | `#8b5cf6` (purple) |
| BigQuery Table | `#3b82f6` (blue) |
| Reference | `#10b981` (green) |
| Other | `#94a3b8` (slate) |

To add colors for your bundle's custom types, edit `viewer/generator.py` → `_TYPE_PALETTE`.

## Notes

- `viz.html` is excluded from git by default (`.gitignore` written by `/llm-wiki:init`). Regenerate on demand rather than committing it.
- Cytoscape and marked.js are loaded from CDN at view time; requires internet access when opening the file.
- Internal links in concept bodies are rewritten to navigate within the viewer (click triggers node selection). External links open in a new tab.
