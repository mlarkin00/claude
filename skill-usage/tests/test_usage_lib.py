"""Tests for counts storage: sharding, strict reads, and aggregation."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts'))
sys.path.insert(0, SCRIPTS)

import usage_lib  # noqa: E402


class TestMachineId(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.id_path = os.path.join(self.tmp.name, 'machine-id')
        p = patch.object(usage_lib, 'MACHINE_ID_PATH', self.id_path)
        p.start()
        self.addCleanup(p.stop)

    def test_stable_across_calls(self):
        """A re-rolled id per call would create a new shard file every time."""
        first = usage_lib.machine_id()
        self.assertEqual(first, usage_lib.machine_id())
        self.assertTrue(os.path.isfile(self.id_path))

    def test_includes_hostname_and_a_unique_suffix(self):
        """Hostname alone collides across cloud VMs; the suffix breaks ties."""
        ident = usage_lib.machine_id()
        self.assertTrue(ident.startswith(usage_lib._hostname_slug() + '-'), ident)
        self.assertGreater(len(ident), len(usage_lib._hostname_slug()) + 1)

    def test_filename_safe(self):
        with patch.object(usage_lib.socket, 'gethostname',
                          return_value='Weird Host/../name!'):
            ident = usage_lib.machine_id()
        self.assertNotIn('/', ident)
        self.assertEqual(ident, os.path.basename(ident))

    def test_unpersistable_id_is_deterministic(self):
        """If the id cannot be saved, re-rolling would litter a new shard per
        increment. Falling back to the bare hostname keeps one file."""
        with patch.object(usage_lib, 'MACHINE_ID_PATH', '/proc/nope/machine-id'):
            self.assertEqual(usage_lib.machine_id(), usage_lib._hostname_slug())
            self.assertEqual(usage_lib.machine_id(), usage_lib._hostname_slug())


class TestStrictLoad(unittest.TestCase):
    """The read that used to destroy counts."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'counts.json')

    def test_missing_file_is_empty(self):
        self.assertEqual(usage_lib.load(self.path), {})

    def test_unparseable_file_raises(self):
        with open(self.path, 'w') as f:
            f.write('<<<<<<< HEAD\n{"a": 1}\n=======\n{"b": 2}\n>>>>>>> other\n')
        with self.assertRaises(usage_lib.CorruptCounts):
            usage_lib.load(self.path)

    def test_non_object_json_raises(self):
        with open(self.path, 'w') as f:
            json.dump([1, 2, 3], f)
        with self.assertRaises(usage_lib.CorruptCounts):
            usage_lib.load(self.path)

    def test_increment_never_overwrites_an_unreadable_file(self):
        """The regression: a conflicted file used to be replaced by one entry,
        silently discarding every count in it."""
        original = '{"alpha": {"count": 4}, TRUNCATED'
        with open(self.path, 'w') as f:
            f.write(original)
        with patch.object(usage_lib, 'counts_path', return_value=self.path):
            with self.assertRaises(usage_lib.CorruptCounts):
                usage_lib.increment('beta')
        with open(self.path) as f:
            self.assertEqual(f.read(), original)


class TestAggregation(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        os.makedirs(os.path.join(self.repo, usage_lib.COUNTS_DIRNAME))

    def write_shard(self, name, counts):
        path = os.path.join(self.repo, usage_lib.COUNTS_DIRNAME, name + '.json')
        with open(path, 'w') as f:
            json.dump(counts, f)

    def test_totals_sum_across_machines(self):
        self.write_shard('laptop-aaa', {
            'gcloud': {'count': 3, 'last_used_at': '2026-07-01T00:00:00Z'}})
        self.write_shard('desktop-bbb', {
            'gcloud': {'count': 4, 'last_used_at': '2026-07-09T00:00:00Z'},
            'grilling': {'count': 1, 'last_used_at': '2026-07-02T00:00:00Z'}})
        totals = usage_lib.totals(self.repo)
        self.assertEqual(totals['gcloud']['count'], 7)
        self.assertEqual(totals['gcloud']['last_used_at'], '2026-07-09T00:00:00Z')
        self.assertEqual(totals['grilling']['count'], 1)

    def test_legacy_root_file_still_counts(self):
        """Counts predating the split must not silently vanish."""
        with open(os.path.join(self.repo, usage_lib.LEGACY_COUNTS_BASENAME), 'w') as f:
            json.dump({'gcloud': {'count': 5, 'last_used_at': '2026-06-01T00:00:00Z'}}, f)
        self.write_shard('laptop-aaa', {
            'gcloud': {'count': 2, 'last_used_at': '2026-07-01T00:00:00Z'}})
        self.assertEqual(usage_lib.totals(self.repo)['gcloud']['count'], 7)

    def test_one_bad_shard_does_not_hide_the_others(self):
        self.write_shard('good-aaa', {'gcloud': {'count': 2, 'last_used_at': 'z'}})
        path = os.path.join(self.repo, usage_lib.COUNTS_DIRNAME, 'bad-bbb.json')
        with open(path, 'w') as f:
            f.write('not json')
        self.assertEqual(usage_lib.totals(self.repo)['gcloud']['count'], 2)


class TestShardPath(unittest.TestCase):

    def test_relpath_is_inside_the_counts_directory(self):
        with patch.object(usage_lib, 'machine_id', return_value='host-abc123'):
            self.assertEqual(usage_lib.counts_relpath(),
                             os.path.join('skill-usage', 'host-abc123.json'))

    def test_two_machines_never_share_a_path(self):
        with patch.object(usage_lib, 'machine_id', return_value='a-111'):
            first = usage_lib.counts_relpath()
        with patch.object(usage_lib, 'machine_id', return_value='b-222'):
            second = usage_lib.counts_relpath()
        self.assertNotEqual(first, second)


class TestConcurrency(unittest.TestCase):

    def test_parallel_increments_are_not_lost(self):
        """Sessions on one machine share a shard, so the lock still matters."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, 'counts.json')
        snippet = (
            "import sys; sys.path.insert(0, %r); import usage_lib\n"
            "from unittest.mock import patch\n"
            "with patch.object(usage_lib, 'counts_path', return_value=%r):\n"
            "    usage_lib.increment('parallel')\n" % (SCRIPTS, path)
        )
        procs = [subprocess.Popen([sys.executable, '-c', snippet]) for _ in range(16)]
        for p in procs:
            p.wait()
        with open(path) as f:
            self.assertEqual(json.load(f)['parallel']['count'], 16)


if __name__ == '__main__':
    unittest.main()
