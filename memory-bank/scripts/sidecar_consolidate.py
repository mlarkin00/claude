import sys
import os
import json
import time
import subprocess
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
                        # Content-shaped events for directContentsSource.events:
                        # {"content": {"role": "user"|"model", "parts": [{"text": ...}]}}.
                        if role == 'user' and content:
                            events.append({"content": {"role": "user", "parts": [{"text": content}]}})
                        elif role == 'assistant' and content:
                            events.append({"content": {"role": "model", "parts": [{"text": content}]}})
            except Exception:
                pass
    return events

# --- GCP API helpers ---

def get_access_token():
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

# --- fail-open nudge to the deployed memory-minion ---

def nudge_minion():
    """Fire-and-forget: ask the deployed memory-minion agent to curate the bank.

    Curation itself is no longer done in this plugin — it runs in the GCP Agent
    Runtime. This nudge is best-effort and FAIL-OPEN: if it cannot fire, the agent's
    own schedule still grooms the change. Never blocks or raises.
    """
    try:
        nudge = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nudge_minion.py')
        subprocess.Popen([sys.executable, nudge],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

# --- graduation phase ---

def run_graduation(force=False):
    try:
        import graduate_memories
        graduate_memories.run(dry_run=False, force=force)
    except Exception as e:
        sys.stderr.write(f"[memory-bank] sidecar: graduation phase error: {e}\n")


# --- main ---

def run():
    force          = "--force" in sys.argv
    force_graduate = "--force-graduate" in sys.argv

    if not force and not should_run_sidecar():
        return

    cfg = get_plugin_config()
    gcp_project = cfg["project"]
    location = cfg["location"]
    engine_id = cfg["reasoning_engine_id"]
    user_hash = resolve_user_id()

    projects_dir = get_projects_dir()
    events = aggregate_transcripts(projects_dir)
    if events:
        success = send_generation_request(gcp_project, location, engine_id, user_hash, "global", events)
        if success:
            save_state_timestamp()
            sys.stderr.write("[memory-bank] sidecar: consolidation complete.\n")

    run_graduation(force=force_graduate)

    # Curation is done server-side by the deployed memory-minion agent. Nudge it
    # (fail-open) after consolidation + graduation so new facts get groomed.
    nudge_minion()

if __name__ == '__main__':
    run()
