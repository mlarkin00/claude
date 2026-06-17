#!/usr/bin/env bash
# Launches the kagent platform-agent stdio MCP server.
#
# If PLATFORM_AGENT_URL is not set (or is the default localhost:8080) and
# nothing is listening on that port, auto-starts kubectl port-forward in the
# background so Claude Code works without any manual setup.
#
# CRITICAL: stdout is the JSON-RPC channel for stdio MCP — all setup output
# MUST go to stderr (>&2). Never echo to stdout.
set -euo pipefail

ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REQ="${ROOT}/requirements.txt"
SERVER="${ROOT}/servers/platform_mcp.py"
VENV="${ROOT}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# ── Port-forward management ──────────────────────────────────────────────────

PLATFORM_AGENT_URL="${PLATFORM_AGENT_URL:-http://localhost:8080}"
PF_PID_FILE="/tmp/kagent-platform-pf.pid"
KAGENT_NAMESPACE="${KAGENT_NAMESPACE:-kagent}"
KAGENT_SERVICE="${KAGENT_SERVICE:-platform-agent}"
LOCAL_PORT=8080

# Extract host:port from URL for reachability check
url_reachable() {
  local url="$1"
  local host port
  host=$(echo "$url" | sed 's|http[s]*://||' | cut -d: -f1)
  port=$(echo "$url" | sed 's|http[s]*://||' | cut -d: -f2 | cut -d/ -f1)
  [[ -z "$port" ]] && port=80
  # nc with 1s timeout
  nc -z -w1 "$host" "$port" >/dev/null 2>&1
}

ensure_port_forward() {
  # Only auto-forward when URL is localhost (don't interfere with remote URLs)
  if ! echo "$PLATFORM_AGENT_URL" | grep -qE "localhost|127\.0\.0\.1"; then
    return 0
  fi

  if url_reachable "$PLATFORM_AGENT_URL"; then
    echo "kagent-kube-agents: platform-agent reachable at ${PLATFORM_AGENT_URL}" >&2
    return 0
  fi

  echo "kagent-kube-agents: starting kubectl port-forward svc/${KAGENT_SERVICE} ${LOCAL_PORT}:8080 -n ${KAGENT_NAMESPACE}" >&2

  # Kill any stale port-forward for this port
  if [[ -f "$PF_PID_FILE" ]]; then
    old_pid=$(cat "$PF_PID_FILE" 2>/dev/null || true)
    if [[ -n "$old_pid" ]]; then
      kill "$old_pid" 2>/dev/null || true
    fi
    rm -f "$PF_PID_FILE"
  fi

  kubectl port-forward \
    "svc/${KAGENT_SERVICE}" "${LOCAL_PORT}:8080" \
    -n "${KAGENT_NAMESPACE}" \
    >/dev/null 2>&1 &
  echo $! > "$PF_PID_FILE"

  # Wait up to 10s for the port to open
  for i in $(seq 1 20); do
    if url_reachable "$PLATFORM_AGENT_URL"; then
      echo "kagent-kube-agents: port-forward ready (pid $(cat "$PF_PID_FILE"))" >&2
      return 0
    fi
    sleep 0.5
  done

  echo "kagent-kube-agents: WARNING — port-forward did not become ready in 10s; proceeding anyway" >&2
}

ensure_port_forward

# ── Python dependency management ─────────────────────────────────────────────

deps_ok() { "$1" -c 'import mcp' >/dev/null 2>&1; }

# 1. System interpreter already satisfied
if deps_ok "${PYTHON_BIN}"; then
  exec "${PYTHON_BIN}" "${SERVER}"
fi

# 2. Reuse or create a venv
VPY="${VENV}/bin/python"
if [[ -x "${VPY}" ]] && deps_ok "${VPY}"; then
  exec "${VPY}" "${SERVER}"
fi
if [[ ! -x "${VPY}" ]]; then
  echo "kagent-kube-agents: creating venv at ${VENV}" >&2
  "${PYTHON_BIN}" -m venv "${VENV}" >&2 2>/tmp/kagent-venv.err || {
    echo "kagent-kube-agents: venv unavailable, falling back to --user install" >&2
    rm -rf "${VENV}"
  }
fi
if [[ -x "${VPY}" ]]; then
  echo "kagent-kube-agents: installing requirements into venv" >&2
  "${VPY}" -m pip install --quiet --upgrade pip >&2 || true
  "${VPY}" -m pip install --quiet -r "${REQ}" >&2
  exec "${VPY}" "${SERVER}"
fi

# 3. Last resort: --user install
echo "kagent-kube-agents: installing requirements with --user" >&2
"${PYTHON_BIN}" -m pip install --quiet --user -r "${REQ}" >&2 \
  || "${PYTHON_BIN}" -m pip install --quiet --user --break-system-packages -r "${REQ}" >&2
exec "${PYTHON_BIN}" "${SERVER}"
