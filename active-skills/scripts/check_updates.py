"""Compare the installed active-skills version against the marketplace repo.

Ran as a sidecar until 2026-07-22, on a 6-hourly schedule. It never executed:
the agy CLI starts no sidecar manager, so a plugin's `sidecars/` directory is
inert on both runtimes (evidence in `.agents/wiki/antigravity/`). It is now
driven by `agy_check_updates.py` from a `Stop` hook, which applies the same
6-hourly cadence and runs this detached so it never delays a turn.

Writes status.json and exits; nothing consumes that file yet.
"""

import os
import sys
import json
import re
import urllib.request
from datetime import datetime, timezone


def status_dir():
    """Directory holding status.json.

    The sidecar read ANTIGRAVITY_EXECUTABLE_DATA_DIR and fell back to a `data/`
    folder beside itself. A hook gets no such variable, and writing inside the
    installed plugin would be wiped by the next `agy plugin install`, so this
    defaults to the XDG cache. The override exists for tests and for pinning the
    location on a machine with an unusual cache root.
    """
    override = os.environ.get('ACTIVE_SKILLS_STATE_DIR')
    if override:
        return override
    cache_root = os.environ.get('XDG_CACHE_HOME') or os.path.expanduser('~/.cache')
    return os.path.join(cache_root, 'active-skills')

def parse_version(v_str):
    """
    Parses semantic version strings robustly.
    Handles 'v' prefixes, pre-release/metadata suffixes (like -beta, +build),
    and normalizes incomplete versions to a standard 3-tuple (major, minor, patch).
    """
    try:
        clean_str = v_str.strip().lstrip('vV')
        parts = []
        for part in clean_str.split('.'):
            match = re.match(r'^(\d+)', part)
            if match:
                parts.append(int(match.group(1)))
            else:
                parts.append(0)
        # Pad with zeros to guarantee at least 3 elements
        while len(parts) < 3:
            parts.append(0)
        # Return standard 3-segment semantic version
        return tuple(parts[:3])
    except Exception:
        return (0, 0, 0)

def check_for_updates():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # scripts/ sits one level under the plugin root; the sidecar sat two.
    local_path = os.path.abspath(os.path.join(current_dir, '../plugin.json'))

    # Establish data directory and state tracking paths
    data_dir = status_dir()
    status_path = os.path.join(data_dir, 'status.json')

    # Try loading existing status file to preserve previous state on failure
    prev_status = {}
    try:
        if os.path.exists(status_path):
            with open(status_path, 'r', encoding='utf-8') as f:
                prev_status = json.load(f)
    except Exception:
        pass

    # 1. Locate and parse local plugin.json
    try:
        with open(local_path, 'r', encoding='utf-8') as f:
            local_manifest = json.load(f)
            local_version = local_manifest.get('version', '0.0.0')
    except Exception as e:
        print(f"Error reading local manifest: {e}", file=sys.stderr)
        local_version = prev_status.get('local_version', '0.0.0')

    # 2. Fetch remote plugin.json
    # The version lives in the marketplace repo, NOT in the skills-authoring repo.
    # mlarkin00/active-skills went skills-only in the 2026-07-22 restructure and
    # carries no manifest at all; this URL used to point there and returned 404 on
    # every run, so the check silently reported "preserving last known state"
    # forever. sync-active-skills.yml owns the version and patch-bumps the manifest
    # below on every mirrored change, so it is the earliest place a new version
    # appears.
    remote_url = ('https://raw.githubusercontent.com/mlarkin00/plugins'
                  '/main/active-skills/plugin.json')
    remote_version = None
    fetch_error = None
    try:
        req = urllib.request.Request(remote_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            remote_manifest = json.loads(response.read().decode('utf-8'))
            remote_version = remote_manifest.get('version')
    except Exception as e:
        fetch_error = str(e)
        print(f"Error fetching remote manifest: {e}", file=sys.stderr)

    # 3. Compare versions
    status_data = {
        "last_checked": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "local_version": local_version,
    }

    if remote_version is not None:
        update_available = parse_version(remote_version) > parse_version(local_version)
        status_data.update({
            "status": "success",
            "remote_version": remote_version,
            "update_available": update_available
        })
        if update_available:
            print(f"[UPDATE] A newer version of active-skills is available: local={local_version}, remote={remote_version}")
        else:
            print(f"[OK] active-skills is up-to-date (v{local_version})")
    else:
        # Graceful fallback: preserve last known remote version and update status on network failure
        preserved_remote = prev_status.get('remote_version')
        preserved_update = prev_status.get('update_available')
        
        status_data.update({
            "status": "error",
            "error_message": fetch_error,
            "remote_version": preserved_remote,
            "update_available": preserved_update if preserved_update is not None else False
        })
        print(f"[WARNING] Update check failed. Preserving last known state: remote={preserved_remote}", file=sys.stderr)

    # 4. Persist state atomically
    try:
        os.makedirs(data_dir, exist_ok=True)
        temp_path = status_path + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2)
        os.replace(temp_path, status_path)
    except Exception as e:
        print(f"Error writing status.json: {e}", file=sys.stderr)
        # Attempt to clean up temp file if write failed mid-way
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    return status_data

if __name__ == '__main__':
    check_for_updates()
