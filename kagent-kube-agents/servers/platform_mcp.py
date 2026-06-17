"""
platform_mcp.py — stdio MCP server for the kagent platform-agent.

Exposes two tools:
  ask_platform_agent(query)               — one-shot message, fresh context
  ask_platform_agent_in_session(query,    — continue an existing A2A session
      context_id, task_id)

Transport: A2A JSON-RPC (message/send) at PLATFORM_AGENT_URL.
Default URL: http://localhost:8080 (run-server.sh auto-starts port-forward).

Register with Claude Code:
    claude mcp add kagent-platform -- /path/to/scripts/run-server.sh
Or install the plugin:
    claude plugin install /path/to/kagent-kube-agents

Env overrides:
    PLATFORM_AGENT_URL   full URL of the A2A endpoint  (default http://localhost:8080)
    A2A_TIMEOUT          request timeout in seconds     (default 300)
"""

import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

PLATFORM_AGENT_URL = os.environ.get("PLATFORM_AGENT_URL", "http://localhost:8080").rstrip("/")
A2A_TIMEOUT = int(os.environ.get("A2A_TIMEOUT", "300"))

mcp = FastMCP("kagent-platform")


def _send(message: dict[str, Any]) -> dict[str, Any]:
    """Send a JSON-RPC message/send request and return the result dict."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {"message": message},
    }).encode()

    req = urllib.request.Request(
        PLATFORM_AGENT_URL + "/",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=A2A_TIMEOUT) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"A2A HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach platform-agent at {PLATFORM_AGENT_URL}: {exc.reason}\n"
            "Check that kubectl port-forward is running or set PLATFORM_AGENT_URL."
        ) from exc

    if "error" in body:
        raise RuntimeError(f"A2A error: {body['error']}")
    return body["result"]


def _extract_text(result: dict[str, Any]) -> str:
    """Pull the first text part from the agent's artifact."""
    artifacts = result.get("artifacts", [])
    if not artifacts:
        return "(no response)"
    parts = artifacts[0].get("parts", [])
    for part in parts:
        if part.get("kind") == "text":
            return part["text"]
    return "(non-text response)"


@mcp.tool()
def ask_platform_agent(query: str) -> str:
    """
    Send a message to the kagent platform-agent and return its response.

    The platform-agent manages a GKE fleet: it provisions/deprovisions operator
    and devteam agents, runs fleet-wide health checks, and routes requests to
    the appropriate cluster or namespace agent.

    Examples:
      - "List all registered operator agents"
      - "Provision an operator agent for cluster agent-cluster in us-west1"
      - "Check the health of all registered clusters"
      - "Which devteam agents are managing the default namespace?"
    """
    message = {
        "messageId": str(uuid.uuid4()),
        "role": "user",
        "parts": [{"kind": "text", "text": query}],
    }
    result = _send(message)
    return _extract_text(result)


@mcp.tool()
def ask_platform_agent_in_session(query: str, context_id: str, task_id: str) -> str:
    """
    Continue a conversation with the kagent platform-agent in an existing session.

    Use this after ask_platform_agent returns a contextId/taskId in the metadata,
    or when you want to follow up on a previous query in the same context.

    Args:
        query:      The follow-up message to send.
        context_id: The contextId from a previous ask_platform_agent response.
        task_id:    The taskId from a previous ask_platform_agent response.
    """
    message = {
        "messageId": str(uuid.uuid4()),
        "role": "user",
        "parts": [{"kind": "text", "text": query}],
        "contextId": context_id,
        "taskId": task_id,
    }
    result = _send(message)
    return _extract_text(result)


@mcp.tool()
def get_platform_agent_info() -> str:
    """
    Fetch the platform-agent's A2A agent card (capabilities, skills, endpoint).

    Returns the raw JSON of the agent card from /.well-known/agent-card.json.
    Useful for confirming connectivity and checking what the agent advertises.
    """
    url = PLATFORM_AGENT_URL + "/.well-known/agent-card.json"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            card = json.loads(resp.read())
        return json.dumps(card, indent=2)
    except urllib.error.URLError as exc:
        return (
            f"Cannot reach platform-agent at {PLATFORM_AGENT_URL}: {exc.reason}\n"
            "Check that kubectl port-forward is running or set PLATFORM_AGENT_URL."
        )


if __name__ == "__main__":
    mcp.run(transport="stdio")
