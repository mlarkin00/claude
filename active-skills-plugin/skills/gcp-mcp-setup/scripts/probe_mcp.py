#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Probe a Google Cloud MCP endpoint to discover exactly what auth it needs.

Do not guess a GCP MCP server's auth requirements — measure them. GCP MCP
endpoints commonly serve the `initialize` and `tools/list` handshake publicly but
require a Google OAuth 2 bearer token AND a quota-project header for real
`tools/call` requests, and additionally require the backing API to be enabled on
that project. This script runs each step and reports which requirement bites.

It performs (stdlib only, no external deps):
  1. initialize            (no auth)
  2. tools/list            (no auth)   -> lists tool names
  3. tools/call            (no auth)   -> expects 401 + WWW-Authenticate
  4. tools/call            (with token, if available) -> detects quota-project /
                                          API-not-enabled / success
  5. GET .well-known/oauth-protected-resource (from WWW-Authenticate) -> OAuth
                                          authorization server + scopes

Diagnostics + a human-readable report go to stderr; a JSON summary goes to stdout.

Usage:
  probe_mcp.py <MCP_URL> [--project QUOTA_PROJECT] [--token ACCESS_TOKEN] [--no-gcloud]

Examples:
  probe_mcp.py https://developerknowledge.googleapis.com/mcp
  probe_mcp.py https://developerknowledge.googleapis.com/mcp --project agentic-ops-dev
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

ACCEPT = "application/json, text/event-stream"


def eprint(*a):
    print(*a, file=sys.stderr)


