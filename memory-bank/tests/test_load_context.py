import unittest
import sys
import os
import json
import io
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

class TestLoadContext(unittest.TestCase):
    @patch('load_context.query_memory_bank')
    def test_output_is_inject_steps_compliant(self, mock_query):
        mock_query.return_value = ["Standard CSS only.", "Max pods 10."]

        captured = io.StringIO()
        sys.stdout = captured
        with patch('sys.stdin', io.StringIO('{"workspacePaths": ["/dummy/root"]}')):
            import load_context
            load_context.run()
        sys.stdout = sys.__stdout__

        output = json.loads(captured.getvalue())
        self.assertIn("injectSteps", output)
        self.assertGreater(len(output["injectSteps"]), 0)
        self.assertIn("ephemeralMessage", output["injectSteps"][0])
        self.assertIn("Standard CSS only.", output["injectSteps"][0]["ephemeralMessage"])

    @patch('load_context.query_memory_bank')
    def test_xml_entities_are_escaped(self, mock_query):
        mock_query.return_value = ["CSS & HTML.", "Pods < 10."]

        captured = io.StringIO()
        sys.stdout = captured
        with patch('sys.stdin', io.StringIO('{"workspacePaths": ["/dummy/root"]}')):
            import load_context
            load_context.run()
        sys.stdout = sys.__stdout__

        ephemeral = json.loads(captured.getvalue())["injectSteps"][0]["ephemeralMessage"]
        self.assertIn("CSS &amp; HTML.", ephemeral)
        self.assertIn("Pods &lt; 10.", ephemeral)

    @patch('load_context.query_memory_bank')
    def test_empty_memories_returns_empty_inject_steps(self, mock_query):
        mock_query.return_value = []

        captured = io.StringIO()
        sys.stdout = captured
        with patch('sys.stdin', io.StringIO('{"workspacePaths": ["/dummy/root"]}')):
            import load_context
            load_context.run()
        sys.stdout = sys.__stdout__

        output = json.loads(captured.getvalue())
        self.assertEqual(output, {"injectSteps": []})

    @patch('load_context.query_memory_bank')
    def test_deduplicates_global_and_project_facts(self, mock_query):
        # Same fact returned from both global and project scopes
        mock_query.return_value = ["Shared fact."]

        captured = io.StringIO()
        sys.stdout = captured
        with patch('sys.stdin', io.StringIO('{"workspacePaths": ["/dummy/root"]}')):
            import load_context
            load_context.run()
        sys.stdout = sys.__stdout__

        ephemeral = json.loads(captured.getvalue())["injectSteps"][0]["ephemeralMessage"]
        # "Shared fact." should appear exactly once
        self.assertEqual(ephemeral.count("Shared fact."), 1)

if __name__ == '__main__':
    unittest.main()
