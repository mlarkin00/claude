---
name: gcp-mcp-setup
description: Use when connecting Claude Code to a Google Cloud / googleapis MCP server (e.g. developerknowledge.googleapis.com, or any *.googleapis.com/mcp or Google Cloud remote MCP endpoint) and wiring up its authentication. Make sure to use this skill whenever the user wants to add, configure, scope (global/user vs project), or debug a GCP / Google MCP server in Claude Code, mentions a googleapis.com MCP URL, hits 401/403 or "missing authentication credential" / "quota project" / "API not enabled" / "dynamic client registration" errors from a Google MCP endpoint, or asks how to keep a gcloud-authenticated MCP server's token from expiring. Covers the bearer-token + x-goog-user-project pattern, enabling the backing API, and Claude Code's headersHelper for auto-refreshing tokens.
metadata:
  category: infra-ops
---

# Setting up Google Cloud MCP servers in Claude Code

Connect Claude Code to a Google Cloud / `googleapis.com` MCP endpoint with authentication
that keeps working. This is not the same as adding a typical public MCP server, and the
two surprises below are why a naive `claude mcp add` looks like it works and then fails:

1. **The handshake is public, but tool calls are not.** GCP MCP endpoints usually answer
   `initialize` and `tools/list` with no auth, so `claude mcp add` and a quick curl look
   fine — but `tools/call` returns 401 without a Google OAuth 2 bearer token **and** a
   quota-project header, and 403 until the backing API is enabled on that project.
2. **Access tokens expire in ~1 hour, and Claude Code stores headers statically.** A token
   baked into a header with `$(gcloud ...)` dies within the hour. The fix is Claude Code's
   `headersHelper`, which mints a fresh token on every connection.

Get the mental model right and the rest is mechanical.

## Prerequisites (verify first)

- **Claude Code ≥ 2.1.193** (`claude --version`) — needed for `headersHelper` with the
  401/403 re-run-and-retry behavior. Below that, the helper concept still exists but the
  auto-retry doesn't; warn the user.
- **gcloud authenticated**: `gcloud auth print-access-token` returns a token. (Or ADC / an
  attached service account — see `references/auth-patterns.md`.)
