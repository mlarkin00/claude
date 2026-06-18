import os
import json

def get_plugin_config():
    """
    Reads .claude-plugin/plugin.json from the plugin root and returns the config block.
    Falls back to environment variables if config is missing.
    """
    plugin_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    plugin_json_path = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")

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
