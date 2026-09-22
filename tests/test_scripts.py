"""Tests for core/scripts (run: python3 -m unittest discover -s tests)."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "core" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import wiki_lint  # noqa: E402
import wiki_state  # noqa: E402

PAGE = """---
title: {title}
type: {type}
status: {status}
updated: 2026-09-22
---

# {title}
"""

SCHEMA = """# Wiki Schema

schema-version: {version}
wiki-language: ko

<!-- wiki:hosts:start -->
{hosts}
<!-- wiki:hosts:end -->

<!-- wiki:protected:start -->
{protected}
<!-- wiki:protected:end -->
"""


class Repo:
    def __init__(self, root: Path):
        self.root = root
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "test")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text), encoding="utf-8")

    def commit(self, message, *paths):
        self.git("add", *(paths or ["-A"]))
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")


def make_wiki(repo, hosts="", protected="", current="current.md", log_sha=None):
    repo.write("wiki/SCHEMA.md", SCHEMA.format(version=wiki_state.template_schema_version(), hosts=hosts, protected=protected))
    repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current"))
    repo.write("wiki/" + current, PAGE.format(title="Current State", type="current", status="current"))
    repo.write("wiki/index.md", "# Project Wiki\n\n- [Overview](overview.md) — o.\n- [Current](%s) — c.\n" % current)
    repo.write("wiki/log.md", "# Wiki Log\n\n## [2026-09-22] init | init\n\nSource HEAD: %s\n" % (log_sha or "0000000"))


class LintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(Path(self.tmp.name))
        self.repo.write("src/app.py", "print('x')\n")
        self.sha = self.repo.commit("src")
        make_wiki(self.repo, log_sha=self.sha)

    def tearDown(self):
        self.tmp.cleanup()

    def messages(self, report, kind="errors"):
        return [m for _, m in getattr(report, kind)]

    def test_clean_wiki_passes(self):
        report = wiki_lint.lint(self.repo.root)
        self.assertEqual(report.errors, [])

    def test_broken_link(self):
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\nSee [gone](components/gone.md).\n")
        self.assertTrue(any("broken link" in m for m in self.messages(wiki_lint.lint(self.repo.root))))

    def test_links_inside_code_are_ignored(self):
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\n```markdown\n[x](nowhere.md)\n```\n")
        self.assertEqual(wiki_lint.lint(self.repo.root).errors, [])

    def test_page_missing_from_index(self):
        self.repo.write("wiki/components/cache.md", PAGE.format(title="Cache", type="component", status="current"))
        errors = self.messages(wiki_lint.lint(self.repo.root))
        self.assertTrue(any("not reachable from wiki/index.md (orphan" in m for m in errors))

    def test_category_index_reachability(self):
        self.repo.write("wiki/components/cache.md", PAGE.format(title="Cache", type="component", status="current"))
        self.repo.write("wiki/components/index.md", "# Components\n\n- [Cache](cache.md) — c.\n")
        self.repo.write("wiki/index.md", "# Wiki\n\n- [Overview](overview.md) — o.\n- [Current](current.md) — c.\n"
                        "- [Components](components/index.md) — list.\n")
        self.assertEqual(wiki_lint.lint(self.repo.root).errors, [])

    def test_invalid_status_and_missing_frontmatter(self):
        self.repo.write("wiki/decisions/0001-x.md", PAGE.format(title="X", type="decision", status="current"))
        self.repo.write("wiki/runbooks/deploy.md", "# Deploy\n")
        self.repo.write("wiki/index.md", "# W\n\n- [O](overview.md) — o.\n- [C](current.md) — c.\n"
                        "- [X](decisions/0001-x.md) — x.\n- [D](runbooks/deploy.md) — d.\n")
        errors = self.messages(wiki_lint.lint(self.repo.root))
        self.assertTrue(any("invalid status 'current' for type decision" in m for m in errors))
        self.assertTrue(any("missing frontmatter" in m for m in errors))

    def test_log_entry_without_source_head(self):
        self.repo.write("wiki/log.md", "# Log\n\n## [2026-09-22] update | x\n\nWiki:\n- y\n")
        self.assertTrue(any("Source HEAD" in m for m in self.messages(wiki_lint.lint(self.repo.root))))

    def test_gitignored_wiki_page(self):
        self.repo.write(".gitignore", "*token*\n")
        self.repo.write("wiki/components/token-logging.md", PAGE.format(title="T", type="component", status="current"))
        errors = self.messages(wiki_lint.lint(self.repo.root))
        self.assertTrue(any("ignored by .gitignore" in m for m in errors))

    def test_path_references(self):
        self.repo.write("results/run.json", "{}\n")
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\n- `src/app.py` ok\n- `src/missing.py` gone\n- `results/run.json` local only\n"
                          "- `origin/main` not a path\n- `/v1/models` endpoint\n")
        self.repo.write(".gitignore", "results/\n")
        warnings = self.messages(wiki_lint.lint(self.repo.root), "warnings")
        self.assertTrue(any("does not exist: src/missing.py" in m for m in warnings))
        self.assertTrue(any("untracked or ignored" in m and "results/run.json" in m for m in warnings))
        self.assertFalse(any("src/app.py" in m or "origin/main" in m or "/v1/models" in m for m in warnings))

    def test_protected_paths_warn_only_for_links(self):
        make_wiki(self.repo, protected="vendor-clone/", log_sha=self.sha)
        self.repo.write("vendor-clone/README.md", "x\n")
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\n- `vendor-clone/` is an independent clone we never touch.\n")
        warnings = self.messages(wiki_lint.lint(self.repo.root), "warnings")
        self.assertFalse(any("vendor-clone" in m for m in warnings))
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\nSee [readme](../vendor-clone/README.md).\n")
        warnings = self.messages(wiki_lint.lint(self.repo.root), "warnings")
        self.assertTrue(any("links into protected path" in m for m in warnings))

    def test_schema_version_compares_major_minor_only(self):
        major, minor, _ = wiki_state.template_schema_version().split(".")
        schema = self.repo.root / "wiki/SCHEMA.md"
        text = schema.read_text()
        schema.write_text(text.replace(wiki_state.template_schema_version(), "%s.%s.999" % (major, minor)))
        self.assertFalse(any("schema-version" in m for m in self.messages(wiki_lint.lint(self.repo.root), "warnings")))
        schema.write_text(text.replace(wiki_state.template_schema_version(), "%s.%d.0" % (major, int(minor) + 1)))
        self.assertTrue(any("schema-version" in m for m in self.messages(wiki_lint.lint(self.repo.root), "warnings")))

    def test_multi_host_current(self):
        for f in ("wiki/current.md",):
            (self.repo.root / f).unlink()
        make_wiki(self.repo, hosts="mbp: mbp-hostname\nstudio: studio-hostname", current="current/mbp.md",
                  log_sha=self.sha)
        report = wiki_lint.lint(self.repo.root, host_override="mbp")
        self.assertEqual(report.errors, [])
        self.assertIn(("wiki/current/studio.md", "declared host has no current file yet"), report.warnings)
        report = wiki_lint.lint(self.repo.root, host_override="studio")
        self.assertTrue(any("current file for this host is missing" in m for m in self.messages(report)))


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(Path(self.tmp.name))
        self.repo.write("src/app.py", "v1\n")
        self.c1 = self.repo.commit("c1")

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("WIKI_HOST", None)

    def test_anchor_survives_manual_wiki_edit(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("wiki init")
        self.repo.write("src/app.py", "v2\n")
        self.repo.commit("c2 source change")
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview!", type="overview", status="current"))
        self.repo.commit("manual wiki edit")
        anchor = wiki_state.find_anchor(self.repo.root)
        self.assertEqual(anchor["method"], "log-source-head")
        self.assertEqual(anchor["anchor"], self.c1)
        changes = wiki_state.changed_source(self.repo.root, anchor["anchor"])
        self.assertEqual(changes, ["M\tsrc/app.py"])

    def test_anchor_falls_back_when_sha_vanished(self):
        make_wiki(self.repo, log_sha="deadbeef")
        sha = self.repo.commit("wiki init")
        anchor = wiki_state.find_anchor(self.repo.root)
        self.assertEqual((anchor["method"], anchor["anchor"]), ("log-commit", sha))

    def test_multi_host_prefers_own_entry(self):
        make_wiki(self.repo, hosts="mbp: a\nstudio: b", current="current/mbp.md", log_sha=self.c1)
        self.repo.write("src/app.py", "v2\n")
        c2 = self.repo.commit("c2")
        log = self.repo.root / "wiki/log.md"
        log.write_text(log.read_text() + "\n## [2026-09-23] update | x\n\nHost: studio\nSource HEAD: %s\n" % c2)
        self.repo.write("wiki/log.md", log.read_text().replace("Source HEAD: %s\n" % self.c1,
                                                                "Host: mbp\nSource HEAD: %s\n" % self.c1, 1))
        self.repo.commit("wiki")
        self.assertEqual(wiki_state.find_anchor(self.repo.root, "mbp")["anchor"], self.c1)
        self.assertEqual(wiki_state.find_anchor(self.repo.root, "studio")["anchor"], c2)

    def test_host_resolution(self):
        make_wiki(self.repo, hosts="mbp: %s" % wiki_state.local_hostname(), current="current/mbp.md")
        self.assertEqual(wiki_state.resolve_host(self.repo.root)["host"], "mbp")
        make_wiki(self.repo, hosts="mbp: some-other-machine", current="current/mbp.md")
        result = wiki_state.resolve_host(self.repo.root)
        self.assertIsNone(result["host"])
        self.assertIn("not mapped", result["error"])
        make_wiki(self.repo, hosts="", current="current.md")
        self.assertEqual(wiki_state.resolve_host(self.repo.root)["current_path"], "wiki/current.md")

    def test_preflight_reports_staged_and_untracked_nested_repo(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("wiki")
        self.repo.write("notes.txt", "user work\n")
        self.repo.git("add", "notes.txt")
        nested = self.repo.root / "upstream-x"
        nested.mkdir()
        subprocess.run(["git", "init", "-q", str(nested)], check=True)
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual(out["blockers"], [])
        self.assertEqual(out["staged"], ["notes.txt"])
        self.assertTrue(any(e["nested_repo"] for e in out["untracked_entries"]))

    def test_preflight_reports_dirty_instruction_files(self):
        self.repo.write("CLAUDE.md", "# rules\n")
        self.repo.write("sub/AGENTS.md", "# sub rules\n")
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("wiki and instructions")
        self.repo.write("CLAUDE.md", "# rules\n\nuser work in progress\n")
        self.repo.write("sub/AGENTS.md", "# sub rules\n\nstaged work\n")
        self.repo.git("add", "sub/AGENTS.md")
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual(out["dirty_instruction_files"], ["CLAUDE.md", "sub/AGENTS.md"])

    def test_preflight_blocks_unmapped_host(self):
        make_wiki(self.repo, hosts="mbp: nowhere", current="current/mbp.md")
        self.repo.commit("wiki")
        self.assertTrue(wiki_state.preflight(self.repo.root)["blockers"])


if __name__ == "__main__":
    unittest.main()
