"""
platform_mcp.py - stdio MCP server bridging an MCP client directly to the
kube-agents platform agent via the Gemini Managed Agents Interactions API.

This is an alternative path to the A2A Cloud Run endpoint: it talks to the
Interactions API directly (no Cloud Run hop), authenticating with Application
Default Credentials.

Streaming narration: the agent's interaction is run with `stream:true` (SSE).
As the agent thinks and calls tools, each step is surfaced two ways:
  1. Live MCP progress notifications (`ctx.report_progress`) — the calling
     client (e.g. Claude Code) shows tool-call ticks while the agent runs.
  2. A full transcript (every text block, tool call, and tool result) is
     written once to GCS for audit/review — NOT real-time.
Only the agent's final reply text is returned as the tool result.

(Cloud Logging of narration is intentionally NOT done here — this is a local
stdio dev tool. Full-narration logging belongs on the A2A Cloud Run executor,
where the platform logger auto-collects to Cloud Logging.)

Warm sandbox: a single `environment_id` is shared across ALL access paths — this
MCP server, the A2A executor, and the Cloud Scheduler keep-warm heartbeat — by
storing it in one GCS object (`gs://<bucket>/<ENV_STATE_OBJECT>`). Every call
reuses it so the agent's sandbox stays warm; the heartbeat pings it on a sub-7-day
cadence so the environment's 7-day TTL never lapses and it never cold-starts.

Run:
    pip install -r requirements.txt
    gcloud auth application-default login   # provides ADC
    python servers/platform_mcp.py

Register with an MCP client (stdio), e.g. Claude Code:
    claude mcp add kube-platform -- python /abs/path/servers/platform_mcp.py

Env overrides (all optional, defaults target the kube-agents demo project):
    AGENT_PROJECT_ID    numeric project id    (default 111393542471)
    AGENT_ID            agent resource id     (default kube-platform)
    AGENT_LOCATION      agent location        (default global)
    GCS_BUCKET          env-id + transcript bucket (default managed-kube-agents-mslarkin-demo)
    ENV_STATE_OBJECT    env-id object path    (default data/platform/environment_id)
    TRANSCRIPT_PREFIX   transcript object dir (default data/platform/transcripts)
    TRANSCRIPTS_ENABLED set "0" to disable GCS transcript writes (default on)
"""

import asyncio
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import google.auth
import google.auth.transport.requests
from mcp.server.fastmcp import Context, FastMCP

PROJECT_ID = os.environ.get("AGENT_PROJECT_ID", "111393542471")
AGENT_ID = os.environ.get("AGENT_ID", "kube-platform")
AGENT_LOCATION = os.environ.get("AGENT_LOCATION", "global")
AGENT_RESOURCE = f"projects/{PROJECT_ID}/locations/{AGENT_LOCATION}/agents/{AGENT_ID}"

# Single source of truth for the shared warm-sandbox id — same GCS object the A2A
# executor and the keep-warm scheduler use, so every path warms one sandbox.
GCS_BUCKET = os.environ.get("GCS_BUCKET", "managed-kube-agents-mslarkin-demo")
ENV_STATE_OBJECT = os.environ.get("ENV_STATE_OBJECT", "data/platform/environment_id")
TRANSCRIPT_PREFIX = os.environ.get(
    "TRANSCRIPT_PREFIX", "data/platform/transcripts"
).strip("/")
TRANSCRIPTS_ENABLED = os.environ.get("TRANSCRIPTS_ENABLED", "1") != "0"

STREAM_TIMEOUT_S = 600  # hard cap on a single streamed interaction

_creds = None
_auth_request = google.auth.transport.requests.Request()

mcp = FastMCP("kube-platform")


def _get_token() -> str:
    global _creds
    if _creds is None:
        _creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    if not _creds.valid:
        _creds.refresh(_auth_request)
    return _creds.token


def _api_request(method: str, path: str, body: dict | None = None) -> dict:
    token = _get_token()
    url = (
        f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}"
        f"/locations/{AGENT_LOCATION}/{path}"
    )
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Interactions API HTTP {e.code}: {e.read().decode('utf-8')}"
        )


