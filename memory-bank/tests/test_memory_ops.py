import unittest
import sys
import os
import json
import io
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

class TestMemoryOps(unittest.TestCase):
    def setUp(self):
        for m in ['list_memories', 'delete_memory', 'update_memory']:
            sys.modules.pop(m, None)

    @patch('list_memories.list_memories')
    @patch('list_memories.resolve_user_id')
    @patch('list_memories.resolve_project_id')
    def test_list_current_scope_filters_by_user(self, mock_project, mock_user, mock_list):
        mock_user.return_value = "user_abc"
        mock_project.return_value = "project_xyz"
        mock_list.return_value = [
            {"name": ".../m1", "fact": "Fact 1",
             "scope": {"user": "user_abc", "project": "project_xyz"}, "createTime": "2026-06-10T20:00:00Z"},
            {"name": ".../m2", "fact": "Fact 2",
             "scope": {"user": "user_other", "project": "project_xyz"}, "createTime": "2026-06-10T20:01:00Z"},
        ]

        captured = io.StringIO()
        sys.stdout = captured
        import list_memories
        with patch('sys.argv', ['list_memories.py', '--scope', 'current']):
            list_memories.main()
        sys.stdout = sys.__stdout__

        output = captured.getvalue()
        self.assertIn("Fact 1", output)
        self.assertNotIn("Fact 2", output)

    @patch('list_memories.list_memories')
    @patch('list_memories.resolve_user_id')
    @patch('list_memories.resolve_project_id')
    def test_list_all_scope_returns_everything(self, mock_project, mock_user, mock_list):
        mock_user.return_value = "user_abc"
        mock_project.return_value = "project_xyz"
        mock_list.return_value = [
            {"name": ".../m1", "fact": "Fact 1",
             "scope": {"user": "user_abc", "project": "project_xyz"}, "createTime": "2026-06-10T20:00:00Z"},
            {"name": ".../m2", "fact": "Fact 2",
             "scope": {"user": "user_other", "project": "project_xyz"}, "createTime": "2026-06-10T20:01:00Z"},
        ]

        captured = io.StringIO()
        sys.stdout = captured
        import list_memories
        with patch('sys.argv', ['list_memories.py', '--scope', 'all']):
            list_memories.main()
        sys.stdout = sys.__stdout__

        output = captured.getvalue()
        self.assertIn("Fact 1", output)
        self.assertIn("Fact 2", output)

    @patch('delete_memory.delete_memory')
    def test_delete_memory_success(self, mock_delete):
        mock_delete.return_value = True  # CC version returns bool

        captured = io.StringIO()
        sys.stdout = captured
        import delete_memory
        with patch('sys.argv', ['delete_memory.py', 'm1']):
            delete_memory.main()
        sys.stdout = sys.__stdout__

        self.assertIn("Successfully deleted memory 'm1'", captured.getvalue())

    @patch('update_memory.update_memory')
    def test_update_memory_success(self, mock_update):
        mock_update.return_value = {"name": "m1", "fact": "New Fact"}

        captured = io.StringIO()
        sys.stdout = captured
        import update_memory
        with patch('sys.argv', ['update_memory.py', 'm1', 'New Fact']):
            update_memory.main()
        sys.stdout = sys.__stdout__

        self.assertIn("Successfully updated memory 'm1'", captured.getvalue())

if __name__ == '__main__':
    unittest.main()
