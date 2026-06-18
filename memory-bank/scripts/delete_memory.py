import sys
import os
import json
import urllib.request
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_plugin_config

def delete_memory(project, location, engine_id, memory_id):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories/{memory_id}"
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
        req = urllib.request.Request(url, headers=headers, method='DELETE')
        with urllib.request.urlopen(req, timeout=10) as res:
            res.read()
            return True
    except Exception as e:
        print(f"Error deleting memory: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Delete a memory from the GCP Memory Bank.")
    parser.add_argument("memory_id", help="Memory ID to delete.")
    args = parser.parse_args()

    cfg = get_plugin_config()
    success = delete_memory(cfg["project"], cfg["location"], cfg["reasoning_engine_id"], args.memory_id)
    if success:
        print(f"Successfully deleted memory '{args.memory_id}'.")
    else:
        print(f"Failed to delete memory '{args.memory_id}'.")

if __name__ == '__main__':
    main()