def _gcs_get(obj: str) -> str | None:
    """Read a GCS object's text via the JSON API. Returns None if absent/error."""
    enc = urllib.parse.quote(obj, safe="")
    url = f"https://storage.googleapis.com/storage/v1/b/{GCS_BUCKET}/o/{enc}?alt=media"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {_get_token()}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8").strip() or None
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"kube-agents: GCS get {obj} HTTP {e.code}", file=sys.stderr)
        return None
    except Exception as e:  # network etc. — non-fatal, just no cached env
        print(f"kube-agents: GCS get {obj} failed: {e}", file=sys.stderr)
        return None


def _gcs_put(obj: str, content: str, content_type: str = "text/plain") -> None:
    """Write a GCS object's text via the JSON API upload endpoint."""
    enc = urllib.parse.quote(obj, safe="")
    url = (
        f"https://storage.googleapis.com/upload/storage/v1/b/{GCS_BUCKET}"
        f"/o?uploadType=media&name={enc}"
    )
    req = urllib.request.Request(
        url,
        data=content.encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": content_type,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except Exception as e:  # non-fatal — reuse/audit degrades, doesn't break
        print(f"kube-agents: GCS put {obj} failed: {e}", file=sys.stderr)


def _gcs_delete(obj: str) -> bool:
    """Delete a GCS object. Returns True if deleted, False if it was absent."""
    enc = urllib.parse.quote(obj, safe="")
    url = f"https://storage.googleapis.com/storage/v1/b/{GCS_BUCKET}/o/{enc}"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {_get_token()}"}, method="DELETE"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise RuntimeError(f"GCS delete {obj} HTTP {e.code}")


def _load_env_id() -> str | None:
    return _gcs_get(ENV_STATE_OBJECT)


def _save_env_id(env_id: str) -> None:
    _gcs_put(ENV_STATE_OBJECT, env_id)


class _StreamCreateError(Exception):
    """The interaction failed to start (e.g. the warm env expired). Retryable
    once without the `environment` param."""


def _iter_sse(body: dict):
    """Open a streamed interaction and yield (event_type, payload) tuples.

    Raises _StreamCreateError if the create call is rejected outright (HTTP 4xx
    before any SSE event), which the caller may retry without the env param.
    """
    token = _get_token()
    url = (
        f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}"
        f"/locations/{AGENT_LOCATION}/interactions"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=STREAM_TIMEOUT_S)
    except urllib.error.HTTPError as e:
        raise _StreamCreateError(f"HTTP {e.code}: {e.read().decode('utf-8')}")

    event = None
    with resp:
        for raw in resp:
            line = raw.decode("utf-8").rstrip("\r\n")
            if not line:
                event = None  # SSE dispatch boundary
                continue
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    return
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue
                yield event, payload


def _accumulate(state: dict, event: str, payload: dict) -> str | None:
    """Fold one SSE event into the running transcript state. Returns a
    human-readable progress tick string when one is warranted, else None."""
    if event == "interaction.start":
        state["interaction_id"] = payload.get("interaction", {}).get("id", "")
        return "agent started"

    if event == "content.start":
        idx = payload.get("index")
        ctype = payload.get("content", {}).get("type", "")
        state["blocks"].setdefault(idx, {"type": ctype, "text_chunks": [], "full_text": None})
        return None

    if event == "content.delta":
        idx = payload.get("index")
        delta = payload.get("delta", {})
        block = state["blocks"].setdefault(
            idx, {"type": delta.get("type", ""), "text_chunks": [], "full_text": None}
        )
        dtype = delta.get("type", block.get("type"))

        if dtype == "text":
            # Incremental token chunks carry event_id; a single consolidated
            # delta repeats the whole block with no event_id — keep it as the
            # authoritative full text, dedup against the chunk stream.
            if payload.get("event_id"):
                block["text_chunks"].append(delta.get("text", ""))
            else:
                block["full_text"] = delta.get("text", "")
            return None

        if dtype == "function_call":
            block["type"] = "function_call"
            block["name"] = delta.get("name", "")
            args = delta.get("arguments", {}) or {}
            block["arguments"] = args
            block["tool_action"] = args.get("toolAction", "")
            block["tool_summary"] = args.get("toolSummary", "")
            block["explanation"] = args.get("explanation", "")
            tick = args.get("toolAction") or args.get("toolSummary") or block["name"]
            return f"{tick}" if tick else None

        if dtype == "function_result":
            block["type"] = "function_result"
            block["name"] = delta.get("name", "")
            block["call_id"] = delta.get("call_id", "")
            block["result"] = delta.get("result")
            return None

    if event == "interaction.complete":
        interaction = payload.get("interaction", {})
        state["status"] = interaction.get("status", "")
        state["usage"] = interaction.get("usage", {})
        state["environment_id"] = interaction.get("environment_id", "")
        if interaction.get("id"):
            state["interaction_id"] = interaction["id"]
        return "completed"

    return None


