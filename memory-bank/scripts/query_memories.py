import sys
import os
import json
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_scope import resolve_user_id, resolve_project_id
from config import get_plugin_config

def query_memory_bank(project, location, engine_id, user_hash, project_hash, query):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories:retrieve"
    payload = {
        "scope": {"user": user_hash, "project": project_hash},
        "similaritySearchParams": {"searchQuery": query}
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
        print(f"Warning: failed to get access token: {e}")

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8')).get('retrievedMemories', [])
    except Exception as e:
        print(f"Error querying memories: {e}")
        return []

def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "retrieve key developer settings and configurations"

    workspace_path = os.getcwd()
    user_hash = resolve_user_id()
    project_hash = resolve_project_id(workspace_path)

    cfg = get_plugin_config()
    results_global = query_memory_bank(cfg["project"], cfg["location"], cfg["reasoning_engine_id"],
                                       user_hash, "global", query)
    results_project = query_memory_bank(cfg["project"], cfg["location"], cfg["reasoning_engine_id"],
                                        user_hash, project_hash, query)

    results = sorted(results_global + results_project, key=lambda x: x.get('distance', 0.0))

    if not results:
        print("No memories matched.")
        return

    print(f"Retrieved {len(results)} match(es) for: '{query}'\n")
    for i, item in enumerate(results, 1):
        memory = item.get('memory', {})
        scope = memory.get('scope', {})
        print(f"Match #{i} (score: {item.get('distance', 0.0):.4f})")
        print(f"  Scope: user=…{scope.get('user','')[-8:]}  project=…{scope.get('project','')[-8:]}")
        print(f"  Fact:  {memory.get('fact', 'N/A')}\n")

if __name__ == '__main__':
    main()
