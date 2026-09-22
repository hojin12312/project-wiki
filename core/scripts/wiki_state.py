#!/usr/bin/env python3
"""Deterministic Git / host / anchor state for the project-wiki skills.

Subcommands:
  self-update          fast-forward the skill package repository
  preflight <repo>     report everything a wiki run needs to decide (JSON)
  host <repo>          resolve which current file this machine owns (JSON)
  anchor <repo>        resolve the update-window anchor (JSON)

Standard library only; Python 3.8+.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[2]
SELF_UPDATE_TIMEOUT = 20
MAX_LIST = 200


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


def lines(text):
    return [line for line in text.splitlines() if line.strip()]


def package_version():
    try:
        return (PACKAGE_DIR / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return None


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
    path = Path(root) / "wiki" / "SCHEMA.md"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


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
    schema_text = read_schema(root)
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


def find_anchor(root, host=None):
    head = head_sha(root)
    result = {"head": head, "anchor": None, "method": "none"}
    if head is None:
        return result
    log_path = Path(root) / "wiki" / "log.md"
    if log_path.exists():
        entries = [e for e in log_entries(log_path.read_text(encoding="utf-8")) if e["sha"]]
        # In multi-host repos prefer this host's own last update: shared pages
        # may be reviewed twice, but this host's current file never misses a change.
        own = [e for e in entries if host and e["host"] == host]
        candidates = own or entries
        if candidates and is_ancestor(root, candidates[-1]["sha"]):
            full = git(root, "rev-parse", candidates[-1]["sha"]).stdout.strip()
            result.update(anchor=full, method="log-source-head")
            return result
        # The recorded SHA vanished (rebase/squash): fall back to the commit
        # that last touched log.md, never to the last commit touching wiki/.
        proc = git(root, "log", "-1", "--format=%H", "--", "wiki/log.md", check=False)
        sha = proc.stdout.strip()
        if sha:
            result.update(anchor=sha, method="log-commit")
    return result


def changed_source(root, anchor):
    if not anchor:
        return None
    proc = git(root, "diff", "--name-status", "%s..HEAD" % anchor, "--", ".", ":(exclude)wiki", check=False)
    return lines(proc.stdout)


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


def preflight(path, host_override=None):
    root = repo_root(path)
    if root is None:
        return {"blockers": ["not a git repository: suggest `git init` to the user"]}
    schema_text = read_schema(root)
    host = resolve_host(root, host_override)
    anchor = find_anchor(root, host.get("host"))
    changes = changed_source(root, anchor["anchor"])
    staged = lines(git(root, "diff", "--cached", "--name-only").stdout)
    unstaged = lines(git(root, "diff", "--name-only").stdout)
    ignored = lines(git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "--", "wiki/").stdout)
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip() or None

    blockers = []
    if anchor["head"] is None:
        blockers.append("repository has no commits yet")
    if schema_text is not None and host["error"]:
        blockers.append(host["error"])
    untracked = untracked_entries(root)
    return {
        "repo_root": root,
        "branch": branch,
        "head": anchor["head"],
        "wiki_exists": (Path(root) / "wiki").is_dir(),
        "schema_version": schema_version(schema_text),
        "package_version": package_version(),
        "package_dir": str(PACKAGE_DIR),
        "host": host,
        "anchor": anchor,
        "changed_source": None if changes is None else changes[:MAX_LIST],
        "changed_source_count": None if changes is None else len(changes),
        "staged": staged,
        "dirty_source": [p for p in unstaged if not p.startswith("wiki/")],
        "dirty_wiki": [p for p in unstaged if p.startswith("wiki/")],
        "untracked_entries": untracked[:MAX_LIST],
        "untracked_count": len(untracked),
        "ignored_wiki_files": ignored,
        "protected_paths": protected_paths(schema_text),
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
    for name in ("preflight", "host", "anchor"):
        p = sub.add_parser(name)
        p.add_argument("repo", nargs="?", default=".")
        p.add_argument("--host", help="host name override (same as WIKI_HOST)")
    args = parser.parse_args(argv)

    if args.command == "self-update":
        out = self_update()
    else:
        root = repo_root(args.repo)
        if root is None:
            out = {"blockers": ["not a git repository: suggest `git init` to the user"]}
        elif args.command == "preflight":
            out = preflight(root, args.host)
        elif args.command == "host":
            out = resolve_host(root, args.host)
        else:
            out = find_anchor(root, resolve_host(root, args.host).get("host"))
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 1 if out.get("blockers") else 0


if __name__ == "__main__":
    sys.exit(main())
