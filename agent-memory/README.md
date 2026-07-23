# agent-memory-plugin

Claude Code plugin that provides GitHub-backed persistent memory across sessions and machines.

Memories written in any Claude Code session are automatically committed and pushed to a private, per-user GitHub repo (`agent-memory`, created on bootstrap under your own account). Every new session pulls the latest state before starting.

---

## How it works

- **SessionStart hook:** pulls the latest memory state from GitHub (remote always wins)
- **PostToolUse hook:** commits and pushes any `.md` file changes in the memory repo after every Edit or Write
- **Symlink:** `~/.claude/memory` → `~/.agents/agent-memory` (the local git clone)

Claude's memory system reads from and writes to `~/.claude/memory/` as usual — the symlink and hooks make it durable and portable.

---

## Prerequisites

The [GitHub CLI](https://cli.github.com) (`gh`) must be installed and authenticated. Bootstrap uses `gh` for all GitHub interaction — auth check, repo clone/create, and configuring git to push over HTTPS with the gh token (no SSH key required):

```bash
gh auth login
```

---

## Installation

### 1. Add the marketplace

```bash
claude plugin marketplace add mlarkin00/plugins
```

### 2. Install the plugin

```bash
claude plugin install agent-memory@mlarkin00-plugins
```

The marketplace qualifier is required — a bare name exits "Plugin not found".

On Antigravity, clone the marketplace repo and bulk-install it instead:

```bash
agy plugin install <path-to-clone>
```

### 3. Bootstrap

Ask any session to "set up agent memory", which triggers the `bootstrap-memory`
skill. It clones the memory repo, wires the symlink and sync hooks, migrates any
legacy memories, and verifies the result.

Or run the script directly:

```bash
bash ~/.claude/scripts/bootstrap-memory.sh
```

Either way it is idempotent — safe to run again if anything breaks.

---

## Plugin structure

```
agent-memory-plugin/
├── .claude-plugin/
│   ├── plugin.json          Plugin manifest
│   └── marketplace.json     Marketplace index
├── hooks/
│   └── hooks.json           Claude Code: SessionStart (pull + verify), PostToolUse (push)
├── hooks.json               Antigravity: PreInvocation (pull) and PostToolUse (push)
├── scripts/
│   ├── install-symlinks.sh    Links the scripts below into ~/.claude/scripts
│   ├── bootstrap-memory.sh    Provisions the memory system on a machine (idempotent)
│   ├── memory-pull.sh         git reset --hard origin/main
│   ├── memory-push.sh         git add *.md && commit && push
│   └── verify-memory.sh       Health check with Tier 1 auto-fix and Tier 2 alerts
└── skills/
    ├── add-memory/            Saves a memory immediately without confirmation
    ├── bootstrap-memory/      Sets up or restores the system on a machine
    ├── sync-memory/           Manual pull from / push to GitHub
    ├── verify-memory/         Runs health check and offers bootstrap on failure
    └── uninstall-agent-memory/  Clean removal of all plugin artifacts
```

There is no `agents/` directory. It held three agents until 0.3.9, when they
became the skills and scripts above: Antigravity installs plugin agents but
cannot invoke them, so anything a plugin must *do* on both runtimes has to be a
skill or a hook.

---

## Memory storage

The memory repo (`agent-memory`, in your own GitHub account) is cloned to `~/.agents/agent-memory/`. Memory files live at the repo root:

```
~/.agents/agent-memory/
├── MEMORY.md              Index loaded into every session
├── GEMINI.md              Gemini CLI memory (shared storage)
└── <type>_<slug>.md       Typed memory files
```

The symlink `~/.claude/memory` → `~/.agents/agent-memory` makes this directory visible to Claude's memory system.

---

## Troubleshooting

Run the health check:

```bash
# Claude Code — via the symlink install-symlinks.sh maintains
bash ~/.claude/scripts/verify-memory.sh

# Antigravity — the plugin's own copy
bash ~/.gemini/config/plugins/agent-memory/scripts/verify-memory.sh
```

No output means the system is healthy. Warning lines prompt you to run the bootstrap agent.

The `verify-memory` skill picks the right one for you; it exists in two places because each runtime installs the plugin somewhere different, and `$CLAUDE_PLUGIN_ROOT` is set for hooks only.

---

## Uninstalling

Use the `/uninstall-agent-memory` skill in a Claude session, or manually:

```bash
claude plugin uninstall agent-memory
```
