import sys
import os
import json
import urllib.request
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_scope import resolve_user_id, resolve_project_id
from config import get_plugin_config

def add_memory(project, location, engine_id, user_hash, project_hash, fact):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories"
    payload = {
        "scope": {"user": user_hash, "project": project_hash},
        "fact": fact,
        "ttl": "2592000s"  # 30 days
    }
    headers = {"Content-Type": "application/json", "X-Goog-User-Project": project}
    try:
        import subprocess
        p = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                           capture_output=True, text=True, check=True)
        token = p.stdout.strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        print(f"Warning: failed to get access token: {e}", file=sys.stderr)

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"Error adding memory: {e}", file=sys.stderr)
        return None

def memory_id_from_response(res):
    """Extract the memory ID from a CreateMemory long-running-operation response.

    CreateMemory returns an Operation, not the Memory. The operation's own
    `name` ends in the OPERATION id, but its `response.name` (present once
    done) is the canonical memory resource. As a fallback, the operation name
    embeds the memory id as `.../memories/{MEMORY_ID}/operations/{OP_ID}`.
    """
    if not isinstance(res, dict):
        return ''
    resource_name = (res.get('response') or {}).get('name', '')
    if not resource_name:
        op_name = res.get('name', '')
        if '/operations/' in op_name:
            resource_name = op_name.split('/operations/')[0]
    return resource_name.split('/')[-1] if resource_name else ''


def main():
    parser = argparse.ArgumentParser(description="Add a new memory fact to the GCP Memory Bank.")
    parser.add_argument("fact", help="The text of the memory fact to store.")
    parser.add_argument("--scope", choices=["global", "project"], default="global",
                        help="Storage scope. Defaults to global.")
    args = parser.parse_args()

    workspace_path = os.getcwd()
    user_hash = resolve_user_id()
    project_hash = "global" if args.scope == "global" else resolve_project_id(workspace_path)

    cfg = get_plugin_config()
    res = add_memory(cfg["project"], cfg["location"], cfg["reasoning_engine_id"],
                     user_hash, project_hash, args.fact)

    memory_id = memory_id_from_response(res)
    if memory_id:
        print(f"Successfully added memory '{memory_id}'.")
    else:
        print("Failed to add memory.")

if __name__ == '__main__':
    main()
