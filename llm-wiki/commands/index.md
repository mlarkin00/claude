---
description: Regenerate all index.md files in an OKF bundle. Bottom-up walk, groups entries by type, pulls title and description from each concept's frontmatter. Add --llm for Gemini Flash directory descriptions.
---

Regenerate index.md files across the bundle.

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/okf_index.py" <bundle_root> [--llm]
```

Load the `index` skill for the full implementation and options.
