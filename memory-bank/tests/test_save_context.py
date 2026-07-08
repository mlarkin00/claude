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
            sys.modules.pop('save_context', None)
            import save_context
            save_context.run()

        self.assertFalse(mock_post.called)

if __name__ == '__main__':
    unittest.main()
