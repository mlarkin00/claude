# GCP MCP troubleshooting

Map an observed symptom to its cause and fix. Most confusion comes from the fact that a
GCP MCP endpoint answers the handshake happily while silently requiring more for real
tool calls — so `claude mcp list` can show a server as needing auth even though `curl` of
`initialize` returned 200.

## Symptom → cause → fix

| Symptom (what you see) | Cause | Fix |
| --- | --- | --- |
| `claude mcp list` shows **✘ Failed to connect**, but curl of `initialize` returns 200 | Claude Code discovered the OAuth challenge (via `WWW-Authenticate` / `.well-known`) and can't complete it, OR no working auth headers are configured yet | Configure a `headersHelper` (auth-patterns Pattern A). Re-check with `claude mcp list`. |
| Tool call error: *"Request is missing required authentication credential. Expected OAuth 2 access token"* (HTTP 401) | No `Authorization` header reached the tool call (handshake is public, tool calls aren't) | Add a bearer token via `headersHelper`. |
| Tool call error: *"...requires a quota project, which is not set by default"* | Missing `x-goog-user-project` header (user-credential ADC needs an explicit quota/billing project) | Add `x-goog-user-project: <PROJECT>` (the headersHelper does this). |
| Tool call error: *"<API> has not been used in project <P> before or it is disabled"* (403) | The backing API isn't enabled on the quota project | `gcloud services enable <service>.googleapis.com --project <P>`, wait ~1 min, retry. |
| `Incompatible auth server: does not support dynamic client registration` | Tried Claude Code's zero-config OAuth against Google (`accounts.google.com`), which lacks DCR | Use a `headersHelper` (Pattern A–C) or pre-register an OAuth client (Pattern D). |
| Worked for ~an hour, now every tool call 401s | A **static** bearer token header expired | Replace the static header with a `headersHelper` so the token refreshes per connection. |
| headersHelper server won't connect; helper works when you run it by hand | `gcloud` not on the PATH Claude Code uses, or the helper prints non-JSON (e.g. a log line) to **stdout** | Use an absolute `gcloud` path (`GCLOUD_BIN`); send all diagnostics to **stderr** — stdout must be only the JSON object. |
| GET to the `/mcp` URL returns **405** | Expected — many GCP MCP servers are stateless streamable-HTTP and don't offer the optional SSE GET stream. Not an error | Ignore; POST-based JSON-RPC still works. |
| `initialize` intermittently returns 401 with an HTML body | Transient gateway blip / unsupported protocol version bounce | Retry; pin `protocolVersion` to a known-good value (e.g. `2025-06-18`). |
| Tools don't appear in the current session even though `claude mcp list` says Connected | MCP tools load at session start | Restart Claude Code; tools appear in a new session. |

## Fast diagnosis

Run the probe — it reproduces the whole chain and prints a diagnosis + next steps:

```bash
scripts/probe_mcp.py <MCP_URL> --project <QUOTA_PROJECT>
```

Diagnosis codes it can emit: `auth-ok`, `needs-auth`, `needs-quota-project`,
`api-not-enabled`, `google-oauth-no-dcr`.

## Useful checks

```bash
claude --version                         # need >= 2.1.193 for headersHelper auto-retry
gcloud auth print-access-token >/dev/null && echo OK   # is a token obtainable?
gcloud config get-value project          # default quota project
claude mcp get <name>                    # scope + connection status
gcloud services list --enabled --project <P> | grep <service>   # is the API on?
```
