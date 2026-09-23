#!/usr/bin/env python3
"""Structural linter for a repository's wiki/ directory.

Usage: wiki_lint.py [repo-root] [--host NAME] [--json]

Exit code 0 = no structural errors, 1 = structural errors found.
Warnings never change the exit code. Semantic checks (code vs wiki
contradictions, stale state) are left to the agent on purpose.

Standard library only; Python 3.8+.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wiki_state  # noqa: E402

GENERAL_STATUS = {"current", "partial", "deprecated", "archived"}
STATUS_BY_TYPE = {
    "overview": GENERAL_STATUS,
    "current": GENERAL_STATUS,
    "architecture": GENERAL_STATUS,
    "component": GENERAL_STATUS,
    "runbook": GENERAL_STATUS,
    "decision": {"proposed", "accepted", "rejected", "superseded"},
    "experiment": {"planned", "running", "completed", "inconclusive"},
}
MANDATORY = ["SCHEMA.md", "index.md", "overview.md", "log.md"]
NON_SUBSTANTIVE = {"SCHEMA.md", "index.md", "log.md"}

FENCE_RE = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*$", re.M | re.S)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
LOG_HEADING_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]", re.M)
# Marker for an output path that is intentionally not preserved (for example a
# build or report path). It must sit right after the specific code span; it
# never exempts a page, a section, or a Markdown link.
NOT_PRESERVED_RE = re.compile(r"<!--\s*wiki:not-preserved\s*-->")
PATH_BAD_CHARS = set("<>*{}$|()[]'\" ")
MARKER_HINT = (" (if it is a reproduction output that exists only after re-running something, append"
               " <!-- wiki:not-preserved --> right after that code span and keep the key numbers,"
               " conditions, and revision in the page body)")
PATH_MESSAGES = {
    "missing": "referenced path does not exist: %s" + MARKER_HINT,
    "ignored": "referenced path is ignored by Git (absent in other checkouts): %s" + MARKER_HINT,
    "untracked": "referenced path is untracked (absent in other checkouts): %s (uncommitted source is not"
                 " a reproduction output: leave it unmarked until it is committed, or drop the reference)",
    "clone": "referenced path is an untracked Git clone (absent in other checkouts): %s (do not mark it"
             " not-preserved; describe it without citing it as evidence, or protect it in SCHEMA)",
}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    def error(self, path, message):
        self.errors.append((path, message))

    def warn(self, path, message):
        self.warnings.append((path, message))


def strip_fences(text):
    return FENCE_RE.sub("", text)


def frontmatter(text):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip("'\"")
    return fields


# Shared with preflight, so both report identical budget numbers.
estimate_tokens = wiki_state.estimate_tokens


def format_positions(items, limit=5):
    shown = ", ".join("%d:%d %s" % (line, column, code) for line, column, code in items[:limit])
    if len(items) > limit:
        shown += ", ... (%d more)" % (len(items) - limit)
    return shown


def integrity_problems(rel, defects):
    """Severity and message per defect class. Messages never quote content."""
    problems = []
    if defects["nul"]:
        problems.append(("error", rel, "contains %d NUL character(s) at %s" % (
            len(defects["nul"]), format_positions(defects["nul"]))))
    if defects["control"]:
        problems.append(("warning", rel, "contains %d disallowed control character(s) at %s" % (
            len(defects["control"]), format_positions(defects["control"]))))
    if defects["replacement"]:
        problems.append(("warning", rel, "contains %d U+FFFD replacement character(s) at %s; "
            "this usually means a decode or encoding loss. Verify against the source and repair by hand; "
            "lint never rewrites the file" % (
                len(defects["replacement"]), format_positions(defects["replacement"]))))
    return problems


def is_substantive(rel):
    parts = rel.parts
    return not (parts[0] == "archive" or rel.name in NON_SUBSTANTIVE)


def tracked_paths(root):
    proc = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True)
    files = set(p for p in proc.stdout.split("\0") if p)
    dirs = set()
    for f in files:
        parent = Path(f).parent
        while str(parent) not in (".", ""):
            dirs.add(str(parent))
            parent = parent.parent
    return files, dirs


def is_ignored(root, rel):
    proc = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", "--", rel], capture_output=True)
    return proc.returncode == 0


def link_targets(page, text, root):
    """Yield (raw, resolved Path or None) for relative links outside code."""
    for match in LINK_RE.finditer(INLINE_CODE_RE.sub("", strip_fences(text))):
        raw = match.group(1)
        if SCHEME_RE.match(raw) or raw.startswith("#"):
            continue
        target = unquote(raw.split("#", 1)[0].split("?", 1)[0])
        if not target:
            continue
        base = root if target.startswith("/") else page.parent
        yield raw, (base / target.lstrip("/")).resolve()


def lint(root, host_override=None):
    root = Path(root).resolve()
    wiki = root / "wiki"
    report = Report()
    if not wiki.is_dir():
        report.error("wiki/", "wiki directory does not exist")
        return report

    schema_text, schema_error = wiki_state.read_schema(root)
    if schema_error:
        report.error("wiki/SCHEMA.md", schema_error)
    schema_text = schema_text or ""
    host = wiki_state.resolve_host(root, host_override)

    for name in MANDATORY:
        if not (wiki / name).is_file():
            report.error("wiki/" + name, "mandatory file is missing")
    if host["mode"] == "single":
        if not (wiki / "current.md").is_file():
            report.error("wiki/current.md", "mandatory file is missing")
    else:
        if host["error"]:
            report.warn("wiki/SCHEMA.md", host["error"])
        elif not (root / host["current_path"]).is_file():
            report.error(host["current_path"], "current file for this host is missing")
        for other in host["declared_hosts"]:
            if not (wiki / "current" / ("%s.md" % other)).is_file() and other != host["host"]:
                report.warn("wiki/current/%s.md" % other, "declared host has no current file yet")
        if (wiki / "current.md").exists():
            report.warn("wiki/current.md", "multi-host wiki should use current/<host>.md instead")

    pages = sorted(p for p in wiki.rglob("*.md") if p.is_file())
    texts = {}
    for page in pages:
        rel = str(page.relative_to(root))
        text, error = wiki_state.read_text(page)
        if error:
            report.error(rel, error)
            continue
        texts[page] = text
        for kind, path, message in integrity_problems(rel, wiki_state.text_defects(text)):
            (report.error if kind == "error" else report.warn)(path, message)

    protected = wiki_state.protected_paths(schema_text)

    def in_protected(rel):
        return any(rel == p or rel.startswith(p + "/") for p in protected)

    # Links: broken targets and inbound graph.
    inbound = {p: 0 for p in pages}
    for page, text in texts.items():
        for raw, target in link_targets(page, text, root):
            rel_page = page.relative_to(root)
            try:
                rel_target = target.relative_to(root).as_posix()
            except ValueError:
                report.warn(str(rel_page), "link points outside the repository: %s" % raw)
                continue
            if in_protected(rel_target):
                # Mentioning a protected path (e.g. to document boundaries) is fine;
                # linking to it as evidence is not.
                report.warn(str(rel_page), "links into protected path (do not use it as evidence): %s" % raw)
                continue
            if not target.exists():
                report.error(str(rel_page), "broken link: %s" % raw)
            elif target in inbound and target != page:
                inbound[target] += 1

    # Index reachability through index.md files.
    indexed, seen_index, queue = set(), set(), [wiki / "index.md"]
    while queue:
        index = queue.pop()
        if index in seen_index or not index.is_file():
            continue
        seen_index.add(index)
        targets_here = []
        for raw, target in link_targets(index, texts.get(index, ""), root):
            if target.suffix != ".md" or not target.is_file():
                continue
            targets_here.append(target)
            indexed.add(target)
            if target.name == "index.md":
                queue.append(target)
        for dup in sorted(set(t for t in targets_here if targets_here.count(t) > 1)):
            report.warn(str(index.relative_to(root)), "duplicate index entry: %s" % dup.relative_to(root))

    titles = {}
    for page in pages:
        rel = page.relative_to(wiki)
        rel_root = str(page.relative_to(root))
        if page not in texts:
            continue  # decode error already reported
        if not is_substantive(rel):
            continue
        if page not in indexed:
            orphan = " (orphan: no inbound links)" if inbound.get(page, 0) == 0 else ""
            report.error(rel_root, "page is not reachable from wiki/index.md" + orphan)
        fields = frontmatter(texts[page])
        if fields is None:
            report.error(rel_root, "missing frontmatter (title, type, status, updated)")
            continue
        page_type, status = fields.get("type"), fields.get("status")
        if not fields.get("title"):
            report.error(rel_root, "frontmatter has no title")
        if page_type not in STATUS_BY_TYPE:
            report.error(rel_root, "invalid type: %r" % page_type)
        elif status not in STATUS_BY_TYPE[page_type]:
            report.error(rel_root, "invalid status %r for type %s" % (status, page_type))
        if fields.get("title"):
            titles.setdefault(fields["title"].lower(), []).append(rel_root)
    for paths in titles.values():
        if len(paths) > 1:
            report.warn(paths[0], "duplicate title shared with: %s" % ", ".join(paths[1:]))

    # log.md entries must carry Source HEAD (the update anchor).
    log_text = texts.get(wiki / "log.md", "")
    entries = wiki_state.log_entries(log_text)
    if (wiki / "log.md").is_file() and not LOG_HEADING_RE.search(log_text):
        report.warn("wiki/log.md", "no entries in the '## [YYYY-MM-DD] ...' format")
    for i, entry in enumerate(entries, 1):
        if not entry["sha"]:
            report.error("wiki/log.md", "entry %d has no 'Source HEAD: <sha>' line" % i)
        elif len(entry["sha"]) < 40:
            report.warn("wiki/log.md", "entry %d Source HEAD is abbreviated (%s); copy preflight's full head" % (i, entry["sha"]))

    # Files git would silently skip.
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--others", "--ignored", "--exclude-standard", "--", "wiki/"],
        capture_output=True,
        text=True,
    )
    for path in wiki_state.lines(proc.stdout):
        report.error(path, "ignored by .gitignore; git add would silently skip it (rename the page)")

    # Repository path references in inline code.
    files, dirs = tracked_paths(root)
    path_refs = {}
    for page, text in texts.items():
        if page.name == "SCHEMA.md":
            continue
        rel_page = str(page.relative_to(root))
        checked = set()
        stripped = strip_fences(text)
        for match in INLINE_CODE_RE.finditer(stripped):
            token = match.group(1).strip().rstrip(".,:;")
            token = re.sub(r":\d+(-\d+)?$", "", token.split("#", 1)[0])
            if ("/" not in token or token in checked or token.startswith(("/", "~", "-", "."))
                    or SCHEME_RE.match(token) or PATH_BAD_CHARS.intersection(token)):
                continue
            # A marker directly after this notation says the output path is
            # intentionally not preserved. It is scoped to this one code span.
            if NOT_PRESERVED_RE.match(stripped[match.end():match.end() + 80].lstrip()):
                continue
            checked.add(token)
            first = token.split("/", 1)[0]
            if not (root / first).exists() and first not in dirs:
                continue  # not a repository path (endpoint, branch, package name, ...)
            norm = token.rstrip("/")
            if in_protected(norm):
                continue  # boundary documentation; links are checked above
            if not (root / norm).exists():
                kind = "missing"
            elif norm in files or norm in dirs:
                continue
            elif (root / norm / ".git").exists():
                kind = "clone"
            elif is_ignored(root, norm):
                kind = "ignored"
            else:
                kind = "untracked"
            path_refs.setdefault((kind, token), []).append(rel_page)
    # One warning per distinct path, listing every page that mentions it. The
    # marker hint appears only where the marker can apply (reproduction outputs).
    for (kind, token), where in path_refs.items():
        report.warn(", ".join(sorted(where)), PATH_MESSAGES[kind] % token)

    # Budgets. The estimate function is shared with preflight, so both report
    # the same numbers; it is a heuristic, not a model tokenizer count.
    budget = wiki_state.budget_report(root, schema_text, host)
    pieces = ", ".join("%s=%s" % (rel, info["tokens"] if info["tokens"] is not None else "?")
                       for rel, info in sorted(budget["files"].items()))
    report.info.append("bootstrap tokens (estimate, not a model tokenizer): %s" % pieces)
    if budget["current_over_budget"]:
        report.warn(budget["applied_current_path"],
                    "current file ~%d tokens exceeds budget %d (estimate, not a model tokenizer count)" % (
                        budget["current_estimate"], budget["current_tokens"]))
    if budget["bootstrap_over_budget"]:
        report.warn("wiki/", "bootstrap ~%d tokens exceeds budget %d (estimate, not a model tokenizer count)" % (
            budget["bootstrap_estimate"], budget["bootstrap_tokens"]))

    version, pkg = wiki_state.schema_version(schema_text), wiki_state.template_schema_version()
    # Patch releases never change the SCHEMA policy, so compare major.minor only.
    if version and pkg and version.split(".")[:2] != pkg.split(".")[:2]:
        report.warn("wiki/SCHEMA.md", "schema-version %s differs from the skill's SCHEMA template %s: optional"
                    " migration, see core/schema-migrations.md; it never blocks a wiki run" % (version, pkg))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--host", help="host name override (same as WIKI_HOST)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = wiki_state.repo_root(args.repo)
    if root is None:
        print("ERROR %s: not a git repository" % args.repo)
        return 1
    report = lint(root, args.host)
    if args.json:
        json.dump({
            "errors": [{"path": p, "message": m} for p, m in report.errors],
            "warnings": [{"path": p, "message": m} for p, m in report.warnings],
            "info": report.info,
        }, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        for path, message in report.errors:
            print("ERROR %s: %s" % (path, message))
        for path, message in report.warnings:
            print("WARN  %s: %s" % (path, message))
        for line in report.info:
            print("INFO  %s" % line)
        print("structural lint: %s (%d errors, %d warnings)" % (
            "FAIL" if report.errors else "PASS", len(report.errors), len(report.warnings)))
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
