import sys
import os
import json
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_scope import resolve_user_id
from config import get_plugin_config

# --- state / rate-limiting ---

def get_state_file_path():
    state_dir = os.path.join(os.path.expanduser('~'), '.cache', 'memory-bank')
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, '.sidecar_state.json')

def get_projects_dir():
    return os.path.join(os.path.expanduser('~'), '.claude', 'projects')

def should_run_sidecar(interval_seconds=86400):
    state_path = get_state_file_path()
    if not os.path.exists(state_path):
        return True
    try:
        with open(state_path, 'r') as f:
            data = json.loads(f.read())
            if time.time() - data.get('last_run', 0) >= interval_seconds:
                return True
    except Exception:
        return True
    return False

def save_state_timestamp():
    try:
        with open(get_state_file_path(), 'w') as f:
            json.dump({"last_run": time.time()}, f)
    except Exception:
        pass

# --- transcript aggregation ---

def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [block.get('text', '') for block in content
                 if isinstance(block, dict) and block.get('type') == 'text']
        return '\n'.join(parts)
    return ''

def aggregate_transcripts(projects_dir):
    events = []
    if not projects_dir or not os.path.exists(projects_dir):
        return events

    for root, _, files in os.walk(projects_dir):
        for file in files:
            if not file.endswith('.jsonl'):
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            step = json.loads(line.strip())
                        except (json.JSONDecodeError, TypeError):
                            continue
                        msg = step if 'role' in step else step.get('message', {})
                        role = msg.get('role', '')
                        content = extract_text(msg.get('content', ''))
                        if role == 'user' and content:
                            events.append({"role": "USER", "content": content})
                        elif role == 'assistant' and content:
                            events.append({"role": "AGENT", "content": content})
            except Exception:
                pass
    return events

# --- GCP API helpers ---

def get_access_token():
    import subprocess
    try:
        p = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                           capture_output=True, text=True, check=True)
        return p.stdout.strip()
    except Exception:
        return None

def make_headers(project, token=None):
    headers = {"Content-Type": "application/json", "X-Goog-User-Project": project}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def list_memories(project, location, engine_id):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories"
    token = get_access_token()
    try:
        req = urllib.request.Request(url, headers=make_headers(project, token), method='GET')
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8')).get('memories', [])
    except Exception as e:
        sys.stderr.write(f"[memory-bank] sidecar: failed to list memories: {e}\n")
        return []

def delete_memory(project, location, engine_id, memory_id):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories/{memory_id}"
    token = get_access_token()
    try:
        req = urllib.request.Request(url, headers=make_headers(project, token), method='DELETE')
        with urllib.request.urlopen(req, timeout=10) as res:
            res.read()
            return True
    except Exception as e:
        sys.stderr.write(f"[memory-bank] sidecar: failed to delete memory '{memory_id}': {e}\n")
        return False

def update_memory(project, location, engine_id, memory_id, new_fact):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories/{memory_id}?updateMask=fact"
    token = get_access_token()
    try:
        req = urllib.request.Request(url, data=json.dumps({"fact": new_fact}).encode('utf-8'),
                                     headers=make_headers(project, token), method='PATCH')
        with urllib.request.urlopen(req, timeout=10) as res:
            res.read()
            return True
    except Exception as e:
        sys.stderr.write(f"[memory-bank] sidecar: failed to update memory '{memory_id}': {e}\n")
        return False

def send_generation_request(project, location, engine_id, user_hash, project_hash, events):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories:generate"
    payload = {
        "scope": {"user": user_hash, "project": project_hash},
        "directContentsSource": {"events": events}
    }
    token = get_access_token()
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                     headers=make_headers(project, token), method='POST')
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status == 200
    except Exception:
        return False

# --- LLM-powered curation ---

