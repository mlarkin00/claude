import os
import json

def plugin_manifest_path():
    """Absolute path to the manifest config.py reads.

    realpath, not abspath: the scripts are invoked through per-runtime symlinks
    (~/.claude/scripts/memory-bank/…), and resolving them lands on the real
    plugin directory rather than the symlink's parent.
    """
    plugin_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    return os.path.join(plugin_dir, ".claude-plugin", "plugin.json")

def get_plugin_config():
    """
    Reads .claude-plugin/plugin.json from the plugin root and returns the config block.
    Falls back to environment variables if config is missing.
    """
    plugin_json_path = plugin_manifest_path()

    config = {}
    if os.path.exists(plugin_json_path):
        try:
            with open(plugin_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                config = data.get("config", {})
        except Exception:
            pass

    return {
        "project": config.get("project") or os.environ.get("GCP_PROJECT", ""),
        "location": config.get("location") or os.environ.get("GCP_LOCATION", ""),
        "reasoning_engine_id": config.get("reasoning_engine_id") or os.environ.get("GCP_REASONING_ENGINE", "")
    }

def set_reasoning_engine_id(engine_id):
    """Persist a newly created engine ID into config.reasoning_engine_id.

    Writes the same manifest get_plugin_config() reads, preserving key order and
    every other field. Replaces the old bootstrap step that had the model Edit
    the manifest by hand — a parse-and-dump cannot corrupt the JSON or touch an
    unrelated field. Returns the path written.
    """
    path = plugin_manifest_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("config", {})["reasoning_engine_id"] = engine_id
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return path
