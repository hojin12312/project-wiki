#!/usr/bin/env python3
"""Deterministic Git / host / anchor state for the project-wiki skills.

Subcommands:
  self-update          fast-forward the skill package repository
  preflight <repo>     report everything a wiki run needs to decide (JSON)
  host <repo>          resolve which current file this machine owns (JSON)
  anchor <repo>        resolve the update-window anchor (JSON)
  lock <repo>          take this checkout's wiki run lock (JSON)
  unlock <repo>        release it with the token lock returned (JSON)

Standard library only; Python 3.8+.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[2]
SELF_UPDATE_TIMEOUT = 20
MAX_LIST = 200
INSTRUCTION_FILES = {"AGENTS.md", "CLAUDE.md", "AGENTS.override.md"}
# Tab, line feed and carriage return are normal text. Every other C0/C1
# character and DEL is reported as a control-character defect.
ALLOWED_CONTROL = {"\t", "\n", "\r"}
MANAGED_BLOCK_START = "<!-- project-wiki:start -->"
# One wiki run per checkout. The lock lives in the Git directory, so it never
# shows up as an untracked file, and each linked worktree gets its own.
LOCK_NAME = "project-wiki.lock"
LOCK_STALE_SECONDS = 3600


class GitError(RuntimeError):
    pass


def git(repo, *args, check=True, timeout=60):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or "git %s failed" % " ".join(args))
    return proc


def git_bytes(repo, *args, timeout=60):
    """Binary-safe git call for blobs that may not be valid UTF-8."""
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=timeout)


def lines(text):
    return [line for line in text.splitlines() if line.strip()]


# --- text integrity ---------------------------------------------------------

def decode_bytes(raw):
    """Return (text, error). The error describes the failure without quoting content."""
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError as exc:
        line = raw.count(b"\n", 0, exc.start) + 1
        return None, "invalid UTF-8 at byte %d (line %d): %s" % (exc.start, line, exc.reason)


def read_text(path, missing_ok=False):
    """Return (text, error). text is None when the file is unreadable or not UTF-8.

    With missing_ok, an absent file is (None, None): absence is a state, not a
    read error (a new repository has no wiki/SCHEMA.md yet).
    """
    if missing_ok and not Path(path).exists():
        return None, None
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        return None, "cannot read (%s)" % (exc.strerror or exc)
    return decode_bytes(raw)


def estimate_tokens(text):
    """Size estimate shared by preflight and lint.

    A stable heuristic, not a model tokenizer: ASCII counts at four
    characters per token, every other character at one token per character.
    """
    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    return int(ascii_chars / 4 + (len(text) - ascii_chars))


def text_defects(text):
    """Locate characters a text file should not contain.

    Returns 1-based (line, column, code point) tuples for U+FFFD replacement
    characters, NUL, and control characters other than tab/LF/CR. Korean
    text, emoji, tabs and line breaks are never defects.
    """
    defects = {"replacement": [], "nul": [], "control": []}
    line = column = 1
    for ch in text:
        code = ord(ch)
        if ch == "\ufffd":
            defects["replacement"].append((line, column, "U+FFFD"))
        elif code == 0:
            defects["nul"].append((line, column, "U+0000"))
        elif (code < 32 and ch not in ALLOWED_CONTROL) or code == 127 or 0x80 <= code <= 0x9F:
            defects["control"].append((line, column, "U+%04X" % code))
        if ch == "\n":
            line, column = line + 1, 1
        else:
            column += 1
    return defects


def package_version():
    text, _ = read_text(PACKAGE_DIR / "VERSION")
    return text.strip() if text else None


def template_schema_version():
    """SCHEMA policy version; bumped only when SCHEMA.template.md policy changes."""
    text, _ = read_text(PACKAGE_DIR / "core" / "SCHEMA_VERSION")
    return text.strip() if text else None


# --- SCHEMA parsing ---------------------------------------------------------

def read_block(text, name):
    match = re.search(
        r"<!--\s*wiki:%s:start\s*-->(.*?)<!--\s*wiki:%s:end\s*-->" % (name, name),
        text,
        re.S,
    )
    if not match:
        return []
    result = []
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("{{"):
            continue
        result.append(line)
    return result


def read_schema(root):
    """Return (schema text or None, read/decode error or None). Absent is not an error."""
    return read_text(Path(root) / "wiki" / "SCHEMA.md", missing_ok=True)


def schema_version(schema_text):
    if not schema_text:
        return None
    match = re.search(r"^schema-version:\s*(\S+)", schema_text, re.M)
    return match.group(1) if match else None


def parse_hosts(schema_text):
    hosts = {}
    for line in read_block(schema_text or "", "hosts"):
        if ":" not in line:
            continue
        name, values = line.split(":", 1)
        names = [v.strip() for v in values.split(",") if v.strip()]
        hosts[name.strip()] = names
    return hosts


def parse_budgets(schema_text):
    budgets = {"current_tokens": 2000, "bootstrap_tokens": 6000}
    for line in read_block(schema_text or "", "budgets"):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        try:
            budgets[key.strip()] = int(value.strip())
        except ValueError:
            pass
    return budgets


def protected_paths(schema_text):
    return [p.rstrip("/") for p in read_block(schema_text or "", "protected")]


def local_hostname():
    return socket.gethostname().split(".")[0]


def resolve_host(root, override=None):
    schema_text, _ = read_schema(root)
    hosts = parse_hosts(schema_text)
    hostname = local_hostname()
    if not hosts:
        return {
            "mode": "single",
            "host": None,
            "hostname": hostname,
            "current_path": "wiki/current.md",
            "error": None,
        }
    override = override or os.environ.get("WIKI_HOST")
    host = None
    if override:
        host = override if override in hosts else None
        error = None if host else "WIKI_HOST=%s is not declared in SCHEMA hosts" % override
    else:
        matches = [name for name, values in hosts.items() if hostname in values]
        if len(matches) == 1:
            host, error = matches[0], None
        elif not matches:
            error = "hostname %r is not mapped in SCHEMA hosts; ask the user which host this is" % hostname
        else:
            error = "hostname %r maps to several hosts: %s" % (hostname, ", ".join(matches))
    return {
        "mode": "multi",
        "host": host,
        "hostname": hostname,
        "declared_hosts": sorted(hosts),
        "current_path": "wiki/current/%s.md" % host if host else None,
        "error": error,
    }


# --- anchor -----------------------------------------------------------------

ENTRY_RE = re.compile(r"^## \[", re.M)


def log_entries(log_text):
    starts = [m.start() for m in ENTRY_RE.finditer(log_text)]
    entries = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(log_text)
        body = log_text[start:end]
        sha = re.search(r"^Source HEAD:\s*([0-9a-fA-F]{7,40})", body, re.M)
        host = re.search(r"^Host:\s*(\S+)", body, re.M)
        entries.append({
            "sha": sha.group(1) if sha else None,
            "host": host.group(1) if host else None,
        })
    return entries


def head_sha(root):
    proc = git(root, "rev-parse", "HEAD", check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def is_ancestor(root, sha):
    proc = git(root, "merge-base", "--is-ancestor", sha, "HEAD", check=False)
    return proc.returncode == 0


def committed_file(root, rel):
    """Return (text, error) for a file as committed at HEAD."""
    proc = git_bytes(root, "show", "HEAD:%s" % rel)
    if proc.returncode != 0:
        return None, None  # no committed copy; not an error by itself
    return decode_bytes(proc.stdout)


def find_anchor(root, host=None):
    """Resolve the update window from the *committed* log.

    Only a committed log entry is a confirmed anchor. An entry that exists
    only in the working tree was never recorded by a wiki commit, so using it
    would silently skip the range it claims to cover; it is reported as
    `pending_source_head` instead.
    """
    head = head_sha(root)
    result = {
        "head": head,
        "anchor": None,
        "method": "none",
        "log_error": None,
        "pending_source_head": None,
    }
    if head is None:
        return result
    committed_text, committed_error = committed_file(root, "wiki/log.md")
    working_text, working_error = read_text(Path(root) / "wiki" / "log.md", missing_ok=True)
    log_errors = []
    if committed_error:
        log_errors.append("HEAD:wiki/log.md: %s" % committed_error)
    if working_error:
        log_errors.append("wiki/log.md: %s" % working_error)
    if log_errors:
        result["log_error"] = "; ".join(log_errors)
    committed = [e for e in log_entries(committed_text or "") if e["sha"]]
    working = [e for e in log_entries(working_text or "") if e["sha"]]
    if working and (not committed or working[-1]["sha"] != committed[-1]["sha"]):
        result["pending_source_head"] = working[-1]["sha"]
    # In multi-host repos prefer this host's own last update: shared pages
    # may be reviewed twice, but this host's current file never misses a change.
    own = [e for e in committed if host and e["host"] == host]
    candidates = own or committed
    if candidates and is_ancestor(root, candidates[-1]["sha"]):
        full = git(root, "rev-parse", candidates[-1]["sha"]).stdout.strip()
        result.update(anchor=full, method="log-source-head")
        return result
    # No usable committed entry (new wiki, vanished SHA after a rebase, or a
    # corrupt log): fall back to the commit that last touched log.md, never to
    # the last commit touching wiki/.
    proc = git(root, "log", "-1", "--format=%H", "--", "wiki/log.md", check=False)
    sha = proc.stdout.strip()
    if sha:
        result.update(anchor=sha, method="log-commit")
    return result


def wiki_run_commits(root, anchor):
    """Commits in anchor..HEAD that a wiki run made.

    A log entry's Source HEAD is the head *before* its wiki commit, so the
    range always starts with the previous run's own commit. Every wiki run
    appends a log.md entry and commits only wiki/ and managed blocks, so a
    commit that touches wiki/log.md counts as a wiki-run commit. Limitation:
    a hand-made commit that also edits log.md hides its wiki/ and
    instruction-file edits from review; its other source paths stay visible.
    """
    proc = git(root, "log", "--format=%H", "%s..HEAD" % anchor, "--", "wiki/log.md", check=False)
    return set(lines(proc.stdout))


def outside_runs(root, anchor, entries, runs):
    """Map each name-status entry to the commits, other than wiki runs, that
    touched it (short SHAs, oldest first). Entries only runs touched are dropped."""
    kept = {}
    for entry in entries:
        paths = entry.split("\t")[1:]
        touched = lines(git(root, "log", "--reverse", "--format=%H", "%s..HEAD" % anchor, "--", *paths,
                            check=False).stdout)
        others = [sha[:12] for sha in touched if sha not in runs]
        if others:
            kept[entry] = others
    return kept


def changed_source(root, anchor):
    """Source paths changed since the anchor, minus the managed blocks wiki runs wrote."""
    if not anchor:
        return None
    proc = git(root, "diff", "--name-status", "%s..HEAD" % anchor, "--", ".", ":(exclude)wiki", check=False)
    entries = lines(proc.stdout)
    instruction = [e for e in entries if Path(e.split("\t")[-1]).name in INSTRUCTION_FILES]
    if not instruction:
        return entries
    kept = outside_runs(root, anchor, instruction, wiki_run_commits(root, anchor))
    return [e for e in entries if e not in instruction or e in kept]


def changed_wiki(root, anchor):
    """Wiki pages committed since the anchor by something other than a wiki run.

    These are edits made alongside feature work (or by hand); a run reviews
    them instead of rewriting them. log.md and the runs' own edits are left out,
    so the previous update never shows up as work for the next one. Review each
    with `git show <commit> -- <path>`.
    """
    if not anchor:
        return None
    proc = git(root, "diff", "--name-status", "%s..HEAD" % anchor, "--", "wiki", ":(exclude)wiki/log.md",
               check=False)
    kept = outside_runs(root, anchor, lines(proc.stdout), wiki_run_commits(root, anchor))
    return [{"path": entry.split("\t")[-1], "commits": commits} for entry, commits in kept.items()]


# --- run lock -------------------------------------------------------------------

def lock_path(root):
    rel = git(root, "rev-parse", "--git-path", LOCK_NAME).stdout.strip()
    return Path(rel) if os.path.isabs(rel) else Path(root) / rel


def lock_status(root, token=None):
    """Who holds this checkout's wiki run lock. Age comes from the file's mtime.

    The holder's token is never printed, so another run cannot release it;
    pass your own token to learn whether you still hold the lock (`owned`).
    """
    path = lock_path(root)
    try:
        age = int(time.time() - path.stat().st_mtime)
    except OSError:
        return {"held": False}
    text, _ = read_text(path)
    try:
        info = json.loads(text or "")
    except ValueError:
        info = {}
    return {
        "held": True,
        "owned": None if token is None else info.get("token") == token,
        "command": info.get("command"),
        "hostname": info.get("hostname"),
        "age_seconds": age,
        "stale": age > LOCK_STALE_SECONDS,
        "path": str(path),
    }


def acquire_lock(root, command):
    """Take the lock, or report the holder. A stale lock (older than
    LOCK_STALE_SECONDS, left by an interrupted run) is replaced; the replaced
    run then fails its pre-commit token check and stops without committing."""
    path = lock_path(root)
    token = secrets.token_hex(8)
    body = json.dumps({"token": token, "command": command, "hostname": local_hostname(),
                       "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    current = lock_status(root)
    if current["held"] and not current["stale"]:
        return dict(status="held", holder=current)
    try:
        if current["held"]:
            tmp = path.with_name(path.name + "." + token)
            tmp.write_text(body, encoding="utf-8")
            os.replace(str(tmp), str(path))
            return dict(status="replaced-stale", token=token, replaced=current)
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return dict(status="held", holder=lock_status(root))
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(body)
    return dict(status="acquired", token=token)


def release_lock(root, token=None, force=False):
    current = lock_status(root, token or "")
    if not current["held"]:
        return {"status": "not-held"}
    if not force and not current["owned"]:
        return {"status": "token-mismatch", "holder": current}
    try:
        lock_path(root).unlink()
    except FileNotFoundError:
        return {"status": "not-held"}
    return {"status": "released"}


# --- preflight ----------------------------------------------------------------

def repo_root(path):
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def upstream_status(root):
    proc = git(root, "rev-list", "--left-right", "--count", "@{u}...HEAD", check=False)
    if proc.returncode != 0:
        return None
    behind, ahead = proc.stdout.split()
    return {"behind": int(behind), "ahead": int(ahead), "note": "based on the last fetch"}


def untracked_entries(root):
    proc = git(root, "ls-files", "--others", "--exclude-standard", "--directory", check=False)
    result = []
    for entry in lines(proc.stdout):
        path = Path(root) / entry
        nested = path.is_dir() and (path / ".git").exists()
        result.append({"path": entry, "nested_repo": nested})
    return result


def classify_staged(staged, host):
    """Split staged paths into the groups a wiki run must treat differently."""
    current_path = host.get("current_path")
    groups = {"all": list(staged), "wiki": [], "wiki_other_hosts": [], "instruction_files": [], "other": []}
    for path in staged:
        name = Path(path).name
        if path.startswith("wiki/current/") and path != current_path:
            groups["wiki_other_hosts"].append(path)
        elif path == "wiki/current.md" and current_path != "wiki/current.md":
            groups["wiki_other_hosts"].append(path)
        elif path.startswith("wiki/"):
            groups["wiki"].append(path)
        elif name in INSTRUCTION_FILES:
            groups["instruction_files"].append(path)
        else:
            groups["other"].append(path)
    return groups


def instruction_states(root, staged, unstaged):
    """Report each instruction file's Git state so the block can be handled safely."""
    tracked = set(lines(git(root, "ls-files").stdout))
    untracked = set(lines(git(root, "ls-files", "--others", "--exclude-standard").stdout))
    ignored = set(lines(git(root, "ls-files", "--others", "--ignored", "--exclude-standard").stdout))
    dirty = set(staged) | set(unstaged)
    result = []
    for path in sorted(p for p in tracked | untracked | ignored if Path(p).name in INSTRUCTION_FILES):
        if not (Path(root) / path).is_file():
            continue
        if path in tracked:
            state = "tracked-dirty" if path in dirty else "tracked-clean"
        elif path in ignored:
            state = "ignored"
        elif path in untracked:
            state = "untracked"
        else:
            continue
        text, error = read_text(Path(root) / path)
        result.append({
            "path": path,
            "state": state,
            "managed_block": None if text is None else (MANAGED_BLOCK_START in text),
            "error": error,
        })
    return result


