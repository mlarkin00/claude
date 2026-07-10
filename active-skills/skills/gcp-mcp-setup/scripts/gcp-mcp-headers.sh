#!/usr/bin/env bash
#
# gcp-mcp-headers.sh — a Claude Code `headersHelper` for Google Cloud MCP servers.
#
# Claude Code runs a headersHelper fresh on every connection (and again when a tool
# call returns 401/403, then retries once — v2.1.193+). It reads the JSON object this
# script prints on stdout and merges it into the request headers. That is how a short-
# lived gcloud token stays fresh without ever being written into the stored config.
#
# It emits:
#   {"Authorization":"Bearer <token>","x-goog-user-project":"<project>"}
#
# The quota project is resolved from, in order:
#   1. $1 (first argument)
#   2. $GCP_MCP_QUOTA_PROJECT
#   3. `gcloud config get-value project`
#
# The token comes from `gcloud auth print-access-token` (user credentials) by default.
# Set GCP_MCP_USE_ADC=1 to use Application Default Credentials instead; combine with
# GCP_MCP_ADC_SCOPES to request specific scopes for ADC.
#
# IMPORTANT: stdout must contain ONLY the JSON object. All diagnostics go to stderr.
#
# Usage:
#   gcp-mcp-headers.sh [QUOTA_PROJECT]
#   gcp-mcp-headers.sh --help
#
# Examples:
#   gcp-mcp-headers.sh agentic-ops-dev
#   GCP_MCP_QUOTA_PROJECT=my-proj gcp-mcp-headers.sh
#   GCP_MCP_USE_ADC=1 GCP_MCP_ADC_SCOPES="https://www.googleapis.com/auth/cloud-platform" gcp-mcp-headers.sh my-proj
#
set -euo pipefail

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  sed -n '2,33p' "$0" >&2
  exit 0
fi

GCLOUD="${GCLOUD_BIN:-$(command -v gcloud || true)}"
if [[ -z "${GCLOUD}" ]]; then
  echo "gcp-mcp-headers: gcloud not found on PATH; set GCLOUD_BIN" >&2
  printf '{}'
  exit 0
fi

# --- resolve quota project ---------------------------------------------------
QUOTA_PROJECT="${1:-${GCP_MCP_QUOTA_PROJECT:-}}"
if [[ -z "${QUOTA_PROJECT}" ]]; then
  QUOTA_PROJECT="$("${GCLOUD}" config get-value project 2>/dev/null || true)"
fi

# --- mint a fresh access token ----------------------------------------------
if [[ "${GCP_MCP_USE_ADC:-0}" == "1" ]]; then
  if [[ -n "${GCP_MCP_ADC_SCOPES:-}" ]]; then
    TOKEN="$("${GCLOUD}" auth application-default print-access-token --scopes="${GCP_MCP_ADC_SCOPES}" 2>/dev/null || true)"
  else
    TOKEN="$("${GCLOUD}" auth application-default print-access-token 2>/dev/null || true)"
  fi
else
  TOKEN="$("${GCLOUD}" auth print-access-token 2>/dev/null || true)"
fi

if [[ -z "${TOKEN}" ]]; then
  echo "gcp-mcp-headers: could not obtain an access token (is gcloud logged in?)" >&2
  # Emit valid-but-empty JSON so Claude Code surfaces the resulting 401 clearly.
  printf '{}'
  exit 0
fi

# --- emit headers ------------------------------------------------------------
if [[ -n "${QUOTA_PROJECT}" ]]; then
  printf '{"Authorization":"Bearer %s","x-goog-user-project":"%s"}' "${TOKEN}" "${QUOTA_PROJECT}"
else
  echo "gcp-mcp-headers: no quota project resolved; omitting x-goog-user-project" >&2
  printf '{"Authorization":"Bearer %s"}' "${TOKEN}"
fi
