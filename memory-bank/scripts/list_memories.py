import sys
import os
import json
import subprocess
import urllib.request
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_scope import resolve_user_id, resolve_project_id
from config import get_plugin_config


def get_token():
    try:
        p = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                           capture_output=True, text=True, check=True)
        return p.stdout.strip()
    except Exception as e:
        print(f"Warning: failed to get access token: {e}", file=sys.stderr)
        return None


def _headers(project, token):
    headers = {"Content-Type": "application/json", "X-Goog-User-Project": project}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _base_url(project, location, engine_id):
    return (f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}"
            f"/locations/{location}/reasoningEngines/{engine_id}/memories")


def list_memories(project, location, engine_id, token):
    url = _base_url(project, location, engine_id)
    try:
        req = urllib.request.Request(url, headers=_headers(project, token), method='GET')
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8')).get('memories', [])
    except Exception as e:
        print(f"Error listing memories: {e}", file=sys.stderr)
        return []


def get_display_name(project, location, engine_id, memory_id, token):
    """The LIST endpoint omits displayName; a single-memory GET returns it."""
    url = f"{_base_url(project, location, engine_id)}/{memory_id}"
    try:
        req = urllib.request.Request(url, headers=_headers(project, token), method='GET')
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8')).get('displayName', '')
    except Exception:
        return ''


def main():
    parser = argparse.ArgumentParser(description="List memories from the GCP Memory Bank.")
    parser.add_argument("--scope", choices=["all", "current"], default="current",
                        help="'current' shows global + project memories; 'all' shows everything.")
    args = parser.parse_args()

    workspace_path = os.getcwd()
    user_hash = resolve_user_id()
    project_hash = resolve_project_id(workspace_path)

    cfg = get_plugin_config()
    token = get_token()
    memories = list_memories(cfg["project"], cfg["location"], cfg["reasoning_engine_id"], token)

    if not memories:
        print("No memories found in the Memory Bank.")
        return

    if args.scope == "current":
        memories = [m for m in memories
                    if m.get('scope', {}).get('user') == user_hash
                    and m.get('scope', {}).get('project') in ("global", project_hash)]
        print(f"Memories for current scope (user …{user_hash[-8:]}, project …{project_hash[-8:]} or global):")
    else:
        print("All memories in the GCP Memory Bank:")

    if not memories:
        print("No memories match the current scope.")
        return

    for i, m in enumerate(memories, 1):
        name = m.get('name', 'N/A')
        memory_id = name.split('/')[-1] if '/' in name else name
        scope = m.get('scope', {})
        # displayName is not returned by LIST — fetch it per memory so names show.
        display = get_display_name(cfg["project"], cfg["location"], cfg["reasoning_engine_id"],
                                   memory_id, token)
        print(f"\n[{i}] ID: {memory_id}")
        print(f"    Name:     {display or '(unnamed)'}")
        print(f"    Created:  {m.get('createTime', 'N/A')}")
        print(f"    Scope:    user=…{scope.get('user','')[-8:]}  project=…{scope.get('project','')[-8:]}")
        print(f"    Fact:     {m.get('fact', 'N/A')}")


if __name__ == '__main__':
    main()