def rpc(url, body, token=None, project=None, method="POST"):
    """Return (status, headers_dict, parsed_or_text). Never raises on HTTP error."""
    headers = {"content-type": "application/json", "accept": ACCEPT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if project:
        headers["x-goog-user-project"] = project
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8", "replace")
            hdrs = {k.lower(): v for k, v in r.headers.items()}
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        hdrs = {k.lower(): v for k, v in (e.headers or {}).items()}
        status = e.code
    except Exception as e:  # network/DNS/timeout
        return None, {}, f"request failed: {e}"
    try:
        return status, hdrs, json.loads(raw)
    except json.JSONDecodeError:
        return status, hdrs, raw


def gcloud_token():
    try:
        out = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except Exception:
        pass
    return None


def result_is_error(parsed):
    """A JSON-RPC tools/call result can be 200 but carry isError=true in the body."""
    if isinstance(parsed, dict):
        res = parsed.get("result")
        if isinstance(res, dict) and res.get("isError"):
            texts = [c.get("text", "") for c in res.get("content", []) if isinstance(c, dict)]
            return " ".join(texts)
    return None


def main():
    ap = argparse.ArgumentParser(description="Probe a GCP MCP endpoint's auth requirements.")
    ap.add_argument("url", help="MCP endpoint URL, e.g. https://<svc>.googleapis.com/mcp")
    ap.add_argument("--project", help="quota project for x-goog-user-project header")
    ap.add_argument("--token", help="OAuth access token (else tries gcloud)")
    ap.add_argument("--no-gcloud", action="store_true", help="do not auto-fetch a gcloud token")
    args = ap.parse_args()

    summary = {"url": args.url, "steps": {}, "diagnosis": [], "next_steps": []}

    # 1. initialize (no auth)
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "probe", "version": "0"}}}
    st, hd, pr = rpc(args.url, init)
    server = pr.get("result", {}).get("serverInfo", {}) if isinstance(pr, dict) else {}
    summary["steps"]["initialize_no_auth"] = {"status": st, "serverInfo": server}
    eprint(f"[1] initialize (no auth): HTTP {st}  server={server.get('name','?')}")

    # 2. tools/list (no auth)
    st, hd, pr = rpc(args.url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = []
    if isinstance(pr, dict):
        tools = [t.get("name") for t in pr.get("result", {}).get("tools", [])]
    summary["steps"]["tools_list_no_auth"] = {"status": st, "tools": tools}
    eprint(f"[2] tools/list (no auth): HTTP {st}  tools={tools or '(none / auth required)'}")

    # 3. tools/call (no auth) -> discover the auth challenge
    www_auth = None
    if tools:
        call = {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": tools[0], "arguments": {}}}
        st, hd, pr = rpc(args.url, call)
        www_auth = hd.get("www-authenticate")
        body_err = result_is_error(pr)
        summary["steps"]["tools_call_no_auth"] = {
            "status": st, "www_authenticate": www_auth, "body_error": body_err}
        eprint(f"[3] tools/call (no auth): HTTP {st}  www-authenticate={www_auth or '(none)'}")
        if body_err:
            eprint(f"    body error: {body_err[:160]}")
    else:
        eprint("[3] tools/call skipped (no tools listed without auth)")

    # 4. tools/call (with token)
    token = args.token or (None if args.no_gcloud else gcloud_token())
    if tools and token:
        call = {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                "params": {"name": tools[0], "arguments": {}}}
        st, hd, pr = rpc(args.url, call, token=token, project=args.project)
        body_err = result_is_error(pr)
        summary["steps"]["tools_call_with_token"] = {
            "status": st, "project": args.project, "body_error": body_err}
        eprint(f"[4] tools/call (token{', project='+args.project if args.project else ''}): "
               f"HTTP {st}")
        low = (body_err or "").lower()
        auth_blocked = False
        if body_err:
            eprint(f"    body error: {body_err[:200]}")
            if "quota project" in low:
                auth_blocked = True
                summary["diagnosis"].append("needs-quota-project")
                summary["next_steps"].append(
                    "Add header x-goog-user-project: <PROJECT> (pass --project or set it in the headersHelper).")
            if "has not been used" in low or "is disabled" in low or "enable it" in low:
                auth_blocked = True
                summary["diagnosis"].append("api-not-enabled")
                host = urlparse(args.url).hostname or ""
                svc = host if host.endswith("googleapis.com") else "<service>.googleapis.com"
                summary["next_steps"].append(
                    f"Enable the backing API: gcloud services enable {svc} --project <PROJECT>")
            if ("missing required authentication" in low or "unauthenticated" in low
                    or "expected oauth" in low or "permission denied" in low
                    or "caller does not have permission" in low):
                auth_blocked = True
                summary["diagnosis"].append("needs-auth")
        if not auth_blocked:
            # Reached the tool itself (a 200 with no error, or a non-auth error such as
            # "invalid argument" from empty probe args) => authentication is satisfied.
            summary["diagnosis"].append("auth-ok")
            eprint("    OK: authentication satisfied (reached tool logic).")
    elif tools and not token:
        eprint("[4] tools/call (with token) skipped: no token available.")
        summary["next_steps"].append(
            "Provide a token (gcloud auth print-access-token) or --token to test the authed path.")

    # 5. OAuth metadata discovery
    if www_auth and "resource_metadata=" in www_auth:
        meta_url = www_auth.split('resource_metadata="', 1)[1].split('"', 1)[0]
        st, hd, pr = rpc(meta_url, None, method="GET")
        if isinstance(pr, dict):
            summary["steps"]["oauth_protected_resource"] = pr
            eprint(f"[5] OAuth metadata: auth_servers={pr.get('authorization_servers')} "
                   f"scopes={pr.get('scopes_supported')}")
            if any("accounts.google.com" in s for s in pr.get("authorization_servers", [])):
                summary["diagnosis"].append("google-oauth-no-dcr")
                summary["next_steps"].append(
                    "Authorization server is Google (no Dynamic Client Registration). Prefer a "
                    "headersHelper with a gcloud token over Claude Code's zero-config OAuth flow.")

    # Report
    eprint("\n=== DIAGNOSIS ===")
    for d in summary["diagnosis"] or ["(none)"]:
        eprint(f"  - {d}")
    eprint("=== NEXT STEPS ===")
    for n in summary["next_steps"] or ["Looks ready; add the server and wire up the headersHelper."]:
        eprint(f"  - {n}")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
