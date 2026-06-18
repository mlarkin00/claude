import unittest
import json
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
from create_engine import build_payload, parse_operation_response

class TestCreateEngine(unittest.TestCase):
    def test_build_payload_structure(self):
        payload = build_payload("Test Memory", "Test Desc", "test-project", "us-west1")
        self.assertEqual(payload["displayName"], "Test Memory")
        self.assertEqual(payload["description"], "Test Desc")
        cfg = payload["contextSpec"]["memoryBankConfig"]
        # CC version uses gemini-2.0-flash-001
        self.assertIn("gemini-2.0-flash-001", cfg["generationConfig"]["model"])
        self.assertIn("text-embedding-005", cfg["similaritySearchConfig"]["embeddingModel"])
        self.assertIn("31536000s", cfg["ttlConfig"]["memoryRevisionDefaultTtl"])

    def test_parse_operation_response_not_done(self):
        done, engine_id = parse_operation_response({"name": "operations/123", "done": False})
        self.assertFalse(done)
        self.assertIsNone(engine_id)

    def test_parse_operation_response_done(self):
        done, engine_id = parse_operation_response({
            "name": "operations/123",
            "done": True,
            "response": {"name": "projects/p/locations/us-west1/reasoningEngines/998877"}
        })
        self.assertTrue(done)
        self.assertEqual(engine_id, "998877")

    def test_parse_operation_response_done_no_engine_id(self):
        done, engine_id = parse_operation_response({
            "done": True,
            "response": {}
        })
        self.assertTrue(done)
        self.assertIsNone(engine_id)

if __name__ == '__main__':
    unittest.main()
