# GCP MCP authentication patterns

Four ways to authenticate a Google Cloud MCP server in Claude Code, when each fits,
and exactly how to wire it. Read the section that matches the target environment.

## Contents
- [Why token expiry is the central problem](#why-token-expiry-is-the-central-problem)
- [Pattern A — headersHelper + gcloud user token (recommended for workstations/VMs)](#pattern-a)
- [Pattern B — headersHelper + Application Default Credentials](#pattern-b)
- [Pattern C — headersHelper + attached service account (headless/CI)](#pattern-c)
- [Pattern D — Claude Code built-in OAuth with a pre-registered client](#pattern-d)
- [Static header (why to avoid it)](#static-header)

---

## Why token expiry is the central problem

Google OAuth 2 access tokens are short-lived (~1 hour). Claude Code stores MCP request
headers **statically** in config — it does not re-run shell substitutions. So a token
baked in with `--header "Authorization: Bearer $(gcloud ...)"` stops working within the
hour. Every robust pattern below therefore refreshes the token at connection time
rather than storing it.

The mechanism that makes this clean is Claude Code's **`headersHelper`** (v2.1.193+): a
command Claude Code runs *fresh on every connection*, and *re-runs then retries once*
when a tool call returns 401/403. Its stdout must be a JSON object of headers, which
Claude Code merges into the request. That is the refresh hook.

---

<a name="pattern-a"></a>
## Pattern A — headersHelper + gcloud user token (recommended for workstations/VMs)

Best when a human is logged in via `gcloud auth login` and `gcloud auth print-access-token`
works. Reuses the existing login; zero OAuth-client setup.

`headersHelper` command: `scripts/gcp-mcp-headers.sh <QUOTA_PROJECT>` (see the script's
`--help`). It emits:

```json
{"Authorization":"Bearer <fresh token>","x-goog-user-project":"<QUOTA_PROJECT>"}
```

Config entry (user scope lives in `~/.claude.json` under top-level `mcpServers`):

```json
"developer-knowledge": {
  "type": "http",
  "url": "https://developerknowledge.googleapis.com/mcp",
  "headersHelper": "/home/<you>/.claude/mcp-helpers/developer-knowledge-headers.sh"
}
```

`claude mcp add` has **no `--headers-helper` flag**, so add the `headersHelper` field by
editing the config JSON (see SKILL.md step 4). Prefer a per-server wrapper script under
`~/.claude/mcp-helpers/` that calls `gcp-mcp-headers.sh` with the right project baked in,
so the config points at a stable path.

---

<a name="pattern-b"></a>
## Pattern B — headersHelper + Application Default Credentials

Use when ADC is configured (`gcloud auth application-default login`) but you don't want to
depend on the active gcloud user config. Set `GCP_MCP_USE_ADC=1` for `gcp-mcp-headers.sh`.
ADC tokens may need explicit scopes — pass `GCP_MCP_ADC_SCOPES` (the required scope is in
the endpoint's `.well-known/oauth-protected-resource`, surfaced by `probe_mcp.py`).

---

<a name="pattern-c"></a>
## Pattern C — headersHelper + attached service account (headless/CI)

On a GCE VM / Cloud Run / GKE with an attached service account, the metadata server
issues auto-refreshing tokens and `gcloud auth print-access-token` returns the SA token.
Same headersHelper as Pattern A. Ensure the SA has the IAM role/scope the API requires and
that the SA's project (or the passed quota project) has the API enabled. This is the right
choice when no human will be logged in where Claude Code runs.

---

<a name="pattern-d"></a>
## Pattern D — Claude Code built-in OAuth with a pre-registered client

Claude Code has a full OAuth 2.0 flow for remote MCP servers: it auto-discovers auth from
a `WWW-Authenticate` header / RFC 9728 `.well-known/oauth-protected-resource`, runs a
browser flow via `/mcp` → Authenticate, and stores + auto-refreshes tokens in the OS
keychain (not in config files).

The catch for Google: its authorization server (`https://accounts.google.com/`) does **not**
support Dynamic Client Registration (RFC 7591), which Claude Code's zero-config OAuth relies
on. You'll see: `Incompatible auth server: does not support dynamic client registration`.
To use OAuth anyway you must pre-register an OAuth 2.0 client (Desktop app) in the Google
Cloud Console for the project, put the endpoint's required scope on the consent screen, then:

```bash
claude mcp add --transport http --scope user \
  --client-id <GOOGLE_OAUTH_CLIENT_ID> --client-secret --callback-port 8080 \
  <name> <url>
```

`--callback-port` fixes the redirect URI (`http://localhost:PORT/callback`) so it can match
a pre-registered one. This is the most "hands-off" once set up, but the Console setup is
heavier and browser OAuth is awkward on headless hosts — which is why Pattern A/C is usually
preferred on Google endpoints.

---

<a name="static-header"></a>
## Static header (why to avoid it)

```bash
# Works for ~1 hour, then every tool call 401s. Use only for a one-off probe.
claude mcp add --transport http --scope user <name> <url> \
  --header "Authorization: Bearer $(gcloud auth print-access-token)" \
  --header "x-goog-user-project: <PROJECT>"
```

Acceptable to confirm connectivity, but never leave a "global" server configured this way —
migrate to a `headersHelper` (Pattern A–C).
