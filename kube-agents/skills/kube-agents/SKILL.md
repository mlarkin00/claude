---
name: kube-agents
description: "Forward a query to the kube-agents platform agent via the kube-platform MCP server. Use when the user invokes /kube-agents <input>, or asks to query/route something to the kube-agents platform agent — cluster status, deployments, operator tasks, governance. Transparent pass-through: the input goes to the platform agent unchanged and its reply is relayed verbatim."
---

# kube-agents

Transparent pass-through to the **kube-agents platform agent** via the
`kube-platform` MCP server (Interactions API path). The platform agent
orchestrates GKE clusters, operators, and devteam agents.

## Procedure

1. Take everything after `/kube-agents` (the skill argument) as the **user
   query**, verbatim. Do not summarize, rephrase, or interpret it.
2. Call the MCP tool:
   `mcp__plugin_kube-agents_kube-platform__ask_platform_agent` with
   `prompt` = the user query.
3. The tool returns JSON: `{"text": <reply>, "interaction_id": <id>}`. Relay
   `text` to the user **verbatim** — no editing, no added commentary.
4. Note the returned `interaction_id`. If the user's next message continues the
   same conversation, pass it back as `previous_interaction_id` on the next
   call so the platform agent keeps history.

## Rules

- Pass-through only. The platform agent does the work; you relay.
- If the argument is empty, ask the user what to send to the platform agent.
- The MCP server reuses a warm sandbox automatically (stable `environment_id`).
  Calls may still take ~12s warm, longer on a cold start — that is expected;
  do not retry on slowness.
- On tool error, surface the error text; do not fabricate a platform reply.
