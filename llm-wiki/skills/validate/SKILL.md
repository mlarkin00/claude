---
name: validate
description: Use when the user invokes /llm-wiki:validate or asks to validate an OKF bundle for conformance. Runs okf_validate.py over the whole bundle and reports violations.
---

# /llm-wiki:validate — Validate Bundle Conformance

Checks every non-reserved `.md` file in an OKF bundle for §9 conformance: parseable YAML frontmatter with a non-empty `type` field.

## Usage

```
/llm-wiki:validate [path]
```

`path` defaults to the current directory (or the nearest bundle root if in a subdirectory).

## Steps

Run:
```bash
python3 <plugin_root>/scripts/okf_validate.py <bundle_root>
```

- Exit 0: bundle is conformant. Report: "Bundle at <path> is OKF §9 conformant (N files checked)."
- Exit 1: violations found on stderr. Report each violation and suggest fixes.

## Interpreting violations

| Violation message | Cause | Fix |
|---|---|---|
| `missing frontmatter block` | File has no `---` frontmatter | Add frontmatter with at minimum `type:` |
| `unparseable frontmatter` | YAML syntax error | Fix the YAML (check indentation, special chars) |
| `'type' is missing or empty` | Frontmatter exists but `type` is absent or blank | Add `type: <value>` to frontmatter |

## Reserved files

`index.md` and `log.md` are skipped — they do not need frontmatter (except the root `index.md` which carries `okf_version`).

## Relationship to the hook

The **PostToolUse hook** runs `okf_validate.py --file` on every single `.md` write in hook mode (softer: skips files with no frontmatter at all). `/llm-wiki:validate` runs the **strict** full-bundle check which catches ALL non-conformant files including those with no frontmatter at all.

Run validate before committing a bundle or sharing it.
