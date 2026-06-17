# kube-agents Claude Code plugin

stdio MCP server giving Claude Code direct access to the **kube-agents platform
agent** via the Gemini Managed Agents **Interactions API**. This is an
alternative path to the A2A Cloud Run endpoint — no Cloud Run hop, just ADC →
Interactions API.

## Tools

| Tool | Purpose |
|---|---|
| `ask_platform_agent(prompt, previous_interaction_id?)` | Send a prompt to the platform agent. Returns `{"text", "interaction_id"}`. Pass `interaction_id` back to continue a conversation (multi-turn). Streams the agent's tool-call steps as live MCP progress notifications while it works; archives a full transcript to GCS. |
| `reset_sandbox()` | Forget the persisted warm-sandbox env id; next call cold-starts a fresh sandbox. |

## Streaming & transcripts

`ask_platform_agent` runs the interaction with `stream:true` (SSE). As the agent
reasons and calls tools, each step surfaces two ways:

- **Live progress** — one MCP progress notification per tool-call step
  (`ctx.report_progress`), so the client shows ticks like *"Listing managed
  namespaces"*, *"Running whoami and id"* while the agent runs. Only the agent's
  final reply text is returned as the tool result (narration is not).
- **Audit transcript** — the full interaction (every text block, tool call, tool
  result, token usage, elapsed time, tool-call count) is written **once** to GCS
  at `gs://<GCS_BUCKET>/<TRANSCRIPT_PREFIX>/<YYYY-MM-DD>/<interaction_id>.json`.
  Not real-time; for review/audit. Disable with `TRANSCRIPTS_ENABLED=0`.

Cloud Logging of narration is intentionally **not** done from this local stdio
server (stdout is the JSON-RPC channel; logging stays on stderr).

The server reuses a **shared** `environment_id` stored in one GCS object
(`gs://managed-kube-agents-mslarkin-demo/data/platform/environment_id`) — the
same object the A2A executor and the `kube-platform-keepwarm` Cloud Scheduler job
use. So this server, A2A, and the heartbeat all warm **one** sandbox. The
heartbeat pings every 6h to keep the 7-day TTL alive, so the ~150-210s cold start
is never hit (~12s warm). Reset with the `reset_sandbox` tool (deletes the GCS
object; next interaction re-provisions + re-persists).

## Skill

`/kube-agents <input>` — transparent pass-through that forwards `<input>`
verbatim to the platform agent via `ask_platform_agent` and relays the reply
unchanged. Threads `interaction_id` across turns for multi-turn continuity.
Defined in `skills/kube-agents/SKILL.md`.

## Prerequisites

- `python3` (3.10+) with `venv`
- Application Default Credentials with `aiplatform.user` on the project, plus
  object write on `GCS_BUCKET` (for the shared env id + transcripts; e.g.
  `roles/storage.objectAdmin` on the bucket):
  ```bash
  gcloud auth application-default login
  ```

## Install

Standalone (from this directory or its git repo):

```bash
/plugin marketplace add /home/user/kube-agents-plugin
/plugin install kube-agents@kube-agents
```

On first launch, `scripts/run-server.sh` creates a `.venv` and installs
`requirements.txt` automatically (idempotent). No manual `pip install` needed.

## Configuration (env overrides, all optional)

| Var | Default | Meaning |
|---|---|---|
| `AGENT_PROJECT_ID` | `111393542471` | Numeric GCP project id |
| `AGENT_ID` | `kube-platform` | Agent resource id |
| `AGENT_LOCATION` | `global` | Agent location |
| `GCS_BUCKET` | `managed-kube-agents-mslarkin-demo` | Bucket holding the shared env id |
| `ENV_STATE_OBJECT` | `data/platform/environment_id` | Shared warm-sandbox id object |
| `TRANSCRIPT_PREFIX` | `data/platform/transcripts` | GCS dir for audit transcripts |
| `TRANSCRIPTS_ENABLED` | `1` | Set `0` to disable GCS transcript writes |
| `PYTHON_BIN` | `python3` | Interpreter used to build the venv |

Set overrides in `.mcp.json` under the server's `env` block if needed.

## Layout

```
kube-agents-plugin/
├── .claude-plugin/
│   ├── plugin.json          # manifest, points at ./.mcp.json
│   └── marketplace.json     # standalone-install marketplace
├── .mcp.json                # stdio server -> scripts/run-server.sh
├── scripts/run-server.sh    # venv bootstrap + exec server (stdout = JSON-RPC)
├── servers/platform_mcp.py  # the MCP server (FastMCP)
└── requirements.txt
```
