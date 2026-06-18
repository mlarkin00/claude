---
name: bootstrap-memory
description: "Use when the user asks to set up or restore the agent memory system on a new machine, or when verify-memory reports structural failures requiring bootstrap. Handles full provisioning: repo clone, memory symlink, settings.json hooks, and memory migration. Examples:"

<example>
Context: User just installed the agent-memory plugin on a new machine and verify-memory reported the repo is missing.
user: "Run bootstrap-memory to set up the memory system."
assistant: "I'll use the bootstrap-memory agent to provision the memory system on this machine."
<commentary>
verify-memory detected a Tier 2 failure and directed the user here. This is the primary trigger.
</commentary>
</example>

<example>
Context: User is setting up Claude Code on a new machine and wants their memories available.
user: "Set up agent memory on this machine."
assistant: "I'll run the bootstrap-memory agent to clone your memory repo and wire up the hooks."
<commentary>
User explicitly asking to set up the memory system on a fresh machine.
</commentary>
</example>

<example>
Context: The memory system stopped syncing after reinstalling Claude Code.
user: "Memory isn't syncing anymore, can you fix it?"
assistant: "Let me run verify-memory first to diagnose, then bootstrap-memory if needed."
<commentary>
Restore scenario — hooks may have been lost when Claude Code was reinstalled.
</commentary>
</example>

model: sonnet
color: green
tools:
  - Bash
  - Read
  - Write
  - Edit
---

You are bootstrapping the agent memory system for Claude Code. Every step is idempotent — check before creating or modifying anything. Work through each step in order and print a one-line status (✓ OK / ✓ CREATED / → SKIPPED / ✗ FAILED) for each.

## Step 1: Verify GitHub CLI auth

```bash
gh auth status && gh auth setup-git
```

If `gh auth status` fails, tell the user to run `gh auth login` before continuing. Do not proceed.
If `gh` is not installed, tell the user to install it (https://cli.github.com) and stop.

`gh auth setup-git` configures git to authenticate to GitHub over HTTPS using the gh token, so the
`git push`/`git fetch` calls in the sync hooks work without an SSH key.

## Step 2: Clone the repo

Check if `~/.agents/agent-memory/.git` exists. If not:

```bash
mkdir -p ~/.agents
gh repo clone mlarkin00/agent-memory ~/.agents/agent-memory
```

If the repo does not yet exist on GitHub, create it first, then clone:

```bash
gh repo view mlarkin00/agent-memory >/dev/null 2>&1 \
  || gh repo create mlarkin00/agent-memory --private
gh repo clone mlarkin00/agent-memory ~/.agents/agent-memory
```

If already cloned, print `→ SKIPPED: repo already present`.

## Step 3: Ensure MEMORY.md exists

Check if `~/.agents/agent-memory/MEMORY.md` exists. If not:

```bash
printf "" > ~/.agents/agent-memory/MEMORY.md
```

## Step 4: Create memory symlink

Check if `~/.claude/memory` is a symlink pointing to `~/.agents/agent-memory`. If not:

```bash
ln -sfn ~/.agents/agent-memory ~/.claude/memory
```

## Step 5: Migrate existing memories

Check if `~/.claude/projects/-home-matthewlarkin-agentic/memory/` exists and contains files.

If it does, copy `.md` files without overwriting existing targets (remote copy wins):

```bash
cp -n ~/.claude/projects/-home-matthewlarkin-agentic/memory/*.md ~/.agents/agent-memory/ 2>/dev/null || true
```

If the source path does not exist, print `→ SKIPPED: no legacy memory path found`.

## Step 6: Initial commit and push

```bash
cd ~/.agents/agent-memory
git add .
git diff --cached --quiet \
  || git commit -m "memory: bootstrap cc @ $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git push origin main
```

On push failure, print `✗ FAILED: push failed — run \`gh auth status\` and check network` and stop. Do not proceed to hook registration.

## Step 7: Register hooks in ~/.claude/settings.json

Read `~/.claude/settings.json` and merge the memory hooks in without overwriting existing content. Use this Python script:

```python
import json, os

settings_path = os.path.expanduser("~/.claude/settings.json")
with open(settings_path) as f:
    s = json.load(f)

hooks = s.setdefault("hooks", {})

# SessionStart hooks
ss = hooks.setdefault("SessionStart", [])
existing_cmds = [
    hh.get("command", "")
    for h in ss
    for hh in h.get("hooks", [])
]

pull_cmd  = "bash ~/.claude/scripts/memory-pull.sh 2>/dev/null || true"
push_cmd  = "bash ~/.claude/scripts/memory-push.sh 2>/dev/null || true"

if pull_cmd not in existing_cmds:
    ss.append({"matcher": "*", "hooks": [{"type": "command", "command": pull_cmd}]})
    print("ADDED: memory-pull SessionStart hook")
else:
    print("SKIPPED: memory-pull hook already present")

# PostToolUse hook
pt = hooks.setdefault("PostToolUse", [])
if not any(push_cmd in str(h) for h in pt):
    pt.append({
        "matcher": "Edit|Write",
        "hooks": [{"type": "command", "command": push_cmd}]
    })
    print("ADDED: memory-push PostToolUse hook")
else:
    print("SKIPPED: memory-push hook already present")

with open(settings_path, "w") as f:
    json.dump(s, f, indent=2)
```

## Step 8: Run verify to confirm

```bash
bash ~/.claude/scripts/verify-memory.sh
echo "Verify exit: $?"
```

If the script outputs any `[verify-memory] ⚠` lines, report them and tell the user what to fix. No output means the system is healthy.

## Final summary

Print a complete status table for all 8 steps and confirm:

> "Memory system is ready. Your memories are synced from GitHub and will persist across machines. On each session start, the latest state is pulled automatically."
