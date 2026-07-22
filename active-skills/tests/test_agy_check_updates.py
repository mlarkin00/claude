"""Tests for the Stop-hook gate that replaced the check-updates sidecar.

The gate is the whole reason this is safe to hang off `Stop`, which fires at
the end of every agent turn. If it stops holding, every turn pays for a network
call; if it holds too hard, the check never runs again.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts'))
sys.path.insert(0, SCRIPTS)

import agy_check_updates  # noqa: E402


class TestGate(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = os.path.join(self.tmp.name, 'last-check')
        patcher = patch.object(agy_check_updates, 'STATE_PATH', self.state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_due_when_never_checked(self):
        """First run after install must proceed — there is no stamp yet."""
        self.assertTrue(agy_check_updates.due(time.time()))

    def test_not_due_inside_the_interval(self):
        now = time.time()
        agy_check_updates.stamp(now)
        self.assertFalse(agy_check_updates.due(now + 60))

    def test_due_after_the_interval(self):
        now = time.time()
        agy_check_updates.stamp(now)
        self.assertTrue(
            agy_check_updates.due(now + agy_check_updates.INTERVAL_SECONDS + 1)
        )

    def test_corrupt_stamp_reads_as_never_checked(self):
        """A truncated stamp must self-heal rather than silence the check."""
        with open(self.state, 'w') as f:
            f.write('not-a-float')
        self.assertTrue(agy_check_updates.due(time.time()))

    def test_stamp_is_written_before_spawning(self):
        """A checker that hangs must cost one attempt per interval, not per turn."""
        order = []
        with patch.object(agy_check_updates, 'stamp',
                          side_effect=lambda now: order.append('stamp') or True), \
             patch.object(agy_check_updates, 'spawn',
                          side_effect=lambda: order.append('spawn')):
            agy_check_updates.main()
        self.assertEqual(order, ['stamp', 'spawn'])

    def test_no_spawn_when_not_due(self):
        agy_check_updates.stamp(time.time())
        with patch.object(agy_check_updates, 'spawn') as spawn:
            agy_check_updates.main()
        spawn.assert_not_called()

    def test_no_spawn_when_the_stamp_cannot_be_written(self):
        """Without a working gate, spawning every turn is the worse failure."""
        with patch.object(agy_check_updates, 'stamp', return_value=False), \
             patch.object(agy_check_updates, 'spawn') as spawn:
            agy_check_updates.main()
        spawn.assert_not_called()

    def test_checker_target_exists(self):
        """The gate spawns by absolute path; a rename would silently no-op."""
        self.assertTrue(os.path.isfile(agy_check_updates.CHECKER))


class TestHookContract(unittest.TestCase):
    """Run as the hook runs it: a subprocess whose stdout the runtime parses."""

    def run_hook(self, env_extra):
        env = dict(os.environ)
        env.update(env_extra)
        return subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, 'agy_check_updates.py')],
            capture_output=True, text=True, timeout=30, env=env,
        )

    def test_emits_json_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as cache:
            # A fresh cache makes the run "due", so this also covers the path
            # that spawns the detached checker.
            result = self.run_hook({'XDG_CACHE_HOME': cache})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {})
            self.assertTrue(
                os.path.isfile(os.path.join(cache, 'active-skills', 'last-check'))
            )

    def test_survives_an_unwritable_cache(self):
        """A hook must never break the session, however broken the environment."""
        result = self.run_hook({'XDG_CACHE_HOME': '/proc/nonexistent-cache'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})


if __name__ == '__main__':
    unittest.main()
