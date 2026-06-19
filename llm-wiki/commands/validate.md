---
description: Validate OKF §9 conformance across the entire bundle. Checks every non-reserved .md file for parseable YAML frontmatter with a non-empty 'type' field. Exits non-zero on any violation.
---

Run full §9 conformance check on the bundle.

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/okf_validate.py" <bundle_root>
```

Load the `validate` skill for interpretation of results and fix suggestions.
