import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import config


class TestSetReasoningEngineId(unittest.TestCase):
    def _manifest(self, data):
        """Write a manifest to a temp file and point config.py at it."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, tmp)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def test_writes_engine_id_into_empty_config(self):
        path = self._manifest({"name": "memory-bank", "version": "0.1.0", "config": {}})
        with patch("config.plugin_manifest_path", return_value=path):
            config.set_reasoning_engine_id("998877")
        data = json.load(open(path))
        self.assertEqual(data["config"]["reasoning_engine_id"], "998877")

    def test_preserves_other_fields_and_overwrites_stale_id(self):
        path = self._manifest({
            "name": "memory-bank",
            "version": "0.1.23",
            "config": {"project": "p", "location": "us-west1", "reasoning_engine_id": "old"},
        })
        with patch("config.plugin_manifest_path", return_value=path):
            config.set_reasoning_engine_id("new-id")
        data = json.load(open(path))
        self.assertEqual(data["config"]["reasoning_engine_id"], "new-id")
        # Nothing else moved.
        self.assertEqual(data["config"]["project"], "p")
        self.assertEqual(data["config"]["location"], "us-west1")
        self.assertEqual(data["version"], "0.1.23")
        self.assertEqual(data["name"], "memory-bank")

    def test_creates_config_block_when_absent(self):
        path = self._manifest({"name": "memory-bank", "version": "0.1.0"})
        with patch("config.plugin_manifest_path", return_value=path):
            config.set_reasoning_engine_id("xyz")
        data = json.load(open(path))
        self.assertEqual(data["config"]["reasoning_engine_id"], "xyz")

    def test_get_config_reads_back_what_was_written(self):
        path = self._manifest({
            "name": "memory-bank",
            "config": {"project": "proj", "location": "loc", "reasoning_engine_id": ""},
        })
        with patch("config.plugin_manifest_path", return_value=path):
            config.set_reasoning_engine_id("round-trip")
            cfg = config.get_plugin_config()
        self.assertEqual(cfg["reasoning_engine_id"], "round-trip")
        self.assertEqual(cfg["project"], "proj")

    def test_output_is_valid_json_not_truncated(self):
        path = self._manifest({"name": "memory-bank", "config": {"project": "p"}})
        with patch("config.plugin_manifest_path", return_value=path):
            config.set_reasoning_engine_id("id-1")
        # Re-parses cleanly and ends with a trailing newline.
        text = open(path).read()
        self.assertTrue(text.endswith("\n"))
        json.loads(text)


if __name__ == "__main__":
    unittest.main()
