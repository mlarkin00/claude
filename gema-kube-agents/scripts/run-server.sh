#!/usr/bin/env bash
# Launches the kube-platform stdio MCP server, ensuring its Python deps exist.
#
# Strategy (most-to-least preferred), so it works whether or not the host has
# python3-venv / a writable system site-packages:
#   1. If the chosen interpreter already imports the deps -> use it as-is.
#   2. Else try a dedicated venv (clean isolation) and install into it.
#   3. Else fall back to a --user install into the chosen interpreter.
#
# CRITICAL: stdout is the JSON-RPC channel for stdio MCP — every setup/log line
# MUST go to stderr (>&2). Never echo to stdout here.
set -euo pipefail

ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REQ="${ROOT}/requirements.txt"
SERVER="${ROOT}/servers/platform_mcp.py"
VENV="${ROOT}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

deps_ok() { "$1" -c 'import mcp, google.auth' >/dev/null 2>&1; }

# 1. Interpreter already satisfied (system install, prior --user install, etc.).
if deps_ok "${PYTHON_BIN}"; then
  exec "${PYTHON_BIN}" "${SERVER}"
fi

# 2. Reuse or build a dedicated venv.
VPY="${VENV}/bin/python"
if [[ -x "${VPY}" ]] && deps_ok "${VPY}"; then
  exec "${VPY}" "${SERVER}"
fi
if [[ ! -x "${VPY}" ]]; then
  echo "kube-agents: creating venv at ${VENV}" >&2
  "${PYTHON_BIN}" -m venv "${VENV}" >&2 2>/tmp/kube-agents-venv.err || {
    echo "kube-agents: venv unavailable, falling back to --user install" >&2
    rm -rf "${VENV}"
  }
fi
if [[ -x "${VPY}" ]]; then
  echo "kube-agents: installing requirements into venv" >&2
  "${VPY}" -m pip install --quiet --upgrade pip >&2 || true
  "${VPY}" -m pip install --quiet -r "${REQ}" >&2
  exec "${VPY}" "${SERVER}"
fi

# 3. Last resort: --user install into the system interpreter.
echo "kube-agents: installing requirements with --user" >&2
"${PYTHON_BIN}" -m pip install --quiet --user -r "${REQ}" >&2 \
  || "${PYTHON_BIN}" -m pip install --quiet --user --break-system-packages -r "${REQ}" >&2
exec "${PYTHON_BIN}" "${SERVER}"
