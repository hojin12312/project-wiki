"""Tests for core/scripts (run: python3 -m unittest discover -s tests).

Every test builds an isolated temporary Git repository as a fixture. No real
service, network, or user repository is used.
"""
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

<!-- wiki:budgets:start -->
current_tokens: {current_tokens}
bootstrap_tokens: {bootstrap_tokens}
<!-- wiki:budgets:end -->

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

    def write_bytes(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def commit(self, message, *paths):
        self.git("add", *(paths or ["-A"]))
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")


def make_wiki(repo, hosts="", protected="", current="current.md", log_sha=None,
              current_tokens=2000, bootstrap_tokens=6000):
    repo.write("wiki/SCHEMA.md", SCHEMA.format(
        version=wiki_state.template_schema_version(), hosts=hosts, protected=protected,
        current_tokens=current_tokens, bootstrap_tokens=bootstrap_tokens))
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

    def test_log_entry_with_short_sha_warns(self):
        self.repo.write("wiki/log.md", "# Log\n\n## [2026-09-22] update | x\n\nSource HEAD: %s\n" % self.sha[:7])
        warnings = self.messages(wiki_lint.lint(self.repo.root), "warnings")
        self.assertTrue(any("abbreviated" in m for m in warnings))

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

    def test_missing_path_warnings_are_aggregated(self):
        for page in ("overview.md", "current.md"):
            kind = "overview" if page == "overview.md" else "current"
            self.repo.write("wiki/" + page, PAGE.format(title=page, type=kind, status="current")
                            + "\n`src/gone.py` is referenced but missing.\n")
        report = wiki_lint.lint(self.repo.root)
        hits = [(p, m) for p, m in report.warnings if "src/gone.py" in m]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][0], "wiki/current.md, wiki/overview.md")

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
        # An unpreserved-output marker never exempts a Markdown link.
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\nSee [readme](../vendor-clone/README.md).<!-- wiki:not-preserved -->\n")
        warnings = self.messages(wiki_lint.lint(self.repo.root), "warnings")
        self.assertTrue(any("links into protected path" in m for m in warnings))

    def test_unpreserved_output_marker_is_scoped_to_one_notation(self):
        (self.repo.root / "build").mkdir()
        base = PAGE.format(title="Overview", type="overview", status="current")
        self.repo.write("wiki/overview.md", base + "\n- `build/release/report.json` (not preserved)\n")
        hits = [m for m in self.messages(wiki_lint.lint(self.repo.root), "warnings")
                if "build/release/report.json" in m]
        self.assertEqual(len(hits), 1)
        self.repo.write("wiki/overview.md", base
                        + "\n- `build/release/report.json`<!-- wiki:not-preserved --> (not preserved)\n")
        hits = [m for m in self.messages(wiki_lint.lint(self.repo.root), "warnings")
                if "build/release/report.json" in m]
        self.assertEqual(hits, [])
        # The marker applies to the code span next to it, not to the whole page.
        self.repo.write("wiki/overview.md", base
                        + "\n<!-- wiki:not-preserved -->\n\n- `build/release/report.json`\n")
        hits = [m for m in self.messages(wiki_lint.lint(self.repo.root), "warnings")
                if "build/release/report.json" in m]
        self.assertEqual(len(hits), 1)

    def test_marker_does_not_hide_broken_links(self):
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\nSee [gone](components/gone.md).<!-- wiki:not-preserved -->\n")
        self.assertTrue(any("broken link" in m for m in self.messages(wiki_lint.lint(self.repo.root))))

    def test_invalid_utf8_page_is_error(self):
        self.repo.write_bytes("wiki/components/broken.md",
                              PAGE.format(title="Broken", type="component", status="current").encode("utf-8")
                              + b"\ntext \xff\xfe more\n")
        errors = wiki_lint.lint(self.repo.root).errors
        self.assertTrue(any("invalid UTF-8" in m and p.endswith("components/broken.md") for p, m in errors))

    def test_replacement_characters_warn_with_positions(self):
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\n손상 \ufffd 두 개 \ufffd\n")
        hits = [m for m in self.messages(wiki_lint.lint(self.repo.root), "warnings") if "U+FFFD" in m]
        self.assertEqual(len(hits), 1)
        self.assertIn("2 U+FFFD", hits[0])
        self.assertRegex(hits[0], r"\d+:\d+ U\+FFFD")

    def test_normal_unicode_is_not_flagged_but_nul_and_controls_are(self):
        base = PAGE.format(title="Overview", type="overview", status="current")
        self.repo.write("wiki/overview.md", base + "\n한글 😀\ttab\n줄바꿈\n")
        warnings = self.messages(wiki_lint.lint(self.repo.root), "warnings")
        self.assertFalse(any("control" in m or "U+FFFD" in m or "NUL" in m for m in warnings))
        self.repo.write("wiki/overview.md", base + "\nbad \x07 char\n")
        warnings = self.messages(wiki_lint.lint(self.repo.root), "warnings")
        self.assertTrue(any("disallowed control" in m and "U+0007" in m for m in warnings))
        self.repo.write("wiki/overview.md", base + "\nbad \x00 char\n")
        errors = self.messages(wiki_lint.lint(self.repo.root))
        self.assertTrue(any("NUL" in m for m in errors))

    def test_budget_uses_the_same_estimate_as_preflight(self):
        big = PAGE.format(title="Current State", type="current", status="current") + "\n" + "가" * 2100
        self.repo.write("wiki/current.md", big)
        preflight = wiki_state.preflight(self.repo.root)
        report = wiki_lint.lint(self.repo.root)
        self.assertIs(wiki_lint.estimate_tokens, wiki_state.estimate_tokens)
        self.assertEqual(preflight["budget"]["current_estimate"], wiki_state.estimate_tokens(big))
        self.assertEqual(preflight["budget"]["applied_current_path"], "wiki/current.md")
        self.assertEqual(preflight["budget"]["missing"], [])
        self.assertTrue(preflight["budget"]["current_over_budget"])
        self.assertTrue(any("exceeds budget 2000" in m for m in self.messages(report, "warnings")))

    def test_budget_reports_missing_bootstrap_file(self):
        (self.repo.root / "wiki/current.md").unlink()
        preflight = wiki_state.preflight(self.repo.root)
        self.assertIn("wiki/current.md", preflight["budget"]["missing"])
        self.assertIsNone(preflight["budget"]["current_estimate"])

    def test_schema_version_compares_major_minor_only(self):
        major, minor, _ = wiki_state.template_schema_version().split(".")
        schema = self.repo.root / "wiki/SCHEMA.md"
        text = schema.read_text()
        schema.write_text(text.replace(wiki_state.template_schema_version(), "%s.%s.999" % (major, minor)))
        self.assertFalse(any("schema-version" in m for m in self.messages(wiki_lint.lint(self.repo.root), "warnings")))
        schema.write_text(text.replace(wiki_state.template_schema_version(), "%s.%d.0" % (major, int(minor) + 1)))
        self.assertTrue(any("schema-version" in m for m in self.messages(wiki_lint.lint(self.repo.root), "warnings")))

    def test_invalid_utf8_schema_is_an_error(self):
        self.repo.write_bytes("wiki/SCHEMA.md", b"# Wiki Schema\n\nschema-version: 0.2.2\nwiki-language: \xff\n")
        self.assertTrue(any("invalid UTF-8" in m for m in self.messages(wiki_lint.lint(self.repo.root))))
        preflight = wiki_state.preflight(self.repo.root)
        self.assertTrue(any("wiki/SCHEMA.md" in b and "invalid UTF-8" in b for b in preflight["blockers"]))
        self.assertTrue(any(e["path"] == "wiki/SCHEMA.md" for e in preflight["encoding_errors"]))

    def test_multi_host_current(self):
        for f in ("wiki/current.md",):
            (self.repo.root / f).unlink()
        make_wiki(self.repo, hosts="mbp: mbp-hostname\nstudio: studio-hostname", current="current/mbp.md",
                  log_sha=self.sha)
        report = wiki_lint.lint(self.repo.root, host_override="mbp")
        self.assertEqual(report.errors, [])
        self.assertIn(("wiki/current/studio.md", "declared host has no current file yet"), report.warnings)
        self.assertEqual(wiki_state.budget_report(self.repo.root, wiki_state.read_schema(self.repo.root)[0],
                                                  wiki_state.resolve_host(self.repo.root, "mbp"))["applied_current_path"],
                         "wiki/current/mbp.md")
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

    def test_uncommitted_log_entry_is_not_a_confirmed_anchor(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("wiki init")
        self.repo.write("src/app.py", "v2\n")
        c2 = self.repo.commit("c2 source change")
        log = self.repo.root / "wiki/log.md"
        log.write_text(log.read_text() + "\n## [2026-09-23] update | x\n\nSource HEAD: %s\n" % c2)
        anchor = wiki_state.find_anchor(self.repo.root)
        self.assertEqual(anchor["method"], "log-source-head")
        self.assertEqual(anchor["anchor"], self.c1)
        self.assertEqual(anchor["pending_source_head"], c2)
        self.assertEqual(wiki_state.changed_source(self.repo.root, anchor["anchor"]), ["M\tsrc/app.py"])

    def test_corrupt_log_does_not_crash_and_keeps_the_committed_anchor(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("wiki init")
        self.repo.write_bytes("wiki/log.md", b"# Wiki Log\n\n## [2026-09-22] update | x\n\nSource HEAD: \xff\xfe\n")
        anchor = wiki_state.find_anchor(self.repo.root)
        self.assertEqual(anchor["method"], "log-source-head")
        self.assertEqual(anchor["anchor"], self.c1)
        self.assertIn("invalid UTF-8", anchor["log_error"])
        preflight = wiki_state.preflight(self.repo.root)
        self.assertTrue(any(e["path"] == "wiki/log.md" and "invalid UTF-8" in e["message"]
                            for e in preflight["encoding_errors"]))

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
        self.assertEqual(out["staged"]["all"], ["notes.txt"])
        self.assertEqual(out["staged"]["other"], ["notes.txt"])
        self.assertTrue(any(e["nested_repo"] for e in out["untracked_entries"]))
        self.assertEqual(out["untracked_count"], 1)

    def test_preflight_reports_instruction_file_states(self):
        self.repo.write("AGENTS.md", "# rules\n<!-- project-wiki:start -->\nblock\n<!-- project-wiki:end -->\n")
        self.repo.write("CLAUDE.md", "# rules\n")
        self.repo.write(".gitignore", "local-only/\n")
        self.repo.write("local-only/AGENTS.md", "# local rules\n")
        self.repo.commit("instructions")
        self.repo.write("notes/CLAUDE.md", "# notes\n")
        self.repo.write("CLAUDE.md", "# rules\n\nuser work in progress\n")
        out = wiki_state.preflight(self.repo.root)
        states = {entry["path"]: entry for entry in out["instruction_files"]}
        self.assertEqual(states["AGENTS.md"]["state"], "tracked-clean")
        self.assertTrue(states["AGENTS.md"]["managed_block"])
        self.assertEqual(states["CLAUDE.md"]["state"], "tracked-dirty")
        self.assertEqual(states["local-only/AGENTS.md"]["state"], "ignored")
        self.assertEqual(states["notes/CLAUDE.md"]["state"], "untracked")
        self.assertEqual(out["dirty_instruction_files"], ["CLAUDE.md"])

    def test_preflight_classifies_staged_paths(self):
        self.repo.write(".gitignore", "build/\n")
        self.repo.commit("ignore")
        make_wiki(self.repo, hosts="mbp: a\nstudio: b", current="current/mbp.md", log_sha=self.c1)
        self.repo.commit("wiki")
        self.repo.write("wiki/current/studio.md", PAGE.format(title="Studio", type="current", status="current"))
        self.repo.write("wiki/other.md", PAGE.format(title="Other", type="component", status="current"))
        self.repo.write("CLAUDE.md", "# rules\n")
        self.repo.write("src/other.py", "x\n")
        self.repo.git("add", "wiki/current/studio.md", "wiki/other.md", "CLAUDE.md", "src/other.py")
        staged = wiki_state.preflight(self.repo.root, host_override="mbp")["staged"]
        self.assertEqual(staged["all"], sorted(staged["all"]))
        self.assertEqual(staged["wiki_other_hosts"], ["wiki/current/studio.md"])
        self.assertEqual(staged["wiki"], ["wiki/other.md"])
        self.assertEqual(staged["instruction_files"], ["CLAUDE.md"])
        self.assertEqual(staged["other"], ["src/other.py"])

    def test_preflight_blocks_unmapped_host(self):
        make_wiki(self.repo, hosts="mbp: nowhere", current="current/mbp.md")
        self.repo.commit("wiki")
        self.assertTrue(wiki_state.preflight(self.repo.root)["blockers"])

    def test_changed_source_truncation_is_explicit(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("wiki init")
        for i in range(4):
            self.repo.write("src/f%d.py" % i, "x\n")
        self.repo.commit("more sources")
        original = wiki_state.MAX_LIST
        wiki_state.MAX_LIST = 2
        try:
            out = wiki_state.preflight(self.repo.root)
        finally:
            wiki_state.MAX_LIST = original
        self.assertEqual(out["changed_source_count"], 4)
        self.assertTrue(out["changed_source_truncated"])
        self.assertEqual(len(out["changed_source"]), 2)
        self.assertEqual(out["changed_source_remainder"]["remaining"], 2)
        self.assertIn("diff --name-status", out["changed_source_remainder"]["command"])

    def test_preflight_reports_a_no_op_window(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("wiki init")
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual(out["changed_source"], [])
        self.assertEqual(out["changed_source_count"], 0)
        self.assertFalse(out["changed_source_truncated"])
        self.assertIsNone(out["changed_source_remainder"])
        self.assertIsNone(out["anchor"]["pending_source_head"])


PACKAGE = Path(__file__).resolve().parents[1]
TEMPLATE = (PACKAGE / "core" / "SCHEMA.template.md").read_text(encoding="utf-8")


def render_template(hosts="", protected=""):
    return (TEMPLATE
            .replace("{{SCHEMA_VERSION}}", wiki_state.template_schema_version())
            .replace("{{WIKI_LANGUAGE}}", "ko (identifiers and paths stay in English)")
            .replace("{{HOSTS}}", hosts)
            .replace("{{PROTECTED_PATHS}}", protected))


class TemplateTests(unittest.TestCase):
    """A wiki scaffolded from the shipped template must be parseable and lint-clean."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(Path(self.tmp.name))
        self.repo.write("src/app.py", "print('x')\n")
        self.sha = self.repo.commit("src")

    def tearDown(self):
        self.tmp.cleanup()

    def test_template_scaffolds_a_clean_wiki(self):
        self.repo.write("wiki/SCHEMA.md", render_template())
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current"))
        self.repo.write("wiki/current.md", PAGE.format(title="Current State", type="current", status="current"))
        self.repo.write("wiki/index.md", "# Project Wiki\n\n- [Overview](overview.md) — o.\n- [Current](current.md) — c.\n")
        self.repo.write("wiki/log.md", "# Wiki Log\n\n## [2026-09-23] init | init\n\nSource HEAD: %s\n" % self.sha)
        self.repo.commit("wiki")
        preflight = wiki_state.preflight(self.repo.root)
        self.assertEqual(preflight["blockers"], [])
        self.assertEqual(preflight["budget"]["current_tokens"], 2000)
        self.assertEqual(preflight["budget"]["bootstrap_tokens"], 6000)
        self.assertEqual(preflight["budget"]["missing"], [])
        self.assertEqual(wiki_state.protected_paths(TEMPLATE), [])
        self.assertEqual(wiki_lint.lint(self.repo.root).errors, [])

    def test_template_hosts_and_protected_blocks_parse(self):
        self.repo.write("wiki/SCHEMA.md", render_template(hosts="mbp: mbp-hostname", protected="vendor-clone/"))
        schema_text, error = wiki_state.read_schema(self.repo.root)
        self.assertIsNone(error)
        self.assertEqual(wiki_state.parse_hosts(schema_text), {"mbp": ["mbp-hostname"]})
        self.assertEqual(wiki_state.protected_paths(schema_text), ["vendor-clone"])


class PackagingTests(unittest.TestCase):
    def test_skill_files_stay_thin(self):
        for name in ("wiki-init", "wiki-update"):
            text = (PACKAGE / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertLessEqual(len(text.splitlines()), 150, "%s/SKILL.md exceeds 150 lines" % name)

    def test_release_metadata_is_consistent(self):
        version = (PACKAGE / "VERSION").read_text(encoding="utf-8").strip()
        schema_version = (PACKAGE / "core" / "SCHEMA_VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertRegex(schema_version, r"^\d+\.\d+\.\d+$")
        self.assertIn("## %s" % version, (PACKAGE / "CHANGELOG.md").read_text(encoding="utf-8"))

    def test_install_paths_match_the_skill_fallbacks(self):
        install = (PACKAGE / "install.sh").read_text(encoding="utf-8")
        self.assertIn(".config/opencode/skills", install)
        for name in ("wiki-init", "wiki-update"):
            skill = (PACKAGE / name / "SKILL.md").read_text(encoding="utf-8")
            for fallback in ("~/.claude/skills/%s" % name, "~/.agents/skills/%s" % name,
                             "~/.config/opencode/skills/%s" % name):
                self.assertIn(fallback, skill)


if __name__ == "__main__":
    unittest.main()
