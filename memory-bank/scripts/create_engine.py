import sys
import os
import json
import time
import urllib.request
import urllib.error
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_plugin_config, set_reasoning_engine_id

def build_payload(display_name, description, project, location):
    return {
        "displayName": display_name,
        "description": description,
        "contextSpec": {
            "memoryBankConfig": {
                "generationConfig": {
                    "model": f"projects/{project}/locations/{location}/publishers/google/models/gemini-2.0-flash-001"
                },
                "similaritySearchConfig": {
                    "embeddingModel": f"projects/{project}/locations/{location}/publishers/google/models/text-embedding-005"
                },
                "ttlConfig": {
                    "memoryRevisionDefaultTtl": "31536000s"
                },
                "customizationConfigs": [
                    {
                        "memoryTopics": [
                            {"managedMemoryTopic": {"managedTopicEnum": "USER_PERSONAL_INFO"}},
                            {"managedMemoryTopic": {"managedTopicEnum": "USER_PREFERENCES"}},
                            {"managedMemoryTopic": {"managedTopicEnum": "KEY_CONVERSATION_DETAILS"}},
                            {"managedMemoryTopic": {"managedTopicEnum": "EXPLICIT_INSTRUCTIONS"}}
                        ],
                        "generateMemoriesExamples": [],
                        "consolidationConfig": {"revisionsPerCandidateCount": 1},
                        "enableThirdPersonMemories": False
                    }
                ],
                "disableMemoryRevisions": False
            }
        }
    }

def parse_operation_response(data):
    done = data.get("done", False)
    if not done:
        return False, None
    engine_id = data.get("response", {}).get("name", "").split("/")[-1] or None
    return True, engine_id

def get_access_token():
    p = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                       capture_output=True, text=True, check=True)
    return p.stdout.strip()

def run_creation(project, location, display_name, description):
    token = get_access_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Goog-User-Project": project
    }
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines"
    payload = build_payload(display_name, description, project, location)

    print(f"Creating reasoning engine '{display_name}' in project '{project}'...")
    req = urllib.request.Request(url, headers=headers, data=json.dumps(payload).encode('utf-8'), method='POST')
    try:
        with urllib.request.urlopen(req) as res:
            op_data = json.loads(res.read().decode('utf-8'))
            op_name = op_data.get("name")
            print(f"Operation started: {op_name}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.reason}", file=sys.stderr)
        try:
            print(e.read().decode('utf-8'), file=sys.stderr)
        except Exception:
            pass
        sys.exit(1)

    poll_url = f"https://{location}-aiplatform.googleapis.com/v1beta1/{op_name}"
    while True:
        print("Polling...")
        time.sleep(10)
        poll_req = urllib.request.Request(poll_url, headers=headers, method='GET')
        with urllib.request.urlopen(poll_req) as poll_res:
            status = json.loads(poll_res.read().decode('utf-8'))
            if status.get("done"):
                response = status.get("response", {})
                engine_id = response.get("name", "").split("/")[-1]
                if engine_id:
                    print(f"\nCreated. Engine ID: {engine_id}")
                    print(f"Full name: projects/{project}/locations/{location}/reasoningEngines/{engine_id}")
                    written = set_reasoning_engine_id(engine_id)
                    print(f'Wrote config.reasoning_engine_id to {written}')
                    return engine_id
                else:
                    print(f"Operation failed: {status.get('error')}", file=sys.stderr)
                    sys.exit(1)

if __name__ == "__main__":
    cfg = get_plugin_config()
    run_creation(cfg["project"], cfg["location"],
                 "Shared Agentic Memory", "Shared long-term memories for AI agents")
