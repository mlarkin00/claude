---
name: uninstall-agent-memory
description: This skill should be used when the user wants to uninstall, remove, or clean up the agent-memory plugin. Handles removal of symlinks, hooks, optional memory data deletion, and plugin de-registration in a safe, step-by-step sequence.
---

You are uninstalling the agent-memory plugin. Work through each step in order. Print a one-line status after each step.

## Step 1: Remove symlinks

```bash
rm -f \
  ~/.claude/scripts/memory-pull.sh \
  ~/.claude/scripts/memory-push.sh \
  ~/.claude/scripts/verify-memory.sh \
  ~/.claude/agents/memory-puller.md \
  ~/.claude/agents/memory-pusher.md \
  ~/.claude/skills/verify-memory.md \
  ~/.claude/skills/add-memory.md \
  ~/.claude/memory
echo "✓ Symlinks removed"
```

## Step 2: Remove memory hooks and plugin registration from ~/.claude/settings.json

Run this single Python script to update settings.json atomically:

```python
import json, os

settings_path = os.path.expanduser("~/.claude/settings.json")
with open(settings_path) as f:
    s = json.load(f)

hooks = s.get("hooks", {})

# Remove SessionStart memory hooks
hooks["SessionStart"] = [
    h for h in hooks.get("SessionStart", [])
    if not any(
        "memory-pull" in hh.get("command", "") or "memory-push" in hh.get("command", "")
        for hh in h.get("hooks", [])
    )
]

# Remove PostToolUse memory-push hook
hooks["PostToolUse"] = [
    h for h in hooks.get("PostToolUse", [])
    if not any("memory-push" in hh.get("command", "") for hh in h.get("hooks", []))
]

s["hooks"] = hooks

# Remove plugin registration
s["plugins"] = [p for p in s.get("plugins", []) if "agent-memory" not in str(p)]

with open(settings_path, "w") as f:
    json.dump(s, f, indent=2)
print("✓ Memory hooks and plugin registration removed from settings.json")
```

## Step 3: Ask about memory data

Ask the user:

> "Do you want to permanently delete `~/.agents/agent-memory`? This contains all your stored memories and **cannot be undone**. Type exactly `YES` (uppercase, case-sensitive) to delete, or anything else to keep it."

**If the user types YES (exact match, case-sensitive):**

```bash
rm -rf ~/.agents/agent-memory
echo "✓ Memory repository deleted"
```

**Otherwise:**

```
→ Memory data preserved at ~/.agents/agent-memory
  You can re-install the plugin later and run bootstrap-memory to reconnect it.
```

## Step 4: Uninstall the plugin

```bash
claude plugin uninstall agent-memory
echo "✓ Plugin uninstalled"
```

## Final summary

Print a closing line confirming all steps completed:

> "The agent-memory plugin has been fully uninstalled. Memory sync hooks are removed and the plugin will not load in future sessions."
