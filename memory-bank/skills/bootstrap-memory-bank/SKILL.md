---
name: bootstrap-memory-bank
description: Use when setting up the memory-bank plugin on a machine, when the GCP reasoning engine needs to be created, or when load_context.py returns no memories and you suspect the engine ID is wrong. Verifies ADC, creates or confirms the reasoning engine, writes the engine ID back to the manifest, and confirms context loads.
---

Provisioning is a script, not a procedure you run by hand. `bootstrap.py` is
idempotent — it verifies the engine before creating one, so a re-run on a
healthy machine reports OK/SKIPPED rather than making a second engine. It is
non-interactive and safe to run headless; the one yes/no decision (importing
existing Claude Code memories) is a flag this skill sets after asking.

**Step 1 — locate the script.** The path differs per runtime:

```bash
ls -d ~/.claude/scripts/memory-bank/bootstrap.py \
      ~/.gemini/config/plugins/memory-bank/scripts/bootstrap.py \
      ~/.claude/plugins/cache/*/memory-bank/*/scripts/bootstrap.py 2>/dev/null
```

**Step 2 — run the first match in this precedence order**, which is *not* the
order `ls` prints (it sorts):

1. `~/.claude/scripts/memory-bank/bootstrap.py` — the version-free symlink
   `install-symlinks.sh` maintains for Claude Code.
2. `~/.gemini/config/plugins/memory-bank/scripts/bootstrap.py` — where
   Antigravity installs the plugin.
3. anything under `~/.claude/plugins/cache/` — last resort if the symlink was
   never created; prefer the highest version number.

**First ask** whether to import existing memories:

> "Do you want to import your existing Claude Code memory files
> (`~/.claude/memory/*.md`) into the GCP Memory Bank?"

Then run the path you chose, adding `--import-cc` only if they said yes:

```bash
python3 <the path you chose>              # setup only
python3 <the path you chose> --import-cc  # setup, then import ~/.claude/memory
```

If step 1 printed nothing, stop and report that the memory-bank plugin does not
appear to be installed.

Two constraints worth knowing before you "simplify" this: `$CLAUDE_PLUGIN_ROOT`
is set for hooks only and is **empty** in a command you run — the script resolves
its own plugin root from `__file__`, so it does not need it — and a one-liner
using `$(…)` command substitution gets auto-denied in a headless Antigravity
session, so keep the lookup and the call as two plain commands.

## Interpreting the result

The script prints one line per step and exits 0 when the Memory Bank is ready.

- **Exit 0** — report the status. A `SKIPPED` line is normal: Step 5 skips when
  no import was requested, and Step 6 skips off Claude Code (Antigravity reaches
  the scripts at their install path and needs no `~/.claude` symlinks).
- **Exit 1** — it stopped at the first hard failure; the final `✗ FAILED` line
  says which step and what to do. Relay it, apply the fix if it is yours, then
  re-run.

The failures that need the user:

| `✗ FAILED` mentions | What the user must do |
|---|---|
| `gcloud is not installed` | Install the Google Cloud SDK |
| `no application-default credentials` | Run `gcloud auth application-default login` |
| `config.project and config.location must be set` | Fill those into the manifest, or export `GCP_PROJECT` / `GCP_LOCATION` |

When Step 3 creates an engine, the new ID is written back to the manifest
automatically (a `json.dump`, not a hand edit) — you do not need to edit
`plugin.json` yourself.
