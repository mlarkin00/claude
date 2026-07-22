# Convention

* [How a skill locates its plugin's scripts](script-resolution.md) - Try three known roots in order as two plain commands; never $CLAUDE_PLUGIN_ROOT, never ls piped to head, never a single substitution line.

# Pitfall

* [Hook payload keys differ in case between runtimes](payload-key-casing.md) - Claude Code sends snake_case, Antigravity sends protojson camelCase; a shared hook script must read both or it silently no-ops on one runtime.
