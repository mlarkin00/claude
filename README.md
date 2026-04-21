# agent-memory-plugin

Claude Code plugin that provides GitHub-backed persistent memory across sessions and machines.

Memories written in any Claude Code session are automatically committed and pushed to a private GitHub repo ([agent-memory](https://github.com/mlarkin00/agent-memory)). Every new session pulls the latest state before starting.

---

## How it works

- **SessionStart hook:** pulls the latest memory state from GitHub (remote always wins)
- **PostToolUse hook:** commits and pushes any `.md` file changes in the memory repo after every Edit or Write
- **Symlink:** `~/.claude/memory` → `~/.agents/agent-memory` (the local git clone)

Claude's memory system reads from and writes to `~/.claude/memory/` as usual — the symlink and hooks make it durable and portable.

---

## Installation

### 1. Add the marketplace

```bash
claude plugin marketplace add mlarkin00/agent-memory-plugin
```

### 2. Install the plugin

```bash
claude plugin install agent-memory
```

### 3. Bootstrap

Run the bootstrap agent in a Claude Code session to clone the memory repo and wire up hooks:

```
/agents run agent-memory:bootstrap-memory
```

This is idempotent — safe to run again if anything breaks.

---

## Plugin structure

```
agent-memory-plugin/
├── .claude-plugin/
│   ├── plugin.json          Plugin manifest
│   └── marketplace.json     Marketplace index
├── agents/
│   ├── bootstrap-memory.md  Provisions the memory system on a new machine
│   ├── memory-puller.md     Manual pull from GitHub
│   └── memory-pusher.md     Manual push to GitHub
├── hooks/
│   └── hooks.json           SessionStart (pull + verify) and PostToolUse (push) hooks
├── scripts/
│   ├── install-symlinks.sh  Creates ~/.claude/scripts, ~/.claude/agents symlinks
│   ├── memory-pull.sh       git reset --hard origin/main
│   ├── memory-push.sh       git add *.md && commit && push
│   └── verify-memory.sh     Health check with Tier 1 auto-fix and Tier 2 alerts
└── skills/
    ├── add-memory/          Saves a memory immediately without confirmation
    ├── verify-memory/       Runs health check and offers bootstrap on failure
    └── uninstall-memory/    Clean removal of all plugin artifacts
```

---

## Memory storage

The memory repo ([agent-memory](https://github.com/mlarkin00/agent-memory)) is cloned to `~/.agents/agent-memory/`. Memory files live at the repo root:

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
bash ~/.claude/scripts/verify-memory.sh
```

No output means the system is healthy. Warning lines prompt you to run the bootstrap agent.

---

## Uninstalling

Use the `uninstall-memory` skill in a Claude session, or manually:

```bash
claude plugin uninstall agent-memory
```