def _block_text(block: dict) -> str:
    if block.get("full_text") is not None:
        return block["full_text"]
    return "".join(block.get("text_chunks", []))


def _finalize(state: dict) -> tuple[str, list[dict]]:
    """Reduce accumulated blocks into (final_reply_text, ordered_steps)."""
    steps: list[dict] = []
    last_text = ""
    for idx in sorted(state["blocks"]):
        b = state["blocks"][idx]
        t = b.get("type")
        if t == "text":
            txt = _block_text(b)
            steps.append({"type": "text", "text": txt})
            if txt.strip():
                last_text = txt  # the agent's final reply is the last text block
        elif t == "function_call":
            steps.append(
                {
                    "type": "function_call",
                    "name": b.get("name", ""),
                    "tool_action": b.get("tool_action", ""),
                    "tool_summary": b.get("tool_summary", ""),
                    "explanation": b.get("explanation", ""),
                    "arguments": b.get("arguments", {}),
                }
            )
        elif t == "function_result":
            steps.append(
                {
                    "type": "function_result",
                    "name": b.get("name", ""),
                    "call_id": b.get("call_id", ""),
                    "result": b.get("result"),
                }
            )
    return last_text, steps


def _write_transcript(state: dict, prompt: str, prev_id: str | None,
                      steps: list[dict], final_text: str) -> str | None:
    """Persist the full interaction transcript to GCS for audit. Returns the
    object path written, or None if disabled/failed."""
    if not TRANSCRIPTS_ENABLED:
        return None
    iid = state.get("interaction_id") or "unknown"
    safe_iid = urllib.parse.quote(iid, safe="")
    day = time.strftime("%Y-%m-%d", time.gmtime(state["t_start"]))
    obj = f"{TRANSCRIPT_PREFIX}/{day}/{safe_iid}.json"
    transcript = {
        "interaction_id": iid,
        "previous_interaction_id": prev_id,
        "agent": AGENT_RESOURCE,
        "prompt": prompt,
        "status": state.get("status", ""),
        "environment_id": state.get("environment_id", ""),
        "usage": state.get("usage", {}),
        "tool_call_count": sum(1 for s in steps if s["type"] == "function_call"),
        "steps": steps,
        "final_text": final_text,
        "t_start_unix": round(state["t_start"], 3),
        "t_end_unix": round(state["t_end"], 3),
        "elapsed_s": round(state["t_end"] - state["t_start"], 2),
    }
    _gcs_put(obj, json.dumps(transcript, indent=2), "application/json")
    return obj


def _build_request(prompt: str, prev_id: str | None, env_id: str | None) -> dict:
    p: dict = {
        "agent": AGENT_RESOURCE,
        "input": prompt,
        "background": True,  # required by the API even when streaming
        "stream": True,
    }
    if prev_id:
        p["previous_interaction_id"] = prev_id
    if env_id:
        p["environment"] = env_id
    return p


