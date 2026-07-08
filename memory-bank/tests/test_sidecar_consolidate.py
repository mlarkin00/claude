import unittest
import sys
import os
import json
import time
import io
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

class TestSidecarConsolidate(unittest.TestCase):
    def setUp(self):
        sys.modules.pop('sidecar_consolidate', None)

    @patch('sidecar_consolidate.get_state_file_path')
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_gate_throttles_within_24_hours(self, mock_open, mock_exists, mock_state_path):
        import sidecar_consolidate
        mock_state_path.return_value = "/dummy/state.json"
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps({"last_run": time.time() - 5})
        mock_open.return_value.__enter__.return_value = mock_file
        self.assertFalse(sidecar_consolidate.should_run_sidecar(interval_seconds=86400))

    @patch('sidecar_consolidate.get_state_file_path')
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_gate_allows_after_24_hours_or_no_state(self, mock_open, mock_exists, mock_state_path):
        import sidecar_consolidate
        mock_state_path.return_value = "/dummy/state.json"

        mock_exists.return_value = False
        self.assertTrue(sidecar_consolidate.should_run_sidecar(interval_seconds=86400))

        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps({"last_run": time.time() - 90000})
        mock_open.return_value.__enter__.return_value = mock_file
        self.assertTrue(sidecar_consolidate.should_run_sidecar(interval_seconds=86400))

    @patch('os.path.exists')
    @patch('os.walk')
    @patch('builtins.open')
    def test_aggregate_transcripts_parses_cc_format(self, mock_open, mock_walk, mock_exists):
        mock_exists.return_value = True
        import sidecar_consolidate

        mock_walk.return_value = [
            ("/projects/abc", [], ["transcript.jsonl"]),
            ("/projects/def", [], ["transcript.jsonl"]),
        ]

        file1 = [
            json.dumps({"role": "user", "content": "I prefer dark theme."}),
            json.dumps({"role": "assistant", "content": "Applying dark theme."}),
        ]
        file2 = [
            json.dumps({"role": "user", "content": "Restrict pods to 5."}),
            "{corrupted_json}",
            json.dumps({"role": "assistant", "content": "Got it, pods capped."}),
        ]

        def open_side_effect(filepath, *args, **kwargs):
            m = MagicMock()
            m.__enter__.return_value = file1 if "abc" in filepath else file2
            return m

        mock_open.side_effect = open_side_effect
        events = sidecar_consolidate.aggregate_transcripts("/projects")

        self.assertEqual(len(events), 4)  # corrupted line skipped
        self.assertEqual(events[0]["content"]["role"], "user")
        self.assertEqual(events[1]["content"]["role"], "model")
        self.assertEqual(events[2]["content"]["role"], "user")
        self.assertEqual(events[3]["content"]["role"], "model")

    @patch('sidecar_consolidate.nudge_minion')
    @patch('sidecar_consolidate.run_graduation')
    @patch('sidecar_consolidate.get_plugin_config')
    @patch('sidecar_consolidate.should_run_sidecar')
    @patch('sidecar_consolidate.aggregate_transcripts')
    @patch('sidecar_consolidate.resolve_user_id')
    @patch('sidecar_consolidate.save_state_timestamp')
    @patch('urllib.request.urlopen')
    def test_run_consolidates_then_nudges_minion(
        self, mock_urlopen, mock_save_state, mock_resolve_user, mock_aggregate,
        mock_should_run, mock_config, mock_graduation, mock_nudge
    ):
        import sidecar_consolidate
        mock_config.return_value = {
            "project": "my-project",
            "location": "us-central1",
            "reasoning_engine_id": "123"
        }
        mock_should_run.return_value = True
        mock_aggregate.return_value = [
            {"content": {"role": "user", "parts": [{"text": "I want TailwindCSS."}]}}
        ]
        mock_resolve_user.return_value = "user_hash_123"

        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch('sys.stdin', io.StringIO(json.dumps({}))):
            sidecar_consolidate.run()

        # Consolidation still runs (transcripts -> memories:generate)
        self.assertTrue(mock_urlopen.called)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.method, 'POST')
        self.assertIn('my-project', req.full_url)
        self.assertIn('memories:generate', req.full_url)
        data = json.loads(req.data.decode('utf-8'))
        self.assertEqual(data["scope"]["user"], "user_hash_123")
        self.assertEqual(data["scope"]["project"], "global")
        self.assertTrue(mock_save_state.called)

        # Curation is no longer done here — the deployed agent is nudged instead.
        self.assertTrue(mock_nudge.called)


if __name__ == '__main__':
    unittest.main()
