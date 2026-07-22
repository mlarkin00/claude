import unittest
import sys
import os
import json
import io
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMMY_TRANSCRIPT = os.path.join(BASE_DIR, 'tests', 'dummy_transcript.jsonl')

class TestSaveContext(unittest.TestCase):
    def tearDown(self):
        for f in [DUMMY_TRANSCRIPT]:
            if os.path.exists(f):
                os.remove(f)
        # Remove cached module so fresh import picks up path changes
        sys.modules.pop('save_context', None)

    @patch('save_context.send_generation_request')
    def test_parses_claude_code_transcript_format(self, mock_post):
        with open(DUMMY_TRANSCRIPT, 'w') as f:
            f.write(json.dumps({"role": "user", "content": "I prefer vanilla CSS."}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": "Understood, using vanilla CSS."}) + "\n")

        stdin = json.dumps({"transcriptPath": DUMMY_TRANSCRIPT, "workspacePaths": ["/dummy/root"]})
        with patch('sys.stdin', io.StringIO(stdin)):
            import save_context
            save_context.run()

        self.assertTrue(mock_post.called)
        events = mock_post.call_args[0][5]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["content"]["role"], "user")
        self.assertEqual(events[1]["content"]["role"], "model")

    @patch('save_context.send_generation_request')
    def test_parses_content_as_list_of_blocks(self, mock_post):
        with open(DUMMY_TRANSCRIPT, 'w') as f:
            f.write(json.dumps({
                "role": "user",
                "content": [{"type": "text", "text": "Use TypeScript."}]
            }) + "\n")
            f.write(json.dumps({
                "role": "assistant",
                "content": [{"type": "text", "text": "Got it, TypeScript."}]
            }) + "\n")

        stdin = json.dumps({"transcriptPath": DUMMY_TRANSCRIPT, "workspacePaths": ["/dummy/root"]})
        with patch('sys.stdin', io.StringIO(stdin)):
            import save_context
            save_context.run()

        self.assertTrue(mock_post.called)
        events = mock_post.call_args[0][5]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["content"]["parts"][0]["text"], "Use TypeScript.")

    @patch('save_context.send_generation_request')
    def test_skips_corrupted_lines(self, mock_post):
        with open(DUMMY_TRANSCRIPT, 'w') as f:
            f.write(json.dumps({"role": "user", "content": "I prefer vanilla CSS."}) + "\n")
            f.write("{invalid_json}\n")
            f.write(json.dumps({"role": "assistant", "content": "Understood."}) + "\n")

        stdin = json.dumps({"transcriptPath": DUMMY_TRANSCRIPT, "workspacePaths": ["/dummy/root"]})
        with patch('sys.stdin', io.StringIO(stdin)):
            import save_context
            save_context.run()

        self.assertTrue(mock_post.called)
        events = mock_post.call_args[0][5]
        self.assertEqual(len(events), 2)

    @patch('save_context.send_generation_request')
    def test_missing_transcript_does_not_call_api(self, mock_post):
        stdin = json.dumps({"transcriptPath": "/nonexistent/path.jsonl", "workspacePaths": ["/dummy/root"]})
        with patch('sys.stdin', io.StringIO(stdin)):
            import save_context
            save_context.run()

        self.assertFalse(mock_post.called)

    # The four cases above all feed Antigravity's protojson camelCase keys, which
    # is precisely why this went unnoticed: the hook was a silent no-op under
    # Claude Code while the suite stayed green. Both payload shapes are asserted
    # from here on.

    @patch('save_context.send_generation_request')
    def test_accepts_claude_code_snake_case_payload(self, mock_post):
        """Claude Code sends transcript_path/cwd, not transcriptPath/workspacePaths."""
        with open(DUMMY_TRANSCRIPT, 'w') as f:
            f.write(json.dumps({"role": "user", "content": "I prefer tabs."}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": "Noted."}) + "\n")

        stdin = json.dumps({
            "session_id": "abc123",
            "transcript_path": DUMMY_TRANSCRIPT,
            "cwd": "/dummy/root",
            "hook_event_name": "Stop",
        })
        with patch('sys.stdin', io.StringIO(stdin)):
            import save_context
            save_context.run()

        self.assertTrue(mock_post.called, "Claude Code payload must reach the API")
        events = mock_post.call_args[0][5]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["content"]["role"], "user")
        self.assertEqual(events[1]["content"]["role"], "model")

    @patch('save_context.send_generation_request')
    def test_camel_case_wins_when_both_keys_present(self, mock_post):
        """A runtime sending both must not get the wrong file."""
        other = DUMMY_TRANSCRIPT + '.other'
        with open(DUMMY_TRANSCRIPT, 'w') as f:
            f.write(json.dumps({"role": "user", "content": "camel"}) + "\n")
        with open(other, 'w') as f:
            f.write(json.dumps({"role": "user", "content": "snake"}) + "\n")
        self.addCleanup(lambda: os.path.exists(other) and os.remove(other))

        stdin = json.dumps({"transcriptPath": DUMMY_TRANSCRIPT, "transcript_path": other})
        with patch('sys.stdin', io.StringIO(stdin)):
            import save_context
            save_context.run()

        events = mock_post.call_args[0][5]
        self.assertEqual(events[0]["content"]["parts"][0]["text"], "camel")

    @patch('save_context.send_generation_request')
    def test_scope_is_global_regardless_of_workspace_key(self, mock_post):
        """Session-end consolidation is always global; no workspace key changes that."""
        with open(DUMMY_TRANSCRIPT, 'w') as f:
            f.write(json.dumps({"role": "user", "content": "scope check"}) + "\n")

        stdin = json.dumps({"transcript_path": DUMMY_TRANSCRIPT, "cwd": "/some/git/project"})
        with patch('sys.stdin', io.StringIO(stdin)):
            import save_context
            save_context.run()

        self.assertEqual(mock_post.call_args[0][4], "global")

if __name__ == '__main__':
    unittest.main()