def budget_report(root, schema_text, host):
    """Budgets plus current/bootstrap estimates, shared by preflight and lint."""
    budgets = parse_budgets(schema_text)
    current_rel = host.get("current_path")
    rels = ["wiki/index.md", "wiki/overview.md"] + ([current_rel] if current_rel else [])
    files = {}
    for rel in rels:
        path = Path(root) / rel
        if not path.is_file():
            files[rel] = {"exists": False, "tokens": None}
            continue
        text, error = read_text(path)
        if error:
            files[rel] = {"exists": True, "tokens": None, "error": error}
        else:
            files[rel] = {"exists": True, "tokens": estimate_tokens(text)}
    current = files.get(current_rel) if current_rel else None
    incomplete = any(info["exists"] and info["tokens"] is None for info in files.values())
    bootstrap = sum(info["tokens"] for info in files.values() if info["tokens"] is not None)
    return {
        "current_tokens": budgets["current_tokens"],
        "bootstrap_tokens": budgets["bootstrap_tokens"],
        "applied_current_path": current_rel,
        "files": files,
        "current_estimate": current["tokens"] if current else None,
        "bootstrap_estimate": bootstrap,
        "current_over_budget": bool(
            current and current["tokens"] is not None and current["tokens"] > budgets["current_tokens"]
        ),
        "bootstrap_over_budget": bool(not incomplete and bootstrap > budgets["bootstrap_tokens"]),
        "missing": [rel for rel, info in files.items() if not info["exists"]],
        "source": "wiki/SCHEMA.md budget block (built-in defaults when absent)",
        "estimate": "estimate_tokens heuristic (ASCII/4 + other/1); not a model tokenizer count",
    }


