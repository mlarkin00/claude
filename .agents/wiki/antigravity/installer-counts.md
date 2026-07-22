---
type: Pitfall
title: agy plugin install component counts are not evidence
description: The counts report what the installer walked, not what the runtime can
  use; three were demonstrably false in one session.
tags:
- antigravity
- install
- verification
timestamp: '2026-07-22T21:49:59+00:00'
---

`agy plugin install` prints a per-component summary. It reports what the installer
**walked**, not what the runtime can **use**. Three counts were false in a single
review:

- `commands : 10 processed (converted to skills)` — printed identically whether 10
  skill directories were written or **zero** ([install paths](install-paths.md)).
- `hooks : 1 processed` — counted a hook whose command resolved to a nonexistent
  path ([plugin root env](plugin-root-env.md)).
- `agents : 3 processed` — counted agents nothing can invoke
  ([component support](component-support.md)).

## Verify by effect instead

- a marker or state file the hook writes
- a counted skill invocation
- a validator line in `~/.gemini/antigravity-cli/cli.log` (hook stderr lands there)
- a committed memory, a real API response

`agy plugin validate <path>` is also not a general check: it hard-fails with
`missing plugin.json` on any plugin without a root manifest. The usable command is
a bulk install into a throwaway `HOME`:

```bash
HOME=$(mktemp -d) agy plugin install "$PWD"
```

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
