import unittest
import sys
import os
import json
import io
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

def load(fmt=None):
    """Run the loader and return its parsed stdout. Default format when None."""
    captured = io.StringIO()
    sys.stdout = captured
    try:
        with patch('sys.stdin', io.StringIO('{"workspacePaths": ["/dummy/root"]}')):
            import load_context
            load_context.run() if fmt is None else load_context.run(fmt)
    finally:
        sys.stdout = sys.__stdout__
    return json.loads(captured.getvalue())


def injected(output):
    """Pull the injected text out of either runtime's payload shape."""
    if "injectSteps" in output:
        steps = output["injectSteps"]
        return steps[0]["ephemeralMessage"] if steps else ""
    return output.get("hookSpecificOutput", {}).get("additionalContext", "")


class TestLoadContext(unittest.TestCase):
    """The default (no-flag) format is Claude Code's — that is how hooks/hooks.json
    invokes the script. Emitting Antigravity's shape there exits 0 and injects
    nothing, which is the failure this suite exists to catch."""

    @patch('load_context.query_memory_bank')
    def test_default_output_is_claude_session_start_compliant(self, mock_query):
        mock_query.return_value = ["Standard CSS only.", "Max pods 10."]

        output = load()

        self.assertNotIn("injectSteps", output)
        self.assertIn("hookSpecificOutput", output)
        hook_output = output["hookSpecificOutput"]
        self.assertEqual(hook_output["hookEventName"], "SessionStart")
        # Non-empty is the assertion that matters: the old bug exited 0 with a
        # full stdout and an empty injection.
        self.assertTrue(hook_output["additionalContext"])
        self.assertIn("Standard CSS only.", hook_output["additionalContext"])

    @patch('load_context.query_memory_bank')
    def test_agy_output_is_inject_steps_compliant(self, mock_query):
        mock_query.return_value = ["Standard CSS only.", "Max pods 10."]

        output = load("agy")

        self.assertNotIn("hookSpecificOutput", output)
        self.assertGreater(len(output["injectSteps"]), 0)
        self.assertIn("ephemeralMessage", output["injectSteps"][0])
        self.assertIn("Standard CSS only.", output["injectSteps"][0]["ephemeralMessage"])

    def test_agy_loader_requests_the_agy_format(self):
        # The agy hook caches and replays the loader's stdout untouched, so it
        # must ask for its own shape rather than inherit the Claude default.
        import agy_load_context
        self.assertEqual(agy_load_context.LOADER_ARGS, ["--format", "agy"])

    @patch('load_context.query_memory_bank')
    def test_xml_entities_are_escaped(self, mock_query):
        mock_query.return_value = ["CSS & HTML.", "Pods < 10."]

        for fmt in (None, "agy"):
            with self.subTest(fmt=fmt or "claude"):
                text = injected(load(fmt))
                self.assertIn("CSS &amp; HTML.", text)
                self.assertIn("Pods &lt; 10.", text)

    @patch('load_context.query_memory_bank')
    def test_empty_memories_injects_nothing(self, mock_query):
        mock_query.return_value = []

        self.assertEqual(load(), {})
        self.assertEqual(load("agy"), {"injectSteps": []})

    @patch('load_context.query_memory_bank')
    def test_deduplicates_global_and_project_facts(self, mock_query):
        # Same fact returned from both global and project scopes
        mock_query.return_value = ["Shared fact."]

        for fmt in (None, "agy"):
            with self.subTest(fmt=fmt or "claude"):
                # "Shared fact." should appear exactly once
                self.assertEqual(injected(load(fmt)).count("Shared fact."), 1)

if __name__ == '__main__':
    unittest.main()
