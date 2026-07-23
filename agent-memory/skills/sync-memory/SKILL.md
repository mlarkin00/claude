---
name: sync-memory
description: Use when the user asks to manually sync memory with GitHub — "push my memories", "pull the latest memories", "refresh memory from GitHub", "make sure my memories are saved" — or when an automatic sync hook may have failed. Pull takes the remote state; push commits and pushes local memory edits.
---

Sync normally happens on its own: memory is pulled at session start and pushed
after every memory write. Use this skill when the user wants it to happen *now*,
or suspects a hook did not fire.

Pick a direction:

- **Pull** — `memory-pull.sh`. Fetches and hard-resets to `origin/main`. **The
  remote wins.** Any uncommitted local memory edit is discarded, so push first if
  the user has unsaved changes.
- **Push** — `memory-push.sh`. Stages `*.md` only, commits, pushes. A no-op when
  nothing changed.

**Step 1 — locate the script** (substitute `memory-pull.sh` or `memory-push.sh`
for `<script>`). The path differs per runtime:

```bash
ls -d ~/.claude/scripts/<script> \
      ~/.gemini/config/plugins/agent-memory/scripts/<script> \
      ~/.claude/plugins/cache/*/agent-memory/*/scripts/<script> 2>/dev/null
```

**Step 2 — run the first match in this precedence order**, which is *not* the
order `ls` prints (it sorts):

1. `~/.claude/scripts/<script>` — the version-free symlink
   `install-symlinks.sh` maintains.
2. `~/.gemini/config/plugins/agent-memory/scripts/<script>` — where Antigravity
   installs the plugin.
3. anything under `~/.claude/plugins/cache/` — last resort if the symlink was
   never created; prefer the highest version number.

```bash
bash <the path you chose>
```

If step 1 printed nothing, stop and report that the agent-memory plugin does not
appear to be installed.

Two constraints worth knowing before you "simplify" this: `$CLAUDE_PLUGIN_ROOT`
is set for hooks only and is **empty** in a command you run, and a one-liner
using `$(…)` command substitution gets auto-denied in a headless Antigravity
session — two plain commands are what survive a permission allowlist.

## Interpreting the result

Both scripts are fail-open — they warn and exit 0 rather than break a session —
so read the output rather than the exit code.

- **No output** — it worked. Report one line: "Memory synced from GitHub." or
  "Memory pushed to GitHub."
- **`SKIP: repo not found`** — the memory repo has never been set up on this
  machine. Offer to run the `bootstrap-memory` skill.
- **`WARNING: fetch failed` / `WARNING: push failed`** — network or auth. Have
  the user check `gh auth status`. On a failed push the local write is still
  safe and will go out with the next sync.

Authentication is the gh CLI token over HTTPS, configured during bootstrap — no
SSH key is involved, so "permission denied (publickey)" means something other
than this plugin is misconfigured.
