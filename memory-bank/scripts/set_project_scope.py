import sys
import os
import json
import urllib.request
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_scope import resolve_user_id, resolve_project_id
from config import get_plugin_config

def get_access_token():
    import subprocess
    try:
        p = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                           capture_output=True, text=True, check=True)
        return p.stdout.strip()
    except Exception:
        return None

def make_headers(project, token=None):
    h = {"Content-Type": "application/json", "X-Goog-User-Project": project}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def get_memory(project, location, engine_id, memory_id):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories/{memory_id}"
    token = get_access_token()
    try:
        req = urllib.request.Request(url, headers=make_headers(project, token), method='GET')
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching memory {memory_id}: {e}", file=sys.stderr)
        return None

def create_memory(project, location, engine_id, user_hash, project_hash, fact):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories"
    payload = {"scope": {"user": user_hash, "project": project_hash}, "fact": fact, "ttl": "2592000s"}
    token = get_access_token()
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                     headers=make_headers(project, token), method='POST')
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"Error creating memory: {e}", file=sys.stderr)
        return None

def delete_memory(project, location, engine_id, memory_id):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories/{memory_id}"
    token = get_access_token()
    try:
        req = urllib.request.Request(url, headers=make_headers(project, token), method='DELETE')
        with urllib.request.urlopen(req, timeout=10) as res:
            res.read()
            return True
    except Exception as e:
        print(f"Error deleting memory {memory_id}: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Re-scope a global memory to the current project.")
    parser.add_argument("memory_id", help="ID of the memory to re-scope.")
    args = parser.parse_args()

    workspace_path = os.getcwd()
    user_hash = resolve_user_id()
    project_hash = resolve_project_id(workspace_path)

    cfg = get_plugin_config()
    project, location, engine_id = cfg["project"], cfg["location"], cfg["reasoning_engine_id"]

    memory = get_memory(project, location, engine_id, args.memory_id)
    if not memory or not memory.get('fact'):
        print(f"Failed to fetch memory '{args.memory_id}'.")
        return

    new_memory = create_memory(project, location, engine_id, user_hash, project_hash, memory['fact'])
    if not new_memory:
        print("Failed to create project-scoped memory.")
        return

    new_id = new_memory.get('name', '').split('/')[-1]
    delete_memory(project, location, engine_id, args.memory_id)
    print(f"Re-scoped: {args.memory_id} → {new_id}")

if __name__ == '__main__':
    main()
