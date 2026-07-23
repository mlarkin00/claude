#!/usr/bin/env python3
"""Provision the GCP Memory Bank for this plugin. Idempotent: every step checks
before it acts, so a re-run on a healthy machine reports OK/SKIPPED, never a
spurious failure.

This was an agent (agents/bootstrap-memory-bank.md) until memory-bank 0.1.24.
Antigravity installs plugin agents but cannot invoke them, so the procedure
moved here — one script both runtimes run identically, rather than a procedure
re-derived from prose each time. It resolves its own plugin root from
__file__ (no $CLAUDE_PLUGIN_ROOT, which is empty outside a hook), verifies or
creates the reasoning engine, and writes a new engine ID back to the manifest
via json.dump instead of a hand Edit.

Usage:
    python3 bootstrap.py                # provision; leave existing memories alone
    python3 bootstrap.py --import-cc    # also import ~/.claude/memory/*.md

The bootstrap-memory-bank skill asks the yes/no import question and passes the
flag; the script itself is non-interactive so it is safe to run headless.

Exit 0 = ready (possibly with SKIPPED steps). Exit 1 = stopped at the first hard
failure; the last ✗ line says why and what to do.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from config import get_plugin_config, set_reasoning_engine_id, plugin_manifest_path  # noqa: E402


def ok(msg):      print(f"✓ OK       {msg}")
def created(msg): print(f"✓ CREATED  {msg}")
def skipped(msg): print(f"→ SKIPPED  {msg}")
def fail(msg):
    print(f"✗ FAILED   {msg}", file=sys.stderr)
    sys.exit(1)


def access_token():
    try:
        p = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            capture_output=True, text=True, check=True,
        )
        return p.stdout.strip()
    except FileNotFoundError:
        fail("Step 1 ADC: gcloud is not installed. Install the Google Cloud SDK, then re-run.")
    except subprocess.CalledProcessError:
        fail("Step 1 ADC: no application-default credentials. "
             "Run 'gcloud auth application-default login', then re-run.")


def engine_exists(project, location, engine_id, token):
    """True if the reasoning engine resolves, False on 404, fail on other errors."""
    url = (f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/"
           f"{project}/locations/{location}/reasoningEngines/{engine_id}")
    req = urllib.request.Request(url, method="GET", headers={
        "Authorization": f"Bearer {token}",
        "X-Goog-User-Project": project,
    })
    try:
        with urllib.request.urlopen(req) as res:
            return res.status == 200
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return False
        fail(f"Step 4 engine: unexpected HTTP {e.code} verifying engine {engine_id}.")
    except urllib.error.URLError as e:
        fail(f"Step 4 engine: could not reach the API ({e.reason}). Check network, then re-run.")


def main():
    ap = argparse.ArgumentParser(description="Provision the GCP Memory Bank.")
    ap.add_argument("--import-cc", action="store_true",
                    help="import ~/.claude/memory/*.md as global memories after setup")
    args = ap.parse_args()

    print("Bootstrapping GCP Memory Bank")
    print()

    # --- Step 1: ADC --------------------------------------------------------
    token = access_token()
    ok("Step 1 ADC: application-default credentials present")

    # --- Step 2: plugin root & config --------------------------------------
    manifest = plugin_manifest_path()
    if not os.path.isfile(manifest):
        fail(f"Step 2 config: manifest not found at {manifest}. Is the plugin installed correctly?")
    cfg = get_plugin_config()
    project, location = cfg["project"], cfg["location"]
    if not project or not location:
        fail("Step 2 config: config.project and config.location must be set in the manifest "
             "(or GCP_PROJECT / GCP_LOCATION in the environment).")
    ok(f"Step 2 config: project={project} location={location}")

    # --- Step 3: reasoning engine ------------------------------------------
    engine_id = cfg["reasoning_engine_id"]
    have_engine = bool(engine_id) and engine_exists(project, location, engine_id, token)
    if have_engine:
        ok(f"Step 3 engine: {engine_id} exists")
    else:
        if engine_id:
            print(f"  engine {engine_id} from config does not resolve; creating a new one")
        # create_engine persists the new ID via set_reasoning_engine_id and
        # polls to completion; it sys.exit(1)s on API failure.
        import create_engine
        new_id = create_engine.run_creation(
            project, location, "Shared Agentic Memory",
            "Shared long-term memories for AI agents")
        if not new_id:
            fail("Step 3 engine: creation returned no engine ID.")
        created(f"Step 3 engine: created {new_id} and wrote it to the manifest")
        engine_id = new_id

    # --- Step 4: verify context loads --------------------------------------
    load_ctx = os.path.join(SCRIPT_DIR, "load_context.py")
    try:
        proc = subprocess.run([sys.executable, load_ctx], input="{}",
                              capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        fail("Step 4 verify: load_context.py timed out.")
    out = proc.stdout.strip()
    try:
        parsed = json.loads(out) if out else {}
    except json.JSONDecodeError:
        fail(f"Step 4 verify: load_context.py did not return JSON: {out[:200] or proc.stderr[:200]}")
    if "injectSteps" in parsed:
        n = len(parsed["injectSteps"])
        ok(f"Step 4 verify: context loads ({n} inject step(s); 0 is normal on a fresh engine)")
    else:
        fail(f"Step 4 verify: unexpected output {out[:200]}. Check the engine ID and ADC.")

    # --- Step 5: optional CC import ----------------------------------------
    if args.import_cc:
        importer = os.path.join(SCRIPT_DIR, "import_cc_memories.py")
        proc = subprocess.run([sys.executable, importer], capture_output=True, text=True)
        if proc.returncode == 0:
            tail = (proc.stdout.strip().splitlines() or ["done"])[-1]
            created(f"Step 5 import: {tail}")
        else:
            # Non-fatal: the engine is provisioned; import can be retried.
            print(f"  import warning: {proc.stderr.strip()[:200]}", file=sys.stderr)
            skipped("Step 5 import: import_cc_memories.py reported an error (engine is still ready)")
    else:
        skipped("Step 5 import: not requested (pass --import-cc to import ~/.claude/memory)")

    # --- Step 6: symlinks (Claude Code only) -------------------------------
    # install-symlinks.sh needs $CLAUDE_PLUGIN_ROOT and links into ~/.claude;
    # on Antigravity the scripts are reached at their install path, so this is
    # correctly a no-op there.
    if os.environ.get("CLAUDE_PLUGIN_ROOT") and os.path.isdir(os.path.expanduser("~/.claude")):
        symlinks = os.path.join(SCRIPT_DIR, "install-symlinks.sh")
        proc = subprocess.run(["bash", symlinks], capture_output=True, text=True)
        if proc.returncode == 0:
            ok("Step 6 symlinks: scripts linked into ~/.claude/scripts/memory-bank")
        else:
            skipped(f"Step 6 symlinks: {proc.stderr.strip()[:120]}")
    else:
        skipped("Step 6 symlinks: not a Claude Code hook context (Antigravity reaches scripts in place)")

    print()
    print("Memory Bank is ready. GCP memories are fetched at each session start and")
    print("consolidated at session end. Use /memory-bank to save a fact immediately.")


if __name__ == "__main__":
    main()
