#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "google-cloud-aiplatform>=1.87.0",
# ]
# ///
"""
Vertex AI Prompt Optimizer — zero-shot interactive runner.

Usage:
  python optimize_prompt.py --detect-env
  python optimize_prompt.py --prompt "Tell me about black holes."
  python optimize_prompt.py --prompt "..." --steering "Be more concise"
  python optimize_prompt.py --project my-project --location us-east4 --prompt "..."
  python optimize_prompt.py --prompt "..." --dry-run
  python optimize_prompt.py --help

Auto-detection: --project and --location are resolved from gcloud config if omitted.
Output (stdout): JSON
Errors (stderr): human-readable diagnostics
"""

import argparse
import difflib
import json
import subprocess
import sys


# ---------------------------------------------------------------------------
# gcloud environment detection
# ---------------------------------------------------------------------------

def _gcloud(args: list[str]) -> str:
    """Run a gcloud command and return stripped stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["gcloud"] + args,
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""


def detect_env() -> dict:
    """Probe the local gcloud config and ADC status."""
    project = _gcloud(["config", "get-value", "project"])
    region = _gcloud(["config", "get-value", "compute/region"])
    account = _gcloud(["config", "get-value", "core/account"])

    # ADC check: gcloud auth application-default print-access-token exits 0 if valid
    try:
        adc_result = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            capture_output=True, text=True, timeout=15
        )
        adc_valid = adc_result.returncode == 0
    except Exception:
        adc_valid = False

    return {
        "project": project or None,
        "location": region or None,
        "account": account or None,
        "adc_valid": adc_valid,
        "warnings": _build_warnings(project, region, adc_valid),
    }


def _build_warnings(project: str, region: str, adc_valid: bool) -> list[str]:
    warnings = []
    if not project:
        warnings.append("No active project detected. Pass --project or run: gcloud config set project PROJECT_ID")
    if not region:
        warnings.append("No compute/region detected. Will default to us-central1. Pass --location to override.")
    if not adc_valid:
        warnings.append("Application Default Credentials not found. Run: gcloud auth application-default login")
    return warnings


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Vertex AI Prompt Optimizer (zero-shot) and output JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--detect-env",
        action="store_true",
        help="Probe local gcloud config and print detected environment as JSON, then exit",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="GCP project ID (auto-detected from gcloud config if omitted)",
    )
    parser.add_argument(
        "--location",
        default=None,
        help="GCP region (auto-detected from gcloud compute/region; fallback: us-central1)",
    )
    parser.add_argument("--prompt", default=None, help="The prompt to optimize (inline string)")
    parser.add_argument("--prompt-file", default=None, help="Path to a file containing the prompt (preferred for large/multi-line prompts)")
    parser.add_argument(
        "--steering",
        default="",
        help="Semicolon-separated steering hints from prior iterations",
    )
    parser.add_argument(
        "--task-description",
        default="",
        help="Optional description of what the prompt is trying to accomplish",
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=1,
        help="Current iteration number (for output metadata, default: 1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the payload that would be sent without calling the API",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_optimization_prompt(prompt: str, steering: str, task_description: str) -> str:
    parts = [prompt]
    if task_description:
        parts.append(f"\n\n[Task context: {task_description}]")
    if steering:
        hints = [h.strip() for h in steering.split(";") if h.strip()]
        if hints:
            parts.append(f"\n\n[Optimization constraints: {'; '.join(hints)}]")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------

def resolve_project_and_location(args: argparse.Namespace) -> tuple[str, str]:
    """Return (project, location), filling gaps from gcloud config."""
    env = detect_env()

    project = args.project or env.get("project")
    location = args.location or env.get("location") or "us-central1"

    if not project:
        print(
            "ERROR: No GCP project found. Pass --project or run: "
            "gcloud config set project PROJECT_ID",
            file=sys.stderr,
        )
        sys.exit(1)

    return project, location


def run_optimizer(args: argparse.Namespace) -> dict:
    project, location = resolve_project_and_location(args)

    if args.prompt_file:
        try:
            with open(args.prompt_file) as f:
                args.prompt = f.read()
        except OSError as exc:
            print(f"ERROR: Cannot read --prompt-file: {exc}", file=sys.stderr)
            sys.exit(1)

    if not args.prompt:
        print("ERROR: --prompt or --prompt-file is required when not using --detect-env.", file=sys.stderr)
        sys.exit(1)

    effective_prompt = build_optimization_prompt(
        args.prompt, args.steering, args.task_description
    )

    if args.dry_run:
        print(json.dumps({
            "dry_run": True,
            "project": project,
            "location": location,
            "effective_prompt": effective_prompt,
        }, indent=2))
        sys.exit(0)

    try:
        import vertexai
    except ImportError:
        print(
            "ERROR: google-cloud-aiplatform is not installed.\n"
            "Run: pip install google-cloud-aiplatform>=1.87.0",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        client = vertexai.Client(project=project, location=location)
    except Exception as exc:
        print(f"ERROR: Failed to initialize Vertex AI client: {exc}", file=sys.stderr)
        print("Hint: Run `gcloud auth application-default login` to authenticate.", file=sys.stderr)
        sys.exit(1)

    try:
        response = client.prompt_optimizer.optimize_prompt(
            prompt=effective_prompt,
        )
    except Exception as exc:
        msg = str(exc)
        print(f"ERROR: Vertex AI API call failed: {msg}", file=sys.stderr)
        if "PERMISSION_DENIED" in msg or "403" in msg:
            print(
                "Hint: Ensure the Vertex AI API is enabled and your account has roles/aiplatform.user.",
                file=sys.stderr,
            )
        elif "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            print("Hint: Quota exceeded. Wait and retry.", file=sys.stderr)
        sys.exit(1)

    suggested = None
    metadata = {}
    try:
        if response.parsed_response and hasattr(response.parsed_response, "suggested_prompt"):
            suggested = response.parsed_response.suggested_prompt
        if not suggested and response.raw_text_response:
            suggested = response.raw_text_response
        if response.parsed_response:
            try:
                metadata = {k: v for k, v in response.parsed_response.model_dump().items()
                            if k != "suggested_prompt" and v is not None}
            except Exception:
                pass
    except Exception as exc:
        print(f"WARNING: Could not extract response fields: {exc}", file=sys.stderr)

    if not suggested:
        print("ERROR: Optimizer returned an empty response.", file=sys.stderr)
        sys.exit(1)

    original_lines = args.prompt.splitlines(keepends=True)
    suggested_lines = suggested.splitlines(keepends=True)
    diff_hunks = list(difflib.unified_diff(
        original_lines, suggested_lines,
        fromfile="original", tofile="optimized",
        lineterm="", n=3,
    ))

    return {
        "iteration": args.iteration,
        "project": project,
        "location": location,
        "original_prompt": args.prompt,
        "steering_applied": [h.strip() for h in args.steering.split(";") if h.strip()],
        "suggested_prompt": suggested,
        "changes": diff_hunks,
        "optimization_metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    if args.detect_env:
        print(json.dumps(detect_env(), indent=2))
        sys.exit(0)
    result = run_optimizer(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
