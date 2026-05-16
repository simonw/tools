#!/usr/bin/env python3
"""Print every change to the first line of a file across its git history.

Output format, one line per change (oldest first):
    <iso-datetime> <6-char-hash> <first line content>
"""
import os
import subprocess
import sys


def git(*args, cwd=None):
    """Run a git command and return stdout, raising on failure."""
    result = subprocess.run(
        ['git', *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout


def resolve_repo(filepath):
    """Return (repo_root, path_relative_to_repo) for the given file.

    The file does not need to exist at HEAD — only its directory needs to be
    inside a git working tree."""
    # realpath resolves symlinks so the path lines up with what
    # `git rev-parse --show-toplevel` returns (git resolves symlinks too).
    abs_path = os.path.realpath(filepath)
    search_dir = os.path.dirname(abs_path) if os.path.isfile(abs_path) else abs_path
    if not os.path.isdir(search_dir):
        raise RuntimeError(f"Not a file or directory: {filepath}")
    repo_root = git('rev-parse', '--show-toplevel', cwd=search_dir).strip()
    rel = os.path.relpath(abs_path, repo_root)
    return repo_root, rel


def iter_commits(filepath, cwd):
    """Yield (sha, iso_date, path_at_that_commit) for each commit touching
    the file, oldest first. --follow tracks renames, so the path may differ
    from the one the caller passed in."""
    # NB: `--follow` and `--reverse` don't combine in git (follow only kicks
    # in after history is walked, so --reverse with --follow returns just the
    # rename commit). We take the default newest-first order and reverse in
    # Python.
    output = git(
        'log', '--follow', '--name-only',
        '--format=__C__%H%x09%aI',
        '--', filepath,
        cwd=cwd,
    )
    commits = []
    sha = date = path = None
    for line in output.split('\n'):
        if line.startswith('__C__'):
            if sha is not None:
                commits.append((sha, date, path or filepath))
            sha, date = line[5:].split('\t', 1)
            path = None
        elif line.strip():
            # With a pathspec filter and no --full-diff, the name list per
            # commit is restricted to the followed file's path at that commit.
            path = line.strip()
    if sha is not None:
        commits.append((sha, date, path or filepath))
    for entry in reversed(commits):
        yield entry


def first_line_at(sha, path, cwd):
    """Return the first line of `path` at commit `sha`, or None if missing."""
    try:
        content = git('show', f'{sha}:{path}', cwd=cwd)
    except RuntimeError:
        return None
    # splitlines handles \n, \r\n, and a missing trailing newline uniformly.
    lines = content.splitlines()
    return lines[0] if lines else ''


def main(argv):
    if len(argv) != 2:
        sys.exit(f"Usage: {argv[0]} <file>")
    filepath = argv[1]

    try:
        repo_root, rel_path = resolve_repo(filepath)
    except RuntimeError as e:
        sys.exit(f"git error: {e}")

    sentinel = object()
    previous = sentinel
    saw_any = False

    try:
        commits = list(iter_commits(rel_path, cwd=repo_root))
    except RuntimeError as e:
        sys.exit(f"git error: {e}")

    for sha, date, path in commits:
        saw_any = True
        first = first_line_at(sha, path, cwd=repo_root)
        if first is None:
            continue
        if first != previous:
            print(f"{date} {sha[:6]} {first}")
            previous = first

    if not saw_any:
        sys.exit(f"No git history found for {filepath}")


if __name__ == '__main__':
    main(sys.argv)
