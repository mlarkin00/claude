import sys
import os
import json
import urllib.request
import urllib.error
import html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_scope import resolve_user_id, resolve_project_id
from config import get_plugin_config

def query_memory_bank(project, location, engine_id, user_hash, project_hash):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories:retrieve"
    payload = {
        "scope": {
            "user": user_hash,
            "project": project_hash
        },
        "similaritySearchParams": {
            "searchQuery": "retrieve key developer settings and configurations"
        }
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-User-Project": project
    }
    try:
        import subprocess
        p = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                           capture_output=True, text=True, check=True)
        token = p.stdout.strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception:
        pass

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            retrieved = data.get('retrievedMemories', [])
            return [item.get('memory', {}).get('fact') for item in retrieved if item.get('memory', {}).get('fact')]
    except Exception:
        return []

def run():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        input_data = {}

    workspace_paths = input_data.get('workspacePaths', [])
    workspace_path = workspace_paths[0] if workspace_paths else None

    user_hash = resolve_user_id()
    project_hash = resolve_project_id(workspace_path)

    cfg = get_plugin_config()
    gcp_project = cfg["project"]
    location = cfg["location"]
    engine_id = cfg["reasoning_engine_id"]

    facts_global = query_memory_bank(gcp_project, location, engine_id, user_hash, "global")
    facts_project = query_memory_bank(gcp_project, location, engine_id, user_hash, project_hash)

    seen = set()
    facts = []
    for fact in (facts_global + facts_project):
        if fact not in seen:
            seen.add(fact)
            facts.append(fact)

    if not facts:
        print(json.dumps({"injectSteps": []}))
        return

    xml_lines = ["<long_term_memories>"]
    for fact in facts:
        escaped = html.escape(fact)
        xml_lines.append(f"  <memory>\n    <fact>{escaped}</fact>\n  </memory>")
    xml_lines.append("</long_term_memories>")
    xml_content = "\n".join(xml_lines)

    print(json.dumps({
        "injectSteps": [
            {"ephemeralMessage": xml_content}
        ]
    }))

if __name__ == '__main__':
    run()
