import ast
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from ..services.gitlab import GitLabService
from ..config import settings
from ..database import log_to_db


async def run_repository_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Repository Context Service: Deterministic service that enriches patch context
    with related files, imports, tests, and recent commits.
    No LLM calls - pure static analysis + GitLab API.
    """
    incident = state.get("incident", {})
    incident_id = incident.get("incident_db_id")
    fusion = state.get("fusion", {})
    affected_file = fusion.get("affected_file")
    pinned_commit_sha = fusion.get("pinned_commit_sha")
    target_repo = incident.get("target_repo")
    target_branch = incident.get("target_branch") or settings.GITLAB_TARGET_BRANCH

    if not affected_file:
        log_to_db(incident_id, "Repository Context", "No affected_file in state, skipping context enrichment", level="WARNING")
        return {"repo_context": {}}

    log_to_db(incident_id, "Repository Context", f"Building context for {affected_file}...")

    gitlab = GitLabService.from_state(state)

    related_files = await _find_related_files(gitlab, affected_file, incident_id)
    import_deps = await _extract_import_dependencies(gitlab, affected_file, related_files, incident_id)
    test_files = await _find_test_files(gitlab, affected_file, incident_id)
    recent_commits = await _get_recent_commits(gitlab, affected_file, pinned_commit_sha, incident_id)

    context = {
        "primary_file": affected_file,
        "related_files": related_files,
        "import_dependencies": import_deps,
        "test_files": test_files,
        "recent_commits": recent_commits,
        "supporting_context": {
            "file_count": len(related_files) + 1,
            "has_imports": len(import_deps) > 0,
            "has_tests": len(test_files) > 0,
        }
    }

    log_to_db(
        incident_id,
        "Repository Context",
        f"Files analyzed: {context['supporting_context']['file_count']}; primary='{affected_file}'",
    )
    log_to_db(incident_id, "Repository Context", f"Context built: {len(related_files)} related, {len(test_files)} tests, {len(recent_commits)} commits")
    return {"repo_context": context}


async def _find_related_files(gitlab: GitLabService, affected_file: str, incident_id: int) -> List[str]:
    """Find files in same directory and parent directories."""
    related = []
    try:
        # Get directory of affected file
        file_dir = str(Path(affected_file).parent)
        if file_dir == ".":
            file_dir = ""

        # Real implementation: use GitLab tree API
        tree = await gitlab.get_repository_tree(path=file_dir, recursive=False)
        for item in tree:
            if item.get("type") == "blob" and item.get("path", "").endswith(".py"):
                # Normalize paths to match
                item_path = item.get("path", "").replace("\\", "/")
                aff_path = affected_file.replace("\\", "/")
                # Ensure we don't add the affected file itself, and that the path ends with .py
                if not item_path.endswith(aff_path):
                    related.append(item_path)
        return related
    except Exception as e:
        log_to_db(incident_id, "Repository Context", f"Error finding related files: {e}", level="WARNING")
        return []


async def _extract_import_dependencies(gitlab: GitLabService, affected_file: str, related_files: List[str], incident_id: int) -> List[str]:
    """Extract import dependencies using Python AST."""
    deps: Set[str] = set()

    async def parse_file(file_path: str):
        content = await gitlab.get_file_content(file_path)
        if not content or not file_path.endswith(".py"):
            return
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        deps.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        deps.add(node.module.split(".")[0])
        except SyntaxError:
            pass

    await parse_file(affected_file)
    for f in related_files:
        await parse_file(f)

    # Filter stdlib
    stdlib = {"os", "sys", "json", "datetime", "typing", "pathlib", "collections", "itertools", "functools", "dataclasses", "enum", "abc", "asyncio", "logging", "re", "math", "random", "uuid", "hashlib", "base64", "time", "decimal", "fractions", "statistics", "string", "textwrap", "unicodedata", "html", "xml", "csv", "sqlite3", "pickle", "copy", "pprint", "inspect", "ast", "tokenize", "keyword", "token", "symbol", "opcode", "dis", "code", "types", "builtins", "__future__", "warnings", "contextlib", "weakref", "gc", "atexit", "traceback", "linecache", "marshal", "struct", "array", "bisect", "heapq", "queue", "sched", "threading", "multiprocessing", "concurrent", "subprocess", "signal", "mmap", "select", "selectors", "asyncio", "socket", "ssl", "urllib", "http", "email", "json", "csv", "sqlite3", "dbm", "pickle", "shelve", "marshal", "copyreg", "json", "xmlrpc", "html", "webbrowser", "cgi", "wsgiref", "http", "urllib", "ftplib", "poplib", "imaplib", "nntplib", "smtplib", "telnetlib", "uuid", "socketserver", "http", "xmlrpc", "ipaddress", "colorsys", "imghdr", "sndhdr", "ossaudiodev", "platform", "errno", "ctypes", "msvcrt", "winreg", "winsound", "posix", "pwd", "grp", "termios", "tty", "pty", "fcntl", "pipes", "resource", "nis", "syslog", "commands", "popen2", "pipes", "stat", "filecmp", "dircache", "fnmatch", "glob", "linecache", "shutil", "macpath", "os2emxpath", "stat", "statvfs", "filecmp", "tempfile", "glob", "fnmatch", "linecache", "shutil", "macpath", "os2emxpath"}
    return [d for d in deps if d not in stdlib and not d.startswith("_")]


async def _find_test_files(gitlab: GitLabService, affected_file: str, incident_id: int) -> List[str]:
    """Heuristic test file discovery."""
    tests = []
    try:
        # No demo mode short-circuit needed here anymore, rely on actual file fetch

        # Real: search for test files matching pattern
        base_name = Path(affected_file).stem
        possible_tests = [
            f"tests/test_{base_name}.py",
            f"tests/test_{Path(affected_file).parent.name}.py",
            f"{Path(affected_file).parent}/test_{base_name}.py",
        ]
        for t in possible_tests:
            content = await gitlab.get_file_content(t)
            if content and not content.startswith("# Simulated content for"):
                tests.append(t)
        return tests
    except Exception as e:
        log_to_db(incident_id, "Repository Context", f"Error finding test files: {e}", level="WARNING")
        return []


async def _get_recent_commits(gitlab: GitLabService, affected_file: str, pinned_sha: Optional[str], incident_id: int) -> List[Dict[str, Any]]:
    """Get recent commits touching the affected file."""
    commits = []
    try:
        commits_data = await gitlab.get_file_commits(affected_file, ref=pinned_sha)
        for c in commits_data[:3]:
            commits.append({
                "sha": c.get("id")[:8] if c.get("id") else "",
                "title": c.get("title", ""),
                "author": c.get("author_name", ""),
                "date": c.get("created_at", ""),
            })
        return commits
    except Exception as e:
        log_to_db(incident_id, "Repository Context", f"Error getting recent commits: {e}", level="WARNING")
        return []