async def _stream_interaction(
    prompt: str, prev_id: str | None, ctx: Context | None
) -> tuple[str, str, list[dict]]:
    """Run one streamed interaction to completion.

    Emits live progress ticks via ctx, accumulates the full transcript, persists
    it to GCS, and returns (final_text, interaction_id, steps). Retries once
    without the warm env if the stored environment has expired.
    """
    env_id = _load_env_id()
    attempts = [env_id, None] if env_id else [None]

    last_err: Exception | None = None
    for eid in attempts:
        state: dict = {
            "blocks": {},
            "interaction_id": "",
            "status": "",
            "usage": {},
            "environment_id": "",
            "t_start": time.time(),
        }
        body = _build_request(prompt, prev_id, eid)
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()

        def reader():
            try:
                for event, payload in _iter_sse(body):
                    loop.call_soon_threadsafe(q.put_nowait, (event, payload))
            except _StreamCreateError as e:
                loop.call_soon_threadsafe(q.put_nowait, ("__create_error__", str(e)))
            except Exception as e:  # mid-stream failure
                loop.call_soon_threadsafe(q.put_nowait, ("__error__", str(e)))
            finally:
                loop.call_soon_threadsafe(q.put_nowait, None)  # sentinel

        threading.Thread(target=reader, daemon=True).start()

        create_failed = False
        tick_n = 0
        while True:
            item = await q.get()
            if item is None:
                break
            event, payload = item
            if event == "__create_error__":
                create_failed = True
                last_err = _StreamCreateError(payload)
                continue
            if event == "__error__":
                last_err = RuntimeError(payload)
                continue
            tick = _accumulate(state, event, payload)
            if tick and ctx is not None:
                tick_n += 1
                try:
                    await ctx.report_progress(progress=tick_n, message=tick)
                except Exception:
                    pass  # progress is best-effort; never break the call

        if create_failed:
            # env likely expired — try next attempt (without env), if any
            continue

        state["t_end"] = time.time()
        final_text, steps = _finalize(state)

        # Persist a fresh env id for the next call across all paths.
        returned_env = state.get("environment_id", "")
        if returned_env and returned_env != env_id:
            _save_env_id(returned_env)

        obj = _write_transcript(state, prompt, prev_id, steps, final_text)
        if obj:
            print(f"kube-agents: transcript gs://{GCS_BUCKET}/{obj}", file=sys.stderr)

        return final_text, state.get("interaction_id", ""), steps

    raise RuntimeError(f"Interaction failed to start: {last_err}")


@mcp.tool()
async def ask_platform_agent(
    prompt: str,
    previous_interaction_id: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Send a prompt to the kube-agents platform agent and return its response.

    The platform agent orchestrates GKE clusters, operators, and devteam agents.
    Ask it about cluster status, deployments, governance, or operator tasks.

    The agent's reasoning and tool calls stream as live progress notifications
    while it works; a full transcript is archived to GCS for audit. Only the
    final reply is returned here.

    Args:
        prompt: Natural-language request for the platform agent.
        previous_interaction_id: Pass the `interaction_id` from a prior reply to
            continue that conversation (multi-turn history). Omit to start fresh.

    Returns:
        JSON string: {"text": <agent reply>, "interaction_id": <id for follow-up>}.
    """
    text, interaction_id, _ = await _stream_interaction(
        prompt, previous_interaction_id, ctx
    )
    return json.dumps({"text": text, "interaction_id": interaction_id})


@mcp.tool()
def reset_sandbox() -> str:
    """Forget the shared warm-sandbox environment id.

    Deletes the GCS env-id object. The next interaction (from ANY path — this
    server, A2A, or the keep-warm heartbeat) provisions a fresh sandbox (cold
    start, slower) and re-persists its id. Use if the sandbox state is corrupted.
    """
    if _gcs_delete(ENV_STATE_OBJECT):
        return (
            "Cleared shared environment id (gs://"
            f"{GCS_BUCKET}/{ENV_STATE_OBJECT}); next interaction cold-starts a "
            "fresh sandbox and re-persists it."
        )
    return "No persisted environment id to clear."


if __name__ == "__main__":
    mcp.run()