def preflight(path, host_override=None, lock_token=None):
    root = repo_root(path)
    if root is None:
        return {"blockers": ["not a git repository: suggest `git init` to the user"]}
    schema_text, schema_error = read_schema(root)
    schema_text = schema_text or ""
    host = resolve_host(root, host_override)
    anchor = find_anchor(root, host.get("host"))
    changes = changed_source(root, anchor["anchor"])
    wiki_changes = changed_wiki(root, anchor["anchor"])
    staged_all = lines(git(root, "diff", "--cached", "--name-only").stdout)
    unstaged = lines(git(root, "diff", "--name-only").stdout)
    ignored = lines(git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "--", "wiki/").stdout)
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip() or None

    untracked = untracked_entries(root)
    instruction_files = instruction_states(root, staged_all, unstaged)
    budget = budget_report(root, schema_text, host)

    encoding_errors = []
    if schema_error:
        encoding_errors.append({"path": "wiki/SCHEMA.md", "message": schema_error})
    if anchor.get("log_error"):
        encoding_errors.append({"path": "wiki/log.md", "message": anchor["log_error"]})
    for rel, info in budget["files"].items():
        if info.get("error"):
            encoding_errors.append({"path": rel, "message": info["error"]})

    run_lock = lock_status(root, lock_token)
    blockers = []
    if lock_token and not run_lock.get("owned"):
        blockers.append("this run no longer holds the wiki run lock (stale takeover or manual release);"
                        " stop without committing and tell the user")
    if anchor["head"] is None:
        blockers.append("repository has no commits yet")
    if host["error"]:
        blockers.append(host["error"])
    if schema_error:
        blockers.append(
            "wiki/SCHEMA.md: %s (fix the file encoding before running; lint will not auto-repair)"
            % schema_error
        )

    truncated = changes is not None and len(changes) > MAX_LIST
    return {
        "repo_root": root,
        "branch": branch,
        "head": anchor["head"],
        "wiki_exists": (Path(root) / "wiki").is_dir(),
        "schema_version": schema_version(schema_text),
        "package_version": package_version(),
        "template_schema_version": template_schema_version(),
        "package_dir": str(PACKAGE_DIR),
        "host": host,
        "anchor": anchor,
        "budget": budget,
        "changed_source": None if changes is None else changes[:MAX_LIST],
        "changed_source_count": None if changes is None else len(changes),
        "changed_source_truncated": truncated,
        "changed_source_remainder": None if not truncated else {
            "shown": MAX_LIST,
            "remaining": len(changes) - MAX_LIST,
            "command": "git -C <repo-root> diff --name-status %s..HEAD -- . ':(exclude)wiki'" % anchor["anchor"],
            "note": "raw diff: it also prints the first entries already shown and any managed-block"
                    " change made only by wiki-run commits; skip those",
        },
        "changed_wiki": wiki_changes,
        "run_lock": run_lock,
        "staged": classify_staged(staged_all, host),
        "dirty_source": [p for p in unstaged if not p.startswith("wiki/")],
        "dirty_wiki": [p for p in unstaged if p.startswith("wiki/")],
        "dirty_instruction_files": [f["path"] for f in instruction_files if f["state"] == "tracked-dirty"],
        "instruction_files": instruction_files,
        "untracked_entries": untracked[:MAX_LIST],
        "untracked_count": len(untracked),
        "untracked_truncated": len(untracked) > MAX_LIST,
        "ignored_wiki_files": ignored,
        "protected_paths": protected_paths(schema_text),
        "encoding_errors": encoding_errors,
        "upstream": upstream_status(root),
        "blockers": blockers,
    }


