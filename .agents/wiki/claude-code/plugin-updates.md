---
type: Pitfall
title: Updating an installed Claude Code plugin
description: claude plugin update needs the name@marketplace form, and `details` resolves
  the newest cached version rather than the loaded one — so a fix can look live while
  the session still runs old code.
tags:
- claude-code
- install
- verification
timestamp: '2026-07-22T22:20:27+00:00'
---

Claude Code plugin caches are **version-keyed**. Installing a fix is three
separate things — release it, point the install at it, restart — and each can
succeed while a later one silently does not.

## The name must be qualified

```bash
claude plugin update agent-memory                    # ✘ Plugin "agent-memory" not found
claude plugin update agent-memory@mlarkin00-plugins  # ✔ updated 0.3.7 -> 0.3.8
```

The bare name fails. It exits non-zero with a clear message, so the only way to
miss it is to discard the output — which is exactly what happened: three updates
were run with `>/dev/null 2>&1`, all three failed, nothing was staged, and the
subsequent restart faithfully reloaded the old versions.

## `claude plugin details` is not proof the fix is loaded

`details` resolves the **newest cached** version. `installed_plugins.json` holds
the `installPath` the harness actually loads. They disagree whenever a newer
version has been fetched but not adopted, and in that state `details` happily
reports the fixed inventory for code the session is not running.

Check the loaded version, not the reported one:

```bash
python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))['plugins'];print({k:v[0]['version'] for k,v in d.items()})"
```

## Order that works

1. push, and let `release.yml` cut the version
2. `claude plugin marketplace update <marketplace>`
3. `claude plugin update <plugin>@<marketplace>` — **read the output**
4. confirm `installed_plugins.json` matches the released version
5. restart, then verify against the installed cache path, not the working tree

Antigravity has no equivalent staging step: `agy plugin install <clone>` copies
from the working tree immediately.

This is the Claude-side instance of the rule in
[installer counts](../antigravity/installer-counts.md) — verify by effect, and
never from a command whose output you did not read.

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
