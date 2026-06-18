import json
import os
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestPluginMetadata(unittest.TestCase):
    def test_plugin_manifest_exists_and_is_valid(self):
        manifest_path = os.path.join(BASE_DIR, '.claude-plugin', 'plugin.json')
        self.assertTrue(os.path.exists(manifest_path), ".claude-plugin/plugin.json is missing")
        with open(manifest_path) as f:
            data = json.load(f)
        self.assertEqual(data.get('name'), 'memory-bank')
        self.assertIn('config', data)
        cfg = data['config']
        self.assertIn('project', cfg)
        self.assertIn('location', cfg)
        self.assertIn('reasoning_engine_id', cfg)

    def test_hooks_file_exists_and_has_correct_structure(self):
        hooks_path = os.path.join(BASE_DIR, 'hooks', 'hooks.json')
        self.assertTrue(os.path.exists(hooks_path), "hooks/hooks.json is missing")
        with open(hooks_path) as f:
            data = json.load(f)
        self.assertIn('hooks', data)
        hooks = data['hooks']
        self.assertIn('SessionStart', hooks)
        self.assertIn('Stop', hooks)
        # SessionStart must have at least load_context.py
        ss_cmds = [h.get('command', '') for entry in hooks['SessionStart'] for h in entry.get('hooks', [])]
        self.assertTrue(any('load_context.py' in c for c in ss_cmds))
        # Stop must have save_context.py and sidecar_consolidate.py
        stop_cmds = [h.get('command', '') for entry in hooks['Stop'] for h in entry.get('hooks', [])]
        self.assertTrue(any('save_context.py' in c for c in stop_cmds))
        self.assertTrue(any('sidecar_consolidate.py' in c for c in stop_cmds))

if __name__ == '__main__':
    unittest.main()