# --- self-update ----------------------------------------------------------------

def self_update():
    result = {"package_dir": str(PACKAGE_DIR), "version_before": package_version()}
    try:
        if git(PACKAGE_DIR, "status", "--porcelain", "--untracked-files=no").stdout.strip():
            result.update(status="skipped", reason="package has uncommitted changes")
            return result
        if git(PACKAGE_DIR, "rev-parse", "--abbrev-ref", "@{u}", check=False).returncode != 0:
            result.update(status="skipped", reason="package branch has no upstream")
            return result
        before = git(PACKAGE_DIR, "rev-parse", "HEAD").stdout.strip()
        env_args = ["-c", "http.lowSpeedLimit=1000", "-c", "http.lowSpeedTime=10"]
        proc = subprocess.run(
            ["git", "-C", str(PACKAGE_DIR), *env_args, "pull", "--ff-only", "--quiet"],
            capture_output=True,
            text=True,
            timeout=SELF_UPDATE_TIMEOUT,
            env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=8"),
        )
        if proc.returncode != 0:
            result.update(status="skipped", reason=proc.stderr.strip()[-300:] or "git pull failed")
            return result
        after = git(PACKAGE_DIR, "rev-parse", "HEAD").stdout.strip()
        if before == after:
            result.update(status="current")
        else:
            changed = lines(git(PACKAGE_DIR, "diff", "--name-only", before, after).stdout)
            result.update(status="updated", changed=changed, version_after=package_version())
    except subprocess.TimeoutExpired:
        result.update(status="skipped", reason="timed out after %ss" % SELF_UPDATE_TIMEOUT)
    except (GitError, OSError) as exc:
        result.update(status="skipped", reason=str(exc))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-update")
    for name in ("preflight", "host", "anchor", "lock", "unlock"):
        p = sub.add_parser(name)
        p.add_argument("repo", nargs="?", default=".")
        if name in ("preflight", "host", "anchor"):
            p.add_argument("--host", help="host name override (same as WIKI_HOST)")
    sub.choices["preflight"].add_argument("--lock-token", help="blocker unless this run still holds the lock")
    sub.choices["lock"].add_argument("--run", default="wiki-run", help="command name recorded for the holder")
    sub.choices["unlock"].add_argument("--token", help="the token lock returned")
    sub.choices["unlock"].add_argument("--force", action="store_true",
                                       help="remove the lock of a run the user confirmed is gone")
    args = parser.parse_args(argv)

    if args.command == "self-update":
        out = self_update()
    else:
        root = repo_root(args.repo)
        if root is None:
            out = {"blockers": ["not a git repository: suggest `git init` to the user"]}
        elif args.command == "lock":
            out = acquire_lock(root, args.run)
        elif args.command == "unlock":
            out = release_lock(root, args.token, args.force)
            json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
            return 0 if out["status"] in ("released", "not-held") else 1
        elif args.command == "preflight":
            out = preflight(root, args.host, args.lock_token)
        elif args.command == "host":
            out = resolve_host(root, args.host)
        else:
            out = find_anchor(root, resolve_host(root, args.host).get("host"))
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 1 if out.get("blockers") or out.get("status") == "held" else 0


if __name__ == "__main__":
    sys.exit(main())
