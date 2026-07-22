import os
import sys
import unittest
import pathlib
from unittest.mock import patch, mock_open, MagicMock

# Ensure sidecar path can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../sidecars/check-updates')))

class TestCheckUpdates(unittest.TestCase):

    def test_remote_url_targets_the_marketplace_repo(self):
        """The version lives in mlarkin00/plugins, not the skills-authoring repo.

        Every other test in this file mocks urlopen, so none of them can notice
        the URL rotting. This one reads the source: the checker pointed at
        mlarkin00/active-skills, which went skills-only and has no manifest, so
        the fetch 404'd on every run and the check reported "preserving last
        known state" indefinitely.
        """
        src = (pathlib.Path(__file__).resolve().parents[1]
               / "sidecars" / "check-updates" / "check_updates.py").read_text(encoding="utf-8")
        self.assertIn("raw.githubusercontent.com/mlarkin00/plugins", src)
        self.assertIn("/active-skills/plugin.json", src)
        self.assertNotIn("mlarkin00/active-skills/main/plugin.json", src)

    def test_parse_version(self):
        """Test semantic version parsing edge cases and robust formatting."""
        from check_updates import parse_version
        
        # Standard SemVer
        self.assertEqual(parse_version("0.1.4"), (0, 1, 4))
        self.assertEqual(parse_version("10.0.12"), (10, 0, 12))
        
        # Pre-releases, suffixes & metadata
        self.assertEqual(parse_version("0.1.5-beta"), (0, 1, 5))
        self.assertEqual(parse_version("1.0.0-rc1"), (1, 0, 0))
        self.assertEqual(parse_version("2.1.3+build.123"), (2, 1, 3))
        
        # Version Prefixes
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version("V2.0.0-alpha"), (2, 0, 0))
        
        # Incomplete/mismatched segments
        self.assertEqual(parse_version("1"), (1, 0, 0))
        self.assertEqual(parse_version("1.2"), (1, 2, 0))
        
        # Invalid inputs fallback
        self.assertEqual(parse_version("invalid"), (0, 0, 0))
        self.assertEqual(parse_version(""), (0, 0, 0))

    @patch('os.replace')
    @patch('os.makedirs')
    @patch('urllib.request.urlopen')
    @patch('builtins.open')
    @patch('os.path.exists')
    @patch('os.environ.get')
    def test_update_available(self, mock_env, mock_exists, mock_open_func, mock_urlopen, mock_makedirs, mock_replace):
        """Test standard update available flow when no previous status file exists."""
        mock_env.return_value = '/tmp/sidecar_data'
        mock_exists.return_value = False  # No previous status file exists
        
        local_json = '{"name": "active-skills", "version": "0.1.4"}'
        remote_json = b'{"name": "active-skills", "version": "0.1.5"}'
        
        # File-specific mocks to prevent read/write collision
        local_mock = mock_open(read_data=local_json).return_value
        write_mock = mock_open().return_value
        
        def open_side_effect(file, mode='r', *args, **kwargs):
            if 'plugin.json' in str(file):
                return local_mock
            else:
                return write_mock
                
        mock_open_func.side_effect = open_side_effect
        
        mock_response = MagicMock()
        mock_response.read.return_value = remote_json
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        if 'check_updates' in sys.modules:
            del sys.modules['check_updates']
        from check_updates import check_for_updates
        
        status = check_for_updates()
        
        self.assertTrue(status['update_available'])
        self.assertEqual(status['local_version'], '0.1.4')
        self.assertEqual(status['remote_version'], '0.1.5')
        self.assertEqual(status['status'], 'success')
        mock_makedirs.assert_called_once_with('/tmp/sidecar_data', exist_ok=True)
        mock_replace.assert_called_once()

    @patch('os.replace')
    @patch('os.makedirs')
    @patch('urllib.request.urlopen')
    @patch('builtins.open')
    @patch('os.path.exists')
    @patch('os.environ.get')
    def test_network_failure_fallback(self, mock_env, mock_exists, mock_open_func, mock_urlopen, mock_makedirs, mock_replace):
        """Test network failure: cached state should be preserved on connection issues."""
        mock_env.return_value = '/tmp/sidecar_data'
        
        # Simulate that previous check had saved update_available = True
        mock_exists.return_value = True
        prev_status_json = '{"last_checked": "2026-07-10T12:00:00Z", "local_version": "0.1.4", "remote_version": "0.1.5", "update_available": true}'
        local_json = '{"name": "active-skills", "version": "0.1.4"}'
        
        prev_mock = mock_open(read_data=prev_status_json).return_value
        local_mock = mock_open(read_data=local_json).return_value
        write_mock = mock_open().return_value
        
        def open_side_effect(file, mode='r', *args, **kwargs):
            if 'status.json' in str(file) and 'r' in mode:
                return prev_mock
            elif 'plugin.json' in str(file):
                return local_mock
            else:
                return write_mock
                
        mock_open_func.side_effect = open_side_effect
        
        # Simulate a network timeout error
        mock_urlopen.side_effect = Exception("Connection timed out")
        
        if 'check_updates' in sys.modules:
            del sys.modules['check_updates']
        from check_updates import check_for_updates
        
        status = check_for_updates()
        
        # The error status should be caught and cached remote details must be preserved
        self.assertEqual(status['status'], 'error')
        self.assertEqual(status['local_version'], '0.1.4')
        self.assertEqual(status['remote_version'], '0.1.5')
        self.assertTrue(status['update_available'])
        mock_makedirs.assert_called_once_with('/tmp/sidecar_data', exist_ok=True)
        mock_replace.assert_called_once()

if __name__ == '__main__':
    unittest.main()
