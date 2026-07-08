import unittest
import sys
import os
import json
import time
import io
from unittest.mock import patch, MagicMock, call

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

        # Claude Code format: role: user/assistant
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

    @patch('sidecar_consolidate.get_plugin_config')
    @patch('sidecar_consolidate.should_run_sidecar')
    @patch('sidecar_consolidate.aggregate_transcripts')
    @patch('sidecar_consolidate.curate_memories')
    @patch('sidecar_consolidate.resolve_user_id')
    @patch('sidecar_consolidate.save_state_timestamp')
    @patch('urllib.request.urlopen')
    def test_run_sends_api_request_and_updates_state(
        self, mock_urlopen, mock_save_state, mock_resolve_user,
        mock_curate, mock_aggregate, mock_should_run, mock_config
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

        self.assertTrue(mock_curate.called)
        self.assertTrue(mock_urlopen.called)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.method, 'POST')
        self.assertIn('my-project', req.full_url)
        self.assertIn('us-central1', req.full_url)
        self.assertIn('123', req.full_url)
        self.assertIn('memories:generate', req.full_url)

        data = json.loads(req.data.decode('utf-8'))
        self.assertEqual(data["scope"]["user"], "user_hash_123")
        self.assertEqual(data["scope"]["project"], "global")
        self.assertEqual(data["directContentsSource"]["events"][0]["content"]["role"], "user")
        self.assertTrue(mock_save_state.called)

    @patch('sidecar_consolidate.list_memories')
    @patch('sidecar_consolidate.call_gemini_for_curation')
    @patch('sidecar_consolidate.delete_memory')
    @patch('sidecar_consolidate.update_memory')
    def test_curate_memories_applies_deletes_and_updates(
        self, mock_update, mock_delete, mock_gemini, mock_list
    ):
        import sidecar_consolidate

        user_hash = "abc123"
        mock_list.return_value = [
            {"name": ".../m1", "scope": {"user": user_hash, "project": "global"}, "fact": "Use dark theme"},
            {"name": ".../m2", "scope": {"user": user_hash, "project": "global"}, "fact": "user likes dark theme"},
            {"name": ".../m3", "scope": {"user": user_hash, "project": "global"}, "fact": "Pods capped at 5"},
            {"name": ".../other", "scope": {"user": "different_user", "project": "global"}, "fact": "irrelevant"},
        ]
        mock_gemini.return_value = (
            ["m2"],
            [{"id": "m3", "new_fact": "Always cap pods at 5"}]
        )
        mock_delete.return_value = True
        mock_update.return_value = True

        sidecar_consolidate.curate_memories("my-project", "us-central1", "123", user_hash)

        # Only current user's memories passed to Gemini
        passed_memories = mock_gemini.call_args[0][0]
        self.assertEqual(len(passed_memories), 3)
        self.assertFalse(any(m['scope']['user'] == 'different_user' for m in passed_memories))

        mock_delete.assert_called_once_with("my-project", "us-central1", "123", "m2")
        mock_update.assert_called_once_with("my-project", "us-central1", "123", "m3", "Always cap pods at 5")

    @patch('sidecar_consolidate.list_memories')
    @patch('sidecar_consolidate.call_gemini_for_curation')
    @patch('sidecar_consolidate.delete_memory')
    @patch('sidecar_consolidate.update_memory')
    def test_curate_memories_skips_update_for_deleted_id(
        self, mock_update, mock_delete, mock_gemini, mock_list
    ):
        import sidecar_consolidate

        user_hash = "abc123"
        mock_list.return_value = [
            {"name": ".../m1", "scope": {"user": user_hash, "project": "global"}, "fact": "fact A"},
        ]
        # Gemini tries to both delete and update the same ID
        mock_gemini.return_value = (["m1"], [{"id": "m1", "new_fact": "rewritten A"}])
        mock_delete.return_value = True

        sidecar_consolidate.curate_memories("my-project", "us-central1", "123", user_hash)

        mock_delete.assert_called_once()
        mock_update.assert_not_called()

    @patch('urllib.request.urlopen')
    @patch('sidecar_consolidate.get_access_token')
    def test_call_gemini_for_curation_parses_response(self, mock_token, mock_urlopen):
        import sidecar_consolidate
        mock_token.return_value = "tok"

        gemini_result = {"to_delete": ["m1"], "to_update": [{"id": "m2", "new_fact": "Always use tabs"}]}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": json.dumps(gemini_result)}]}}]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        memories = [
            {"name": ".../m1", "scope": {"user": "u", "project": "global"}, "fact": "use spaces"},
            {"name": ".../m2", "scope": {"user": "u", "project": "global"}, "fact": "user prefers tabs"},
        ]
        to_delete, to_update = sidecar_consolidate.call_gemini_for_curation(memories, "proj", "us-west1")

        self.assertEqual(to_delete, ["m1"])
        self.assertEqual(len(to_update), 1)
        self.assertEqual(to_update[0]["id"], "m2")
        self.assertEqual(to_update[0]["new_fact"], "Always use tabs")

        req = mock_urlopen.call_args[0][0]
        self.assertIn("gemini-3.5-flash", req.full_url)
        self.assertIn("locations/global", req.full_url)
        self.assertIn("generateContent", req.full_url)

    @patch('urllib.request.urlopen')
    @patch('sidecar_consolidate.get_access_token')
    def test_call_gemini_for_curation_returns_empty_on_failure(self, mock_token, mock_urlopen):
        import sidecar_consolidate
        mock_token.return_value = "tok"
        mock_urlopen.side_effect = Exception("network error")

        to_delete, to_update = sidecar_consolidate.call_gemini_for_curation(
            [{"name": ".../m1", "scope": {"user": "u", "project": "global"}, "fact": "something"}],
            "proj", "us-west1"
        )
        self.assertEqual(to_delete, [])
        self.assertEqual(to_update, [])

    def test_call_gemini_for_curation_returns_empty_for_no_memories(self):
        import sidecar_consolidate
        to_delete, to_update = sidecar_consolidate.call_gemini_for_curation([], "proj", "us-west1")
        self.assertEqual(to_delete, [])
        self.assertEqual(to_update, [])

if __name__ == '__main__':
    unittest.main()
