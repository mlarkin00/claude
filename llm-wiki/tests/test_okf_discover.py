import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import okf_discover as d  # noqa: E402


ROOT_INDEX = """---
okf_version: "0.1"
---

# Pitfall

* [A trap](gotchas/trap.md) - It bites.

# Subdirectories

* [gotchas](gotchas/index.md) - Contains 1 entry.
"""


class DiscoverTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.host = Path(self.tmp.name)
        (self.host / ".git").mkdir()
        self.bundle = self.host / ".agents" / "wiki"
        self.bundle.mkdir(parents=True)
        (self.bundle / "index.md").write_text(ROOT_INDEX, encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "okf_discover.py"), str(self.bundle), *args],
            capture_output=True, text=True,
        )


class TestHostAndMode(DiscoverTestCase):
    def test_host_is_the_nearest_git_root(self):
        self.assertEqual(d.find_host(self.bundle), self.host)

    def test_host_falls_back_to_the_bundle_parent(self):
        (self.host / ".git").rmdir()
        self.assertEqual(d.find_host(self.bundle), self.bundle.parent)

    def test_standalone_claude_md_gets_the_import_mode(self):
        claude = self.host / "CLAUDE.md"
        claude.write_text("# x\n", encoding="utf-8")
        self.assertEqual(d.choose_mode(claude, self.host), d.MODE_IMPORT)

    def test_agents_md_is_always_inlined(self):
        """agy loads AGENTS.md but does not expand `@` imports (verified 2026-07-22,
        agy 1.1.5) — an import line there would be inert text."""
        agents = self.host / "AGENTS.md"
        agents.write_text("# x\n", encoding="utf-8")
        self.assertEqual(d.choose_mode(agents, self.host), d.MODE_INLINE)

    def test_claude_md_symlinked_to_agents_md_is_inlined(self):
        """One shared file has to satisfy the runtime that cannot follow imports."""
        agents = self.host / "AGENTS.md"
        agents.write_text("# x\n", encoding="utf-8")
        claude = self.host / "CLAUDE.md"
        claude.symlink_to(agents)
        self.assertEqual(d.choose_mode(claude, self.host), d.MODE_INLINE)


