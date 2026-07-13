# Skill Forge Audit Report: active-skills/brainstorming

| Check | Status | Finding |
| --- | --- | --- |
| naming | ⚠️ | Skill name 'brainstorming' uses a gerund form (ends in '-ing'). Avoid gerunds and prefer simple, descriptive names (e.g. 'code-design' instead of 'designing-code', 'doc-review' instead of 'reviewing-docs'). |
| frontmatter | ✅ | Format is valid. |
| tone | ❌ | Found passive suggestion prose (should, consider, might). Use MUST/NEVER for discipline skills. |
| paths | ✅ | Forward slashes used. |
| scripts | ⚠️ | Destructive script 'stop-server.sh' missing --dry-run flag. |
| references | ✅ | Modular with TOC where needed. |
| evals | ❌ | Missing 'evals/' directory. |
| security | ✅ | No obvious secrets found. |
| config | ✅ | Configuration isolation standards are satisfied. |

_Generated automatically by skill-forge-minion._