- **A quota/billing project** you can enable APIs on: `gcloud config get-value project`.
- The **endpoint URL** and its **backing service name**. Find both in Google's live
  directory — **https://docs.cloud.google.com/mcp/supported-products** — which is the
  authoritative, continuously-updated list of Google Cloud, Google, and Workspace MCP
  endpoints. Fetch it when the user names a product but not a URL (e.g. "the Cloud Run MCP
  server" → `https://run.googleapis.com/mcp`), or to confirm an endpoint exists. `config.json`
  keeps a tiny local cache for offline hints, but the live page wins.

  **Endpoint URL patterns (don't assume the naive form):** most are
  `https://<service>.googleapis.com/mcp`, so the backing service is the hostname and
  enabling it is `gcloud services enable <service>.googleapis.com`. But there are
  exceptions the live doc will show — e.g. Cloud Storage is `.../storage/mcp`, Workspace
  servers use `.../mcp/v1` (e.g. `gmailmcp.googleapis.com`), several are **regional**
  (`https://<service>.<REGION>.rep.googleapis.com/mcp` — substitute a real region), and
  Gemini Enterprise Agent Platform has per-toolset paths under `aiplatform.googleapis.com/mcp/...`.
  When the endpoint host doesn't map cleanly to the service to enable, check the product's
  page linked from the directory. `probe_mcp.py` reports the exact API to enable from the
  `api-not-enabled` diagnosis, so let it settle any ambiguity.

## Workflow

### 1. Probe the endpoint — measure the auth, don't guess it

```bash
scripts/probe_mcp.py <MCP_URL> --project <QUOTA_PROJECT>
```

It runs `initialize`, `tools/list`, and `tools/call` (unauthenticated, then with a gcloud
token), reads the `WWW-Authenticate` header and `.well-known/oauth-protected-resource`, and
prints a **diagnosis** (`auth-ok` / `needs-auth` / `needs-quota-project` / `api-not-enabled`
/ `google-oauth-no-dcr`) with next steps. This tells you exactly what to configure before
touching any config, and confirms the endpoint is reachable.

### 2. Choose a scope

- `--scope user` — **global**: available in all the user's projects. Use for a personal,
  broadly-useful server. Stored in `~/.claude.json`.
- `--scope project` — shared with a repo via `.mcp.json` (committed; teammates get it).
- `--scope local` — default; just this project, just this user.

"Add it globally / for all my projects" → `--scope user`.

### 3. Add the server

```bash
claude mcp add --scope user --transport http <name> <MCP_URL>
claude mcp list        # health check
```

At this point `initialize`/`tools/list` succeed, so it may show Connected — but tool calls
still need auth. Continue.

### 4. Wire up auth that refreshes itself (headersHelper)

This is the crux. `claude mcp add` has **no `--headers-helper` flag**, so set the field by
editing config. Prefer a small per-server wrapper script at a **stable path** so the config
points somewhere durable:

```bash
mkdir -p ~/.claude/mcp-helpers
cat > ~/.claude/mcp-helpers/<name>-headers.sh <<'EOF'
#!/usr/bin/env bash
exec "$HOME/.claude/skills/gcp-mcp-setup/scripts/gcp-mcp-headers.sh" "<QUOTA_PROJECT>"
EOF
chmod +x ~/.claude/mcp-helpers/<name>-headers.sh
# Sanity check: must print ONE JSON object of headers, nothing else on stdout.
~/.claude/mcp-helpers/<name>-headers.sh | python3 -c "import sys,json;print(sorted(json.load(sys.stdin)))"
```

Then swap the static entry for a `headersHelper` (back up config first). The user-scoped
entry lives under top-level `mcpServers` in `~/.claude.json`:

```python
python3 - <<'PY'
import json, os, shutil
cfg = os.path.expanduser('~/.claude.json'); shutil.copy(cfg, cfg + '.bak')
d = json.load(open(cfg))
e = d['mcpServers']['<name>']
e.pop('headers', None)
e['headersHelper'] = os.path.expanduser('~/.claude/mcp-helpers/<name>-headers.sh')
json.dump(d, open(cfg, 'w'), indent=2)
print(json.dumps(d['mcpServers']['<name>'], indent=2))
PY
```

Claude Code runs the helper fresh on every connection and, on a 401/403 from a tool call,
re-runs it and retries once — so the token never goes stale in the stored config. See
`references/auth-patterns.md` for ADC, service-account, and OAuth-client variants.

### 5. Enable the backing API on the quota project

```bash
gcloud services enable <service>.googleapis.com --project <QUOTA_PROJECT>
```

Skip this and tool calls 403 with *"...has not been used in project ... or it is disabled."*
Enablement can take ~a minute to propagate.

### 6. Verify end-to-end — exercise a real tool call, not just the handshake

The health check only does `initialize`/`tools/list`, which never needed auth — so it does
**not** prove the token path works. Drive an actual `tools/call`:

```bash
# Option A: through Claude Code (proves the whole config incl. headersHelper)
claude -p "Use the <name> MCP tool <tool> with <args>. Reply TOOL_OK + first result, or TOOL_ERR + the error." \
  --allowedTools "mcp__<name>__<tool>"

# Option B: re-run the probe; expect diagnosis: auth-ok
scripts/probe_mcp.py <MCP_URL> --project <QUOTA_PROJECT>
```

Then tell the user MCP tools load at **session start**, so they must restart Claude Code to
use the new tools in a fresh session.

## Reporting back

Summarize what was configured: server name, URL, scope, quota project, the API you enabled,
the helper script path, and the verified tool call. Call out the "restart to load tools"
step and any environment caveat (e.g. the helper needs gcloud creds present wherever Claude
Code runs — flag headless/service-account contexts).

## Reference files

- **Live endpoint directory** — https://docs.cloud.google.com/mcp/supported-products is the
  authoritative, continuously-updated list of every Google Cloud / Google / Workspace MCP
  endpoint. Fetch it to resolve a product name to a URL or confirm an endpoint exists;
  prefer it over any static list, including `config.json`.
- `references/auth-patterns.md` — the four auth patterns (gcloud user token, ADC, attached
  service account, pre-registered OAuth client) and when to use each. Read before choosing.
- `references/troubleshooting.md` — symptom → cause → fix table. Read when anything 401/403s
  or won't connect.
- `config.json` — defaults + a small offline cache of known GCP MCP servers. It is only a
  hint; the live directory above is canonical. Don't hardcode endpoints elsewhere.

## Gotchas & Anti-Patterns

| Excuse / assumption | Reality |
| --- | --- |
| "`claude mcp add` said Connected and curl of the endpoint worked, so auth is done." | The handshake is public. Only `tools/call` reveals the 401/403. Always verify with a real tool call (step 6). |
| "I'll just bake the token into the header with `$(gcloud auth print-access-token)`." | Claude Code stores headers statically; that token dies in ~1 hour. Use a `headersHelper` for anything you keep. |
| "The 401 says OAuth — I'll run Claude Code's OAuth flow." | Google's auth server has no Dynamic Client Registration, so zero-config OAuth fails. Prefer a headersHelper, or pre-register a client (`--client-id`). |
| "Bearer token alone should be enough." | User-credential tokens also need `x-goog-user-project` (quota project), or you get a "quota project not set" error. |
| "Auth is configured, so tool calls will work." | The backing `*.googleapis.com` API must be **enabled** on that project first, or every call 403s. |
| "A GET to the URL 405s — the server is broken." | Stateless streamable-HTTP GCP servers legitimately don't offer the SSE GET stream. POST JSON-RPC still works. |
| "The helper works when I run it, but the server won't connect." | gcloud may be off Claude Code's PATH, or the helper leaked a log line to stdout. stdout must be **only** the JSON; use an absolute gcloud path. |
| "Tools should show up right after I add the server." | MCP tools load at session start. Restart Claude Code. |
