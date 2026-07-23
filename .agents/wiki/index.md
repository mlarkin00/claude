---
okf_version: "0.1"
---

# Subdirectories

* [antigravity](antigravity/index.md) - Contains 9 entries: Which plugin components actually work on Antigravity, Headless permission matching is first-word based, Antigravity hooks contract, agy plugin install is additive — it never deletes files removed from the source, Two install paths, selected by the root plugin.json, agy plugin install component counts are not evidence, $CLAUDE_PLUGIN_ROOT does not exist in Antigravity, PreInvocation is not SessionStart, The agy CLI never starts the sidecar manager.
* [claude-code](claude-code/index.md) - claude plugin update needs the name@marketplace form, and `details` resolves the newest cached version rather than the loaded one — so a fix can look live while the session still runs old code.
* [cross-runtime](cross-runtime/index.md) - Contains 3 entries: Each runtime reads a different briefing file, and only one expands imports, Hook payload keys differ in case between runtimes, How a skill locates its plugin's scripts.
* [testing](testing/index.md) - Contains 2 entries: ls does not honour argument order, Popping a patched module makes tests hit the network.
