# Skill Forge Audit Report: active-skills/close-session

| Check | Status | Finding |
| --- | --- | --- |
| naming | ✅ | Matches specification. |
| frontmatter | ⚠️ | Description MUST start with 'Use when...' or 'Use this skill when...'. Missing 'category' field in YAML frontmatter metadata. |
| tone | ❌ | Found passive suggestion prose (should, consider, might). Use MUST/NEVER for discipline skills. |
| paths | ✅ | Forward slashes used. |
| scripts | ✅ | Deterministic and non-interactive. |
| references | ✅ | Modular with TOC where needed. |
| evals | ❌ | Missing 'evals/' directory. |
| security | ✅ | No obvious secrets found. |
| config | ✅ | Configuration isolation standards are satisfied. |

_Generated automatically by skill-forge-minion._