_CURATION_PROMPT = """\
You are curating a GCP Memory Bank for an AI coding assistant. Review the memories below \
and return a JSON object indicating which to delete (semantic duplicates or superseded by scope) \
and which to rewrite (for agent-readability).

Dedup rules (apply in order):
1. Global vs global: if two global memories express the same fact, mark the less complete one for deletion.
2. Project vs global: if a project-scoped memory is fully covered by a global memory, mark the \
project-scoped one for deletion. Global scope wins.
3. Same-project vs same-project: if two memories in the same project scope express the same fact, \
mark the less complete one for deletion.
4. Cross-project: if memories in two different project scopes (neither global) express the same \
fact, leave both untouched — they are never co-loaded and are not true duplicates.

Rewrite rules (apply to surviving memories only):
- Use imperative voice: prefer "Always do X" over "User prefers X" or "User likes X".
- Remove hedging: eliminate "might", "usually", "generally", "kind of", "sometimes".
- Never lose semantic content — if tightening the wording changes the meaning, leave it unchanged.
- Only include a memory in to_update if the rewrite is substantively different; skip trivial style changes.

Memories:
{memories_json}

Return exactly this JSON and nothing else:
{{"to_delete": ["memory_id_1"], "to_update": [{{"id": "memory_id_2", "new_fact": "rewritten fact"}}]}}\
"""

def call_gemini_for_curation(memories, project, location):
    """Call Gemini to semantically deduplicate and rewrite memories.

    Returns (to_delete, to_update) where to_delete is a list of memory IDs and
    to_update is a list of {"id": ..., "new_fact": ...} dicts. Returns ([], []) on failure.
    """
    if not memories:
        return [], []

    memories_data = []
    for m in memories:
        scope = m.get('scope', {})
        proj = scope.get('project', '')
        memories_data.append({
            "id": m.get('name', '').split('/')[-1],
            "scope": "global" if proj == 'global' else f"project:{proj[-8:]}",
            "fact": m.get('fact', '')
        })

    prompt = _CURATION_PROMPT.replace("{memories_json}", json.dumps(memories_data, indent=2))

    url = (f"https://aiplatform.googleapis.com/v1/projects/{project}"
           f"/locations/global/publishers/google/models/gemini-3.5-flash:generateContent")
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0}
    }
    token = get_access_token()
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                     headers=make_headers(project, token), method='POST')
        with urllib.request.urlopen(req, timeout=60) as res:
            data = json.loads(res.read().decode('utf-8'))
            text = data['candidates'][0]['content']['parts'][0]['text']
            result = json.loads(text)
            return result.get('to_delete', []), result.get('to_update', [])
    except Exception as e:
        sys.stderr.write(f"[memory-bank] sidecar: gemini curation call failed: {e}\n")
        return [], []

def curate_memories(project, location, engine_id, user_hash):
    sys.stderr.write("[memory-bank] sidecar: curating memories...\n")
    all_memories = list_memories(project, location, engine_id)
    if not all_memories:
        return

    user_memories = [m for m in all_memories if m.get('scope', {}).get('user') == user_hash]
    if not user_memories:
        return

    to_delete, to_update = call_gemini_for_curation(user_memories, project, location)

    valid_ids = {m.get('name', '').split('/')[-1] for m in user_memories}

    deleted = 0
    deleted_ids = set()
    for memory_id in to_delete:
        if memory_id and memory_id in valid_ids:
            if delete_memory(project, location, engine_id, memory_id):
                deleted_ids.add(memory_id)
                deleted += 1

    updated = 0
    for item in to_update:
        memory_id = item.get('id', '')
        new_fact = item.get('new_fact', '').strip()
        if memory_id and memory_id in valid_ids and memory_id not in deleted_ids and new_fact:
            if update_memory(project, location, engine_id, memory_id, new_fact):
                updated += 1

    if deleted or updated:
        sys.stderr.write(f"[memory-bank] sidecar: curation complete — {deleted} deleted, {updated} rewritten.\n")

# --- main ---

def run():
    force = "--force" in sys.argv
    if not force and not should_run_sidecar():
        return

    cfg = get_plugin_config()
    gcp_project = cfg["project"]
    location = cfg["location"]
    engine_id = cfg["reasoning_engine_id"]
    user_hash = resolve_user_id()

    curate_memories(gcp_project, location, engine_id, user_hash)

    projects_dir = get_projects_dir()
    events = aggregate_transcripts(projects_dir)
    if events:
        success = send_generation_request(gcp_project, location, engine_id, user_hash, "global", events)
        if success:
            save_state_timestamp()
            sys.stderr.write("[memory-bank] sidecar: consolidation complete.\n")

if __name__ == '__main__':
    run()
