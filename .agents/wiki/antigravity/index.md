# Pitfall

* [agy plugin install component counts are not evidence](installer-counts.md) - The counts report what the installer walked, not what the runtime can use; three were demonstrably false in one session.
* [Headless permission matching is first-word based](headless-permissions.md) - agy -p matches allow-rules on the command's first word, so a leading assignment or any $( ) substitution is auto-denied with no prompt.
* [PreInvocation is not SessionStart](preinvocation-semantics.md) - It fires before every model call and blocks the loop, and its ephemeralMessage is transient, so session-once work must be gated and injected context must be cached and replayed.
* [Sidecars load from the config directory, never from a plugin](sidecar-location.md) - agy reads <config>/sidecars/<id>/sidecar.json; a sidecars/ directory inside a plugin is inert and is never listed as a component.

# Runtime Behaviour

* [$CLAUDE_PLUGIN_ROOT does not exist in Antigravity](plugin-root-env.md) - The variable is undefined in agy and empty in any model-run command, so it cannot be used to locate plugin files.
* [Antigravity hooks contract](hooks-contract.md) - agy runs hooks only from a plugin's root hooks.json, supports five events, and sets cwd to that file's directory.
* [Two install paths, selected by the root plugin.json](install-paths.md) - A root plugin.json puts agy on its native path; without one it takes the claude-format path, which converts commands and merges a broken hooks block.
* [Which plugin components actually work on Antigravity](component-support.md) - Skills and hooks work; agents install but cannot be invoked; sidecars are never registered from a plugin directory.
