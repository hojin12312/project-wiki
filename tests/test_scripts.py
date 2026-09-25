"""Tests for core/scripts (run: python3 -m unittest discover -s tests).

Every test builds an isolated temporary Git repository as a fixture. No real
service, network, or user repository is used.
"""
from __future__ import annotations

import os
import re
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

    def run_commit(self, message, *paths, run="wiki-update"):
        """Commit the way the procedure does: exact paths plus the run trailer.
        A harness trailer in a separate paragraph must not hide it."""
        self.git("add", "--", *paths)
        self.git("commit", "-q", "-m", message, "-m", "Project-Wiki-Run: %s" % run,
                 "-m", "Co-Authored-By: Agent <agent@example.com>", "--", *paths)
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
        self.assertTrue(any("ignored by Git" in m and "results/run.json" in m and "not-preserved" in m
                            for m in warnings))
        self.assertFalse(any("src/app.py" in m or "origin/main" in m or "/v1/models" in m for m in warnings))

    def test_marker_hint_only_for_reproduction_outputs(self):
        self.repo.write("src/draft.py", "x\n")  # uncommitted source
        subprocess.run(["git", "init", "-q", str(self.repo.root / "clone-x")], check=True)
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\n- `src/draft.py`\n- `clone-x/`\n- `src/gone.py`\n")
        warnings = self.messages(wiki_lint.lint(self.repo.root), "warnings")
        draft = [m for m in warnings if "src/draft.py" in m]
        clone = [m for m in warnings if "clone-x" in m]
        gone = [m for m in warnings if "src/gone.py" in m]
        self.assertTrue(draft and "untracked" in draft[0] and "<!-- wiki:not-preserved -->" not in draft[0])
        self.assertTrue(clone and "Git clone" in clone[0] and "<!-- wiki:not-preserved -->" not in clone[0])
        self.assertTrue(gone and "<!-- wiki:not-preserved -->" in gone[0])

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
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\nSee [gone](components/gone.md).<!-- wiki:local-path -->\n")
        self.assertTrue(any("broken link" in m for m in self.messages(wiki_lint.lint(self.repo.root))))

    def test_local_path_marker_scopes_a_boundary_mention(self):
        # An untracked clone or scratch path cited as a local boundary, never as
        # evidence, carries the marker on that one notation.
        subprocess.run(["git", "init", "-q", str(self.repo.root / "clone-x")], check=True)
        (self.repo.root / "scratch").mkdir()
        base = PAGE.format(title="Overview", type="overview", status="current")
        self.repo.write("wiki/overview.md", base
                        + "\n- `clone-x/`<!-- wiki:local-path --> independent clone, local only\n"
                          "- `scratch/`<!-- wiki:local-path --> recreated per session\n"
                          "- `gone/dir/`<!-- wiki:local-path --> no longer present\n")
        warnings = self.messages(wiki_lint.lint(self.repo.root), "warnings")
        self.assertFalse(any("clone-x" in m or "scratch" in m or "gone/dir" in m for m in warnings))
        # The marker covers one notation only: a second, unmarked mention warns.
        self.repo.write("wiki/overview.md", base
                        + "\n- `clone-x/`<!-- wiki:local-path --> boundary\n- `clone-x/` again\n")
        hits = [m for m in self.messages(wiki_lint.lint(self.repo.root), "warnings") if "clone-x" in m]
        self.assertEqual(len(hits), 1)
        self.assertIn("Git clone", hits[0])

    def test_not_preserved_marker_never_marks_a_clone(self):
        # A local clone stays a warning even when marked not-preserved: the
        # marker applies to reproduction outputs only.
        subprocess.run(["git", "init", "-q", str(self.repo.root / "clone-y")], check=True)
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\n- `clone-y/`<!-- wiki:not-preserved -->\n")
        hits = [m for m in self.messages(wiki_lint.lint(self.repo.root), "warnings") if "clone-y" in m]
        self.assertEqual(len(hits), 1)
        self.assertIn("Git clone", hits[0])

    def test_log_inline_paths_are_historical_but_links_still_checked(self):
        # Mentions inside log entries are a historical record: lint keeps the
        # entry structure and real links under review, but never re-warns that
        # a path named in an old entry has since moved or vanished.
        subprocess.run(["git", "init", "-q", str(self.repo.root / "upstream-x")], check=True)
        self.repo.write("wiki/log.md", "# Wiki Log\n\n## [2026-09-22] init | init\n\nSource HEAD: %s\n\n"
                        "Wiki:\n- noted the clone `upstream-x/` and `src/gone.py` locally\n" % self.sha)
        report = wiki_lint.lint(self.repo.root)
        self.assertFalse(any("gone" in m or "upstream-x" in m
                             for m in self.messages(report, "warnings")))
        self.assertEqual(report.errors, [])
        # The same mentions on a live page do warn — the exemption is log-only.
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current")
                        + "\n- `src/gone.py` is gone\n")
        self.assertTrue(any("src/gone.py" in m
                            for m in self.messages(wiki_lint.lint(self.repo.root), "warnings")))
        self.repo.write("wiki/log.md", "# Wiki Log\n\n## [2026-09-22] init | init\n\nSource HEAD: %s\n\n"
                        "See [old page](old-page.md).\n" % self.sha)
        errors = self.messages(wiki_lint.lint(self.repo.root))
        self.assertTrue(any("broken link" in m and "old-page.md" in m for m in errors))

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

    def append_log(self, topic):
        head = self.repo.git("rev-parse", "HEAD")
        log = self.repo.root / "wiki/log.md"
        log.write_text(log.read_text() + "\n## [2026-09-23] update | %s\n\nSource HEAD: %s\n" % (topic, head))

    def test_preflight_reports_a_no_op_window(self):
        # A wiki run's own commit (pages, log, managed block) never shows up as
        # work for the next run, and repeating an update stays a no-op.
        self.repo.write("CLAUDE.md", "# rules\n")
        c2 = self.repo.commit("instructions")
        make_wiki(self.repo, log_sha=c2)
        self.repo.write("CLAUDE.md", "# rules\n<!-- project-wiki:start -->\nb\n<!-- project-wiki:end -->\n")
        self.repo.run_commit("docs(wiki): initialize project memory", "CLAUDE.md", "wiki/SCHEMA.md",
                             "wiki/overview.md", "wiki/current.md", "wiki/index.md", "wiki/log.md", run="wiki-init")
        for _ in range(2):
            out = wiki_state.preflight(self.repo.root)
            self.assertEqual(out["changed_source"], [])
            self.assertEqual(out["changed_source_count"], 0)
            self.assertEqual(out["changed_wiki"], [])
            self.assertFalse(out["changed_source_truncated"])
            self.assertIsNone(out["changed_source_remainder"])
            self.assertIsNone(out["anchor"]["pending_source_head"])
        # A feature commit that also edits a wiki page and the instruction file:
        # both stay visible, once.
        self.repo.write("src/app.py", "v2\n")
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current") + "\nnew\n")
        self.repo.write("CLAUDE.md", "# rules\nmore\n<!-- project-wiki:start -->\nb\n<!-- project-wiki:end -->\n")
        self.repo.commit("feat: v2 with wiki edit")
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual(out["changed_source"], ["M\tCLAUDE.md", "M\tsrc/app.py"])
        feature = self.repo.git("rev-parse", "HEAD")[:12]
        self.assertEqual(out["changed_wiki"], [{"path": "wiki/overview.md", "commits": [feature]}])
        # The run reviews it, keeps the accurate page, and only appends a log entry.
        self.append_log("v2")
        self.repo.run_commit("docs(wiki): update project memory after v2", "wiki/log.md")
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual((out["changed_source"], out["changed_wiki"]), ([], []))

    def test_hand_commit_touching_log_stays_visible(self):
        # A manual commit that edits a page, log.md and the managed block is
        # not a wiki run, even though it looks like one structurally.
        self.repo.write("CLAUDE.md", "# rules\n")
        c2 = self.repo.commit("instructions")
        make_wiki(self.repo, log_sha=c2)
        self.repo.run_commit("docs(wiki): initialize project memory", "wiki/SCHEMA.md", "wiki/overview.md",
                             "wiki/current.md", "wiki/index.md", "wiki/log.md", run="wiki-init")
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current") + "\nhand\n")
        self.repo.write("CLAUDE.md", "# rules\n<!-- project-wiki:start -->\nhand\n<!-- project-wiki:end -->\n")
        log = self.repo.root / "wiki/log.md"
        log.write_text(log.read_text() + "\nhand note\n")
        hand = self.repo.commit("docs(wiki): update project memory after manual fix")[:12]
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual(out["changed_source"], ["M\tCLAUDE.md"])
        self.assertEqual(sorted(e["path"] for e in out["changed_wiki"]), ["wiki/log.md", "wiki/overview.md"])
        self.assertTrue(all(e["commits"] == [hand] for e in out["changed_wiki"]))
        # A trailer does not make a commit that touches source a wiki run.
        self.repo.write("src/app.py", "v3\n")
        self.repo.write("wiki/current.md", PAGE.format(title="Current State", type="current", status="current") + "\nx\n")
        self.repo.run_commit("docs(wiki): sneaky", "src/app.py", "wiki/current.md")
        out = wiki_state.preflight(self.repo.root)
        self.assertIn("M\tsrc/app.py", out["changed_source"])
        self.assertIn("wiki/current.md", [e["path"] for e in out["changed_wiki"]])

    def test_hand_log_entry_cannot_move_the_anchor(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.run_commit("docs(wiki): init", "wiki/SCHEMA.md", "wiki/overview.md", "wiki/current.md",
                             "wiki/index.md", "wiki/log.md", run="wiki-init")
        self.repo.write("src/app.py", "v2\n")
        self.repo.write("wiki/overview.md", PAGE.format(title="Overview", type="overview", status="current") + "\nhand\n")
        m = self.repo.commit("feat + hand wiki edit")
        self.append_log("hand")  # Source HEAD: m, written by hand
        hand = self.repo.commit("docs: hand log entry")
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual(out["anchor"]["anchor"], self.c1)
        self.assertEqual(out["anchor"]["ignored_entries"], [{"source_head": m, "written_by": hand[:12]}])
        self.assertEqual(out["changed_source"], ["M\tsrc/app.py"])
        self.assertEqual(sorted(e["path"] for e in out["changed_wiki"]), ["wiki/log.md", "wiki/overview.md"])
        # A real run that reviewed the range advances the anchor normally.
        self.append_log("reviewed")
        self.repo.run_commit("docs(wiki): update project memory after review", "wiki/log.md")
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual(out["anchor"]["anchor"], hand)
        self.assertEqual((out["changed_source"], out["changed_wiki"]), ([], []))

    def test_entries_from_before_the_trailer_still_count(self):
        # Upgraded wiki: the legacy init entry keeps anchoring until a run
        # entry replaces it; later hand entries do not.
        make_wiki(self.repo, log_sha=self.c1)
        legacy = self.repo.commit("docs(wiki): initialize project memory")
        self.append_log("first 0.7 run")
        self.repo.run_commit("docs(wiki): update project memory after upgrade", "wiki/log.md")
        self.assertEqual(wiki_state.find_anchor(self.repo.root)["anchor"], legacy)
        self.assertEqual(wiki_state.find_anchor(self.repo.root)["ignored_entries"], [])

    def test_untracked_wiki_leftovers_count_as_dirty(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("wiki")
        self.repo.write("wiki/components/leftover.md", "x\n")
        self.assertIn("wiki/components/", wiki_state.preflight(self.repo.root)["dirty_wiki"])

    def test_legacy_run_commit_is_reviewed_once_then_no_op(self):
        # Commits made before the trailer existed are shown once after upgrading.
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("docs(wiki): initialize project memory")
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual(len(out["changed_wiki"]), 5)
        self.append_log("reviewed legacy run")
        self.repo.run_commit("docs(wiki): update project memory after upgrade", "wiki/log.md")
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual((out["changed_source"], out["changed_wiki"]), ([], []))

    def test_fresh_repository_is_not_blocked_by_the_missing_wiki(self):
        out = wiki_state.preflight(self.repo.root)
        self.assertEqual(out["blockers"], [])
        self.assertEqual(out["encoding_errors"], [])
        self.assertFalse(out["wiki_exists"])
        self.assertIsNone(out["schema_version"])
        (self.repo.root / "wiki").mkdir()
        (self.repo.root / "wiki/index.md").write_text("# Project Wiki\n")
        hits = [m for p, m in wiki_lint.lint(self.repo.root).errors if p == "wiki/SCHEMA.md"]
        self.assertEqual(hits, ["mandatory file is missing"])

    def test_run_lock_serializes_runs_in_one_checkout(self):
        first = wiki_state.acquire_lock(self.repo.root, "wiki-update")
        self.assertEqual(first["status"], "acquired")
        second = wiki_state.acquire_lock(self.repo.root, "wiki-update")
        self.assertEqual(second["status"], "held")
        self.assertNotIn("token", second["holder"])
        self.assertIn("--force --id %s" % second["holder"]["id"], second["next"])
        self.assertFalse(self.repo.git("status", "--porcelain"))  # lock lives under .git
        self.assertEqual(wiki_state.release_lock(self.repo.root, "wrong")["status"], "mismatch")
        self.assertTrue(wiki_state.preflight(self.repo.root, lock_token=first["token"])["run_lock"]["owned"])
        self.assertEqual(wiki_state.release_lock(self.repo.root, first["token"])["status"], "released")
        self.assertEqual(wiki_state.release_lock(self.repo.root, first["token"])["status"], "not-held")

    def test_stale_lock_is_never_replaced(self):
        old = wiki_state.acquire_lock(self.repo.root, "wiki-update")
        path = wiki_state.lock_path(self.repo.root)
        before = path.read_bytes()
        past = path.stat().st_mtime - wiki_state.LOCK_STALE_SECONDS - 10
        os.utime(str(path), (past, past))
        self.assertTrue(wiki_state.lock_status(self.repo.root)["stale"])
        # Two runs arriving together at a stale lock: both stop, nothing changes.
        procs = [subprocess.Popen([sys.executable, str(SCRIPTS / "wiki_state.py"), "lock", str(self.repo.root)],
                                  stdout=subprocess.PIPE, text=True) for _ in range(2)]
        results = [__import__("json").loads(p.communicate()[0]) for p in procs]
        self.assertEqual([r["status"] for r in results], ["held", "held"])
        self.assertTrue(all(r["holder"]["stale"] for r in results))
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(wiki_state.lock_status(self.repo.root, old["token"])["owned"])

    def test_force_removes_only_the_named_lock(self):
        old = wiki_state.acquire_lock(self.repo.root, "wiki-update")
        old_id = wiki_state.lock_status(self.repo.root)["id"]
        self.assertEqual(wiki_state.release_lock(self.repo.root, force=True)["status"], "error")
        wiki_state.release_lock(self.repo.root, old["token"])
        new = wiki_state.acquire_lock(self.repo.root, "wiki-update")
        # A force aimed at the old lock must not delete the new one.
        self.assertEqual(wiki_state.release_lock(self.repo.root, force=True, lock_id=old_id)["status"], "mismatch")
        self.assertTrue(wiki_state.lock_status(self.repo.root, new["token"])["owned"])
        new_id = wiki_state.lock_status(self.repo.root)["id"]
        self.assertEqual(wiki_state.release_lock(self.repo.root, force=True, lock_id=new_id)["status"], "released")
        self.assertFalse(list(wiki_state.lock_path(self.repo.root).parent.glob("project-wiki.lock*")))

    def test_only_one_of_many_concurrent_runs_gets_the_lock(self):
        for _ in range(5):
            procs = [subprocess.Popen([sys.executable, str(SCRIPTS / "wiki_state.py"), "lock", str(self.repo.root)],
                                      stdout=subprocess.PIPE, text=True) for _ in range(4)]
            results = [__import__("json").loads(p.communicate()[0]) for p in procs]
            winners = [r for r in results if r["status"] == "acquired"]
            self.assertEqual(len(winners), 1)
            wiki_state.release_lock(self.repo.root, winners[0]["token"])

    def test_edits_since_lock_show_other_writers(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.write("CLAUDE.md", "# rules\n")
        self.repo.commit("wiki")
        mine = wiki_state.acquire_lock(self.repo.root, "wiki-update")
        self.repo.write("wiki/current.md", "mine\n")          # this run's edit
        self.repo.write("wiki/components/new.md", "other\n")  # someone else, untracked
        self.repo.write("CLAUDE.md", "# rules\nother\n")     # someone else, instruction file
        edits = wiki_state.preflight(self.repo.root, lock_token=mine["token"])["run_lock"]["edits_since_lock"]
        self.assertEqual(edits, [
            {"path": "CLAUDE.md", "change": "modified"},
            {"path": "wiki/components/new.md", "change": "added"},
            {"path": "wiki/current.md", "change": "modified"},
        ])

    def test_untracked_entries_match_git_status(self):
        # Issue #21: empty directories and directories whose whole content is
        # excluded are not untracked candidates; the basis is explicit.
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("wiki")
        (self.repo.root / "empty-dir").mkdir()
        (self.repo.root / ".claude" / "worktrees").mkdir(parents=True)
        self.repo.write(".claude/worktrees/state.json", "{}\n")
        exclude = self.repo.root / ".git" / "info" / "exclude"
        exclude.write_text(exclude.read_text() + ".claude/worktrees/\n" if exclude.exists()
                           else ".claude/worktrees/\n")
        self.repo.write("notes/x.txt", "x\n")
        subprocess.run(["git", "init", "-q", str(self.repo.root / "upstream-x")], check=True)
        status = subprocess.run(["git", "-C", str(self.repo.root), "status", "--porcelain", "-z"],
                                check=True, capture_output=True, text=True).stdout
        expected = sorted(p[3:] for p in wiki_state.lines_z(status) if p.startswith("??"))
        out = wiki_state.preflight(self.repo.root)
        reported = sorted(e["path"] for e in out["untracked_entries"])
        self.assertEqual(reported, expected)
        self.assertEqual(reported, ["notes/", "upstream-x/"])
        self.assertEqual(out["untracked_count"], 2)
        self.assertIn("--exclude-standard", out["untracked_basis"]["command"])
        self.assertIn("directory", out["untracked_basis"]["unit"])
        self.assertTrue(any(e["nested_repo"] for e in out["untracked_entries"]))

    def test_untracked_entries_preserve_special_names(self):
        for name in ("한글 메모.txt", "spaced name.txt", "odd\nname.txt"):
            self.repo.write(name, "x\n")
        reported = [e["path"] for e in wiki_state.untracked_entries(self.repo.root)]
        for name in ("한글 메모.txt", "spaced name.txt", "odd\nname.txt"):
            self.assertIn(name, reported)

    def test_lock_records_the_dirty_baseline(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.commit("wiki")
        self.repo.write("src/app.py", "dirty before the run\n")
        self.repo.write("untracked-note.txt", "x\n")
        mine = wiki_state.acquire_lock(self.repo.root, "wiki-update")
        status = wiki_state.lock_status(self.repo.root, mine["token"])
        self.assertEqual(status["dirty_baseline"], ["src/app.py", "untracked-note.txt"])
        # A path in the baseline was dirty before the run's first edit, even
        # after this run also edits wiki files.
        self.repo.write("wiki/current.md", PAGE.format(title="Current", type="current", status="current"))
        status = wiki_state.preflight(self.repo.root, lock_token=mine["token"])["run_lock"]
        self.assertEqual(status["dirty_baseline"], ["src/app.py", "untracked-note.txt"])
        self.assertEqual(status["edits_since_lock"],
                         [{"path": "wiki/current.md", "change": "modified"}])

    def test_budget_command_reports_sections_without_git_investigation(self):
        make_wiki(self.repo, log_sha=self.c1)
        self.repo.write("wiki/current.md", PAGE.format(title="Current State", type="current", status="current")
                        + "\n## Working\n\n- a\n\n## Next Logical Work\n\n- b\n")
        self.repo.commit("wiki")
        out = wiki_state.budget_command(self.repo.root)
        self.assertEqual(out["blockers"], [])
        self.assertNotIn("anchor", out)   # no history/status scan
        self.assertNotIn("changed_source", out)
        self.assertNotIn("untracked_entries", out)
        sections = {s["section"]: s["tokens"] for s in out["budget"]["current_sections"]}
        self.assertIn("<head>", sections)
        self.assertEqual(sections["## Working"], wiki_state.estimate_tokens("## Working\n\n- a\n\n"))
        self.assertIn("## Next Logical Work", sections)
        # Each section estimate truncates the same ASCII/4 fraction the whole-
        # file estimate does once, so the sum never exceeds the file estimate.
        self.assertLessEqual(sum(sections.values()), out["budget"]["current_estimate"])
        # The same report drives preflight's budget block.
        self.assertEqual(wiki_state.preflight(self.repo.root)["budget"]["current_sections"],
                         out["budget"]["current_sections"])

    def test_run_lock_is_per_worktree(self):
        other = Path(self.tmp.name) / "wt"
        self.repo.git("worktree", "add", "-q", str(other))
        self.assertEqual(wiki_state.acquire_lock(self.repo.root, "wiki-update")["status"], "acquired")
        self.assertEqual(wiki_state.acquire_lock(other, "wiki-update")["status"], "acquired")
        self.assertNotEqual(wiki_state.lock_path(self.repo.root).resolve(), wiki_state.lock_path(other).resolve())


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


class SelfUpdateTests(unittest.TestCase):
    """self-update runs one at a time per package (issue #17)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.origin = base / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        (base / "author").mkdir()
        self.author = Repo(base / "author")
        self.author.write("VERSION", "1\n")
        self.author.commit("v1")
        self.author.git("push", "-q", str(self.origin), "HEAD:main")
        self.pkg = base / "pkg"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.pkg)], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self, n):
        self.author.write("VERSION", "%d\n" % n)
        self.author.commit("v%d" % n)
        self.author.git("push", "-q", str(self.origin), "HEAD:main")

    def test_busy_when_another_update_holds_the_package_lock(self):
        held = wiki_state.package_lock(self.pkg, 0)
        try:
            out = wiki_state.self_update(self.pkg, wait=0.5)
        finally:
            held.close()
        self.assertEqual(out["status"], "busy")
        self.assertFalse(out["read_core"])
        self.assertIn("another self-update", out["reason"])
        self.assertEqual(wiki_state.self_update(self.pkg, wait=0.5)["status"], "current")

    def test_concurrent_updates_are_serialized(self):
        code = ("import json, sys; sys.path.insert(0, %r); import wiki_state; from pathlib import Path;"
                " print(json.dumps(wiki_state.self_update(Path(%r))))" % (str(SCRIPTS), str(self.pkg)))
        for n in range(2, 5):
            self.publish(n)
            procs = [subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
                     for _ in range(3)]
            statuses = sorted(__import__("json").loads(p.communicate()[0])["status"] for p in procs)
            self.assertEqual(statuses, ["current", "current", "updated"])
            head = subprocess.run(["git", "-C", str(self.pkg), "rev-parse", "HEAD"],
                                  capture_output=True, text=True).stdout
            main = subprocess.run(["git", "-C", str(self.origin), "rev-parse", "main"],
                                  capture_output=True, text=True).stdout
            self.assertEqual(head, main)


class PackagingTests(unittest.TestCase):
    def test_skill_files_are_entry_points_only(self):
        # The procedure lives in core/ so that a SKILL.md loaded before
        # self-update cannot carry stale steps (issue #11).
        for name, proc in (("wiki-init", "init.md"), ("wiki-update", "update.md")):
            text = (PACKAGE / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertLessEqual(len(text.splitlines()), 30, "%s/SKILL.md grew a procedure" % name)
            self.assertNotRegex(text, r"(?m)^## ", "%s/SKILL.md has procedure sections" % name)
            self.assertIn("self-update", text)
            self.assertIn("`busy`", text)  # stop before reading files mid-replacement (#17)
            self.assertLess(text.index("core/protocol.md"), text.index("core/%s" % proc))
            self.assertTrue((PACKAGE / "core" / proc).is_file())

    def test_schema_migration_notes_cover_the_template_version(self):
        version = (PACKAGE / "core" / "SCHEMA_VERSION").read_text(encoding="utf-8").strip()
        notes = (PACKAGE / "core" / "schema-migrations.md").read_text(encoding="utf-8")
        self.assertRegex(notes, r"(?m)^## %s\b" % re.escape(version))

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