class TestPlan(DiscoverTestCase):
    def test_a_symlinked_pair_is_planned_once(self):
        agents = self.host / "AGENTS.md"
        agents.write_text("# x\n", encoding="utf-8")
        (self.host / "CLAUDE.md").symlink_to(agents)
        self.assertEqual([p.name for p, _ in d.plan(self.bundle, self.host)], ["CLAUDE.md"])

    def test_gemini_md_yields_to_a_distinct_agents_md(self):
        """agy discovers both, so inlining twice pays for the catalog twice."""
        (self.host / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        (self.host / "GEMINI.md").write_text("# g\n", encoding="utf-8")
        self.assertEqual([p.name for p, _ in d.plan(self.bundle, self.host)], ["AGENTS.md"])

    def test_gemini_md_alone_is_still_installed(self):
        (self.host / "GEMINI.md").write_text("# g\n", encoding="utf-8")
        self.assertEqual([p.name for p, _ in d.plan(self.bundle, self.host)], ["GEMINI.md"])


class TestBlockRendering(DiscoverTestCase):
    def test_import_block_carries_the_at_line(self):
        block = d.render_block(d.MODE_IMPORT, ".agents/wiki", self.bundle)
        self.assertIn("@.agents/wiki/index.md", block)
        self.assertNotIn("A trap", block)

    def test_inline_block_carries_the_catalog(self):
        block = d.render_block(d.MODE_INLINE, ".agents/wiki", self.bundle)
        self.assertIn("A trap", block)
        self.assertNotIn("okf_version", block)

    def test_inlined_links_are_rebased_on_the_host_root(self):
        """Inlined into a repo-root briefing file, a bundle-relative link like
        `gotchas/trap.md` would resolve against the repo root and 404."""
        block = d.render_block(d.MODE_INLINE, ".agents/wiki", self.bundle)
        self.assertIn("](.agents/wiki/gotchas/trap.md)", block)
        self.assertNotIn("](gotchas/trap.md)", block)

    def test_inlined_headings_are_demoted_below_the_host_section(self):
        """A `#` group heading from the index would outrank the briefing file's
        own `##` sections and visually reparent everything after it."""
        block = d.render_block(d.MODE_INLINE, ".agents/wiki", self.bundle)
        self.assertIn("### Pitfall", block)
        self.assertNotIn("\n# Pitfall", block)

    def test_absolute_links_are_left_alone(self):
        body = "* [x](https://example.com) [y](#anchor)"
        self.assertEqual(d._rewrite_links(body, ".agents/wiki"), body)

    def test_missing_root_index_is_an_error(self):
        (self.bundle / "index.md").unlink()
        with self.assertRaises(FileNotFoundError):
            d.render_block(d.MODE_INLINE, ".agents/wiki", self.bundle)


class TestApplyBlock(DiscoverTestCase):
    def test_second_apply_replaces_rather_than_appends(self):
        text = "# Repo\n"
        first = d.apply_block(text, d.render_block(d.MODE_IMPORT, "w", self.bundle), "w")
        second = d.apply_block(first, d.render_block(d.MODE_IMPORT, "w", self.bundle), "w")
        self.assertEqual(first, second)
        self.assertEqual(second.count(d.marker_start("w")), 1)

    def test_content_outside_the_markers_survives(self):
        text = "# Repo\n\nHand-written rule.\n"
        out = d.apply_block(text, d.render_block(d.MODE_IMPORT, "w", self.bundle), "w")
        self.assertIn("Hand-written rule.", out)
        out2 = d.apply_block(out + "\nTrailing note.\n",
                             d.render_block(d.MODE_INLINE, "w", self.bundle), "w")
        self.assertIn("Hand-written rule.", out2)
        self.assertIn("Trailing note.", out2)

    def test_two_bundles_coexist(self):
        text = d.apply_block("# Repo\n", d.render_block(d.MODE_IMPORT, "a", self.bundle), "a")
        text = d.apply_block(text, d.render_block(d.MODE_IMPORT, "b", self.bundle), "b")
        self.assertIn(d.marker_start("a"), text)
        self.assertIn(d.marker_start("b"), text)


class TestCli(DiscoverTestCase):
    def test_install_writes_both_files_in_their_own_modes(self):
        (self.host / "CLAUDE.md").write_text("# c\n", encoding="utf-8")
        (self.host / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("@.agents/wiki/index.md",
                      (self.host / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn("A trap", (self.host / "AGENTS.md").read_text(encoding="utf-8"))

    def test_install_is_idempotent(self):
        (self.host / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        self.run_cli()
        once = (self.host / "AGENTS.md").read_text(encoding="utf-8")
        second = self.run_cli()
        self.assertIn("unchanged", second.stdout)
        self.assertEqual(once, (self.host / "AGENTS.md").read_text(encoding="utf-8"))

    def test_check_fails_when_discovery_is_absent(self):
        (self.host / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING", result.stdout)

    def test_check_fails_when_the_inlined_catalog_drifts(self):
        """The inlined copy is the failure mode this mechanism buys — a doc added
        after install is invisible until the block is refreshed."""
        (self.host / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        self.run_cli()
        (self.bundle / "index.md").write_text(
            ROOT_INDEX.replace("A trap", "A different trap"), encoding="utf-8")
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("STALE", result.stdout)

    def test_sync_refreshes_but_never_creates(self):
        (self.host / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        skipped = self.run_cli("--sync")
        self.assertNotIn("A trap", (self.host / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("skipped", skipped.stdout)
        self.run_cli()
        (self.bundle / "index.md").write_text(
            ROOT_INDEX.replace("A trap", "A renamed trap"), encoding="utf-8")
        self.run_cli("--sync")
        self.assertIn("A renamed trap", (self.host / "AGENTS.md").read_text(encoding="utf-8"))

    def test_no_briefing_file_is_an_error_not_a_silent_success(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("no briefing file", result.stderr)

    def test_create_bootstraps_a_claude_md(self):
        result = self.run_cli("--create")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("@.agents/wiki/index.md",
                      (self.host / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_agents_only_repo_is_warned_about_claude_code(self):
        """Claude Code 2.1.218 does not read AGENTS.md — verified with a codeword
        fixture. An AGENTS.md-only install is half-installed, and silence there
        is how a bundle ends up unread on the runtime it was written for."""
        (self.host / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        result = self.run_cli()
        self.assertIn("does not read AGENTS.md", result.stderr)

    def test_missing_root_index_reports_instead_of_tracebacking(self):
        (self.host / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        (self.bundle / "index.md").unlink()
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("no root index.md", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_bundle_outside_the_host_is_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "okf_discover.py"), str(self.bundle),
                 "--host", other],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("not inside host repo", result.stderr)


if __name__ == "__main__":
    unittest.main()
