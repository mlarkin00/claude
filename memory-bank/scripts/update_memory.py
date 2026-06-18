import sys
import os
import json
import urllib.request
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_plugin_config

def update_memory(project, location, engine_id, memory_id, new_fact):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories/{memory_id}?updateMask=fact"
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
        req = urllib.request.Request(url, data=json.dumps({"fact": new_fact}).encode('utf-8'),
                                     headers=headers, method='PATCH')
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"Error updating memory: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Update an existing memory's fact in the GCP Memory Bank.")
    parser.add_argument("memory_id", help="Memory ID to update.")
    parser.add_argument("fact", help="New fact text.")
    args = parser.parse_args()

    cfg = get_plugin_config()
    res = update_memory(cfg["project"], cfg["location"], cfg["reasoning_engine_id"],
                        args.memory_id, args.fact)

    if res is not None and isinstance(res, dict):
        print(f"Successfully updated memory '{args.memory_id}'.")
    else:
        print(f"Failed to update memory '{args.memory_id}'.")

if __name__ == '__main__':
    main()
