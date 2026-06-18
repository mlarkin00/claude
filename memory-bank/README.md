# memory-bank

Claude Code plugin for GCP-backed long-term memory. At session start, facts are fetched from the Vertex AI Reasoning Engine Memory Bank and injected into context. At session end, the conversation transcript is processed to extract and consolidate new facts.

Port of the `gcp-memory-bank` Gemini CLI plugin (`~/agent-skills/plugins/memory-bank`).

---

## How it works

- **SessionStart hook → `load_context.py`**: Queries the GCP Memory Bank for global facts and project-specific facts (scoped by git remote URL). Injects them as an ephemeral `<long_term_memories>` block into the Claude Code context.
- **Stop hook → `save_context.py`**: Reads the session transcript and sends conversation events to the GCP `memories:generate` endpoint for LLM-driven extraction.
- **Stop hook → `sidecar_consolidate.py`**: Daily job — aggregates all `~/.claude/projects/**/*.jsonl` transcripts, re-runs generation, and deduplicates the memory store.

### Memory scopes

| Scope | Used for | Default? |
|---|---|---|
| `global` | User preferences, cross-project rules | ✓ Yes |
| `project` | Workspace-specific context (keyed by git remote URL SHA-256) | Only on request |

---

## Prerequisites

- `gcloud` CLI installed and authenticated with Application Default Credentials:
  ```bash
  gcloud auth application-default login
  ```
- The target GCP project (`845186993936`) must have the Vertex AI API enabled.

---

## Installation

### 1. Add the marketplace

```bash
claude plugin marketplace add mlarkin00/claude
```

### 2. Install

```bash
claude plugin install memory-bank
```

### 3. Bootstrap

Run the bootstrap agent to verify the GCP engine and wire symlinks:

```
/agents run memory-bank:bootstrap-memory-bank
```

This is idempotent — safe to re-run.

---

## Plugin structure

```
memory-bank/
├── .claude-plugin/
│   └── plugin.json              manifest + GCP config (project, location, engine ID)
├── agents/
│   └── bootstrap-memory-bank.md verify engine, update config, import CC memories
├── hooks/
│   └── hooks.json               SessionStart (load) + Stop (save + consolidate)
├── scripts/
│   ├── config.py                reads .claude-plugin/plugin.json, env-var fallback
│   ├── resolve_scope.py         user hash (gcloud account) + project hash (git remote)
│   ├── load_context.py          SessionStart: fetch + inject memories
│   ├── save_context.py          Stop: extract facts from CC transcript
│   ├── sidecar_consolidate.py   Stop: daily dedup + bulk consolidation
│   ├── add_memory.py            manual add
│   ├── list_memories.py         manual list
│   ├── query_memories.py        manual similarity search
│   ├── update_memory.py         manual update
│   ├── delete_memory.py         manual delete
│   ├── set_project_scope.py     re-scope global → project
│   ├── create_engine.py         one-time engine provisioning
│   ├── import_cc_memories.py    import ~/.claude/memory/*.md into GCP
│   └── install-symlinks.sh      wires skills + scripts into ~/.claude/
└── skills/
    ├── memory-bank/             /memory-bank — save a high-priority fact immediately
    ├── memories-add/            /memories-add — add a fact
    ├── memories-list/           /memories-list — list memories
    ├── memories-update/         /memories-update — update a fact by ID
    ├── memories-delete/         /memories-delete — delete a fact by ID
    └── memories-set-project-scope/  /memories-set-project-scope — narrow global → project
```

---

## Configuration

Config is read from `.claude-plugin/plugin.json` (hardcoded defaults) with environment variable fallback:

| Key | plugin.json field | Env var |
|---|---|---|
| GCP project number | `config.project` | `GCP_PROJECT` |
| Region | `config.location` | `GCP_LOCATION` |
| Reasoning engine ID | `config.reasoning_engine_id` | `GCP_REASONING_ENGINE` |

To use a different engine, update `.claude-plugin/plugin.json` or set the env vars.
