# Insights

Runtime behaviour that cost real testing to establish and is **not derivable from
the code**. Rules that follow from these live in `AGENTS.md`; this file is the
evidence, so a future session does not re-derive it or "simplify" a guard away.

Established 2026-07-22 against `agy` 1.1.5 / Claude Code 2.1.217.

## Antigravity

**The hooks spec is embedded in the `agy` binary.** `strings $(readlink -f $(which agy))`
and search for `` `PreInvocation` Contract `` — it documents the file format, the
five events, the matcher rules, and every stdin/stdout contract. Read it before
guessing. A raw string match is not the schema: `SessionStart` appears in the
binary but is not a hook event.

**`$CLAUDE_PLUGIN_ROOT` does not exist there.** Not as that name, not as any
`*_PLUGIN_ROOT` or `AGY_*` equivalent — the string is absent from the whole
188 MB binary. A converted Claude hook referencing it runs `bash "/hooks/x.sh"`
and dies. Claude populates it for *hooks only*; it is empty in a command the
model runs, on both runtimes.

**Installer counts are not evidence.** Three of them were false in one session:
`commands : 10 processed (converted to skills)` printed identically whether 10
directories were written or zero; `hooks : 1 processed` counted a hook whose
command pointed at a nonexistent path; `agents : 3 processed` counted agents no
session can invoke. Verify by observing an effect.

**A root `plugin.json` switches the install path**, and the two paths differ in
what they do with the rest of the plugin:

| | no root `plugin.json` (claude-format) | with root `plugin.json` (native) |
|---|---|---|
| `hooks/hooks.json` | converted, `$CLAUDE_PLUGIN_ROOT` left intact → broken | ignored |
| root `hooks.json` | **merged** with the converted block — both fire | used as-is |
| `commands/` | converted to `<plugin>-cmd-*` skills | not converted |

The merge is the trap: shipping a correct root `hooks.json` without a root
`plugin.json` leaves the broken converted copy firing alongside it on every tool
call.

**`PreInvocation` is not `SessionStart`.** It fires before *every* model call and
blocks the agent loop, so unguarded session-once work runs per turn — measured
~3.6 s for a Vertex round-trip. But its `ephemeralMessage` is **transient**: a
gate that simply skips after the first invocation leaves later turns with nothing.
A first cut did exactly that, passed every offline test, and failed live on turn 2
with "NO MEMORIES INJECTED". Context-injecting hooks must **cache and replay**;
only side-effect hooks (a `git fetch`) may skip.

**Sidecars are not loaded from plugins.** `agy` reads `<config>/sidecars/<id>/sidecar.json`
— i.e. `~/.gemini/config/sidecars/` — one directory per sidecar. A `sidecars/`
directory inside a plugin is inert: no `sidecar_data/`, no process, and the
installer never lists it as a component.

**Headless permission matching is first-word based.** `bash <path>` and
`ls -d <paths> 2>/dev/null` pass with `command(bash)` / `command(ls)`; a leading
`SCRIPT=$(…)` assignment or a `$(…)` substitution is auto-denied with no prompt.
Skills that shell out must be two plain commands.

## Cross-runtime

**Hook payload keys differ in case.** Claude Code sends snake_case
(`transcript_path`, `tool_name`, `tool_input`, `cwd`); Antigravity sends protojson
camelCase (`transcriptPath`, `toolCall.args`, `workspacePaths`, `conversationId`).
A shared script must read both. `save_context.py` read only the camelCase key and
was a silent no-op under Claude Code for the plugin's entire life — the Stop hook
ran, found nothing, exited 0.

**A test suite that only feeds one runtime's payload will stay green through
that.** All four `save_context` cases used Antigravity keys. Assert both shapes.

**`ls a b c | head -1` does not honour argument order** — `ls` sorts, so the first
line is the alphabetically smallest path. With a versioned-cache candidate in the
list that silently selects a *stale* copy over the live symlink. Order-sensitive
lookups need an explicit loop, or prose the model applies.

**Mocks and module reloading.** `sys.modules.pop('<module>')` *inside* a test body
discards the `@patch`-ed module; the fresh import rebinds the real function and
the test makes live network calls — and any `assertFalse(mock.called)` then passes
vacuously. Let `tearDown` clear the module.
