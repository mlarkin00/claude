#!/usr/bin/env bash
# Run optimize_prompt.py inside a Docker container.
# Mounts gcloud ADC credentials so the container can authenticate.
#
# Usage:
#   bash scripts/run_docker.sh --detect-env
#   bash scripts/run_docker.sh --prompt "My prompt here"
#   bash scripts/run_docker.sh --prompt "..." --steering "Be concise" --project my-project
#   bash scripts/run_docker.sh --dry-run --prompt "test"
#   bash scripts/run_docker.sh --help
#
# Requirements: Docker must be installed and running.
# ADC path: ~/.config/gcloud is mounted read-only at /root/.config/gcloud inside the container.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="vertex-prompt-optimizer"

# Show help if requested (before build, so it's fast)
if [[ "$*" == *"--help"* ]]; then
  echo "Usage: bash run_docker.sh [args passed to optimize_prompt.py]"
  echo ""
  echo "Builds (once) and runs optimize_prompt.py in a Docker container."
  echo "Mounts ~/.config/gcloud for Application Default Credentials."
  echo ""
  echo "optimize_prompt.py flags:"
  docker run --rm "$IMAGE_NAME" --help 2>/dev/null || true
  exit 0
fi

# --detect-env must run on the host — gcloud is not inside the container.
if [[ "$*" == *"--detect-env"* ]]; then
  python3 "$SCRIPT_DIR/optimize_prompt.py" --detect-env
  exit $?
fi

# Verify Docker is available
if ! command -v docker &>/dev/null; then
  echo "ERROR: Docker is not installed or not on PATH." >&2
  echo "Install Docker: https://docs.docker.com/get-docker/" >&2
  exit 1
fi

if ! docker info &>/dev/null; then
  echo "ERROR: Docker daemon is not running. Start Docker and retry." >&2
  exit 1
fi

# Build the image if it doesn't exist or if the Dockerfile/script changed
NEEDS_BUILD=false
if ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
  NEEDS_BUILD=true
fi

if [[ "$NEEDS_BUILD" == "true" ]]; then
  echo "Building Docker image '$IMAGE_NAME'..." >&2
  docker build -t "$IMAGE_NAME" -f "$SKILL_DIR/docker/Dockerfile" "$SCRIPT_DIR" >&2
  echo "Build complete." >&2
fi

# Resolve ADC path (Linux/macOS)
ADC_DIR="${CLOUDSDK_CONFIG:-$HOME/.config/gcloud}"

if [[ ! -d "$ADC_DIR" ]]; then
  echo "WARNING: gcloud config directory not found at $ADC_DIR." >&2
  echo "Run: gcloud auth application-default login" >&2
fi

# Rebuild image if optimize_prompt.py has changed since last build
IMAGE_CREATED=$(docker inspect --format='{{.Created}}' "$IMAGE_NAME" 2>/dev/null || echo "")
SCRIPT_MTIME=$(date -r "$SCRIPT_DIR/optimize_prompt.py" +%s 2>/dev/null || echo "0")
IMAGE_TS=$(date -d "$IMAGE_CREATED" +%s 2>/dev/null || echo "9999999999")
if [[ "$SCRIPT_MTIME" -gt "$IMAGE_TS" ]]; then
  echo "optimize_prompt.py changed since last build — rebuilding image..." >&2
  docker build -t "$IMAGE_NAME" -f "$SKILL_DIR/docker/Dockerfile" "$SCRIPT_DIR" >&2
fi

# Handle --prompt-file: copy to a temp file, mount it, rewrite the arg to the container path.
EXTRA_MOUNTS=()
REWRITTEN_ARGS=()
SKIP_NEXT=false
for arg in "$@"; do
  if [[ "$SKIP_NEXT" == "true" ]]; then
    HOST_PROMPT_FILE="$arg"
    CONTAINER_PROMPT_PATH="/tmp/prompt_input.txt"
    cp "$HOST_PROMPT_FILE" /tmp/prompt_input_host.txt
    EXTRA_MOUNTS=(-v "/tmp/prompt_input_host.txt:$CONTAINER_PROMPT_PATH:ro")
    REWRITTEN_ARGS+=("$CONTAINER_PROMPT_PATH")
    SKIP_NEXT=false
  elif [[ "$arg" == "--prompt-file" ]]; then
    REWRITTEN_ARGS+=("$arg")
    SKIP_NEXT=true
  else
    REWRITTEN_ARGS+=("$arg")
  fi
done

# Run the container
# Status/errors go to stderr; JSON output goes to stdout — same contract as the raw script.
docker run --rm \
  -v "$ADC_DIR:/root/.config/gcloud:ro" \
  "${EXTRA_MOUNTS[@]}" \
  "$IMAGE_NAME" \
  "${REWRITTEN_ARGS[@]}"
