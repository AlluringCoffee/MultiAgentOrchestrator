import logging
import os
import re
import shlex
from .cli import CLITool
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _sanitize_git_message(message: str) -> str:
    """
    Sanitize a git commit message to prevent command injection.
    Removes or escapes dangerous characters while preserving message readability.
    """
    if not message:
        return "No message provided"

    # Remove null bytes and other control characters (except newlines/tabs)
    message = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', message)

    # Limit message length to prevent buffer issues
    max_length = 5000
    if len(message) > max_length:
        message = message[:max_length] + "... (truncated)"

    return message


def _validate_repo_url(url: str) -> bool:
    """Validate a git repository URL to prevent injection attacks."""
    if not url:
        return False

    # Allow common git URL patterns
    valid_patterns = [
        r'^https?://[\w\-\.]+/[\w\-\./]+\.git$',  # HTTPS
        r'^https?://[\w\-\.]+/[\w\-\./]+$',        # HTTPS without .git
        r'^git@[\w\-\.]+:[\w\-\./]+\.git$',        # SSH
        r'^git://[\w\-\.]+/[\w\-\./]+\.git$',      # Git protocol
        r'^ssh://[\w\-@\.]+/[\w\-\./]+\.git$',     # SSH explicit
    ]

    for pattern in valid_patterns:
        if re.match(pattern, url, re.IGNORECASE):
            return True

    logger.warning(f"Invalid or potentially dangerous git URL: {url}")
    return False


def _validate_path(path: str) -> bool:
    """Validate a file path to prevent directory traversal attacks."""
    if not path:
        return True  # Empty path is OK (means current directory)

    # Prevent path traversal
    if '..' in path or path.startswith('/') or ':' in path:
        # Allow absolute paths on Windows (C:\...)
        if os.name == 'nt' and re.match(r'^[a-zA-Z]:\\', path):
            return True
        logger.warning(f"Potentially dangerous path: {path}")
        return False

    return True


class GitTool:
    """
    Wrapper for Git operations using the CLI tool.
    Avoids heavy dependency on GitPython if not installed, falls back to CLI.

    Security improvements:
    - Input validation and sanitization
    - Proper escaping of user-provided values
    - URL validation for clone operations
    - Path validation to prevent traversal
    """

    @staticmethod
    def status(cwd: str = ".") -> Dict[str, Any]:
        if not _validate_path(cwd):
            return {"success": False, "error": "Invalid working directory path"}
        return CLITool.execute_safe(["git", "status"], cwd)

    @staticmethod
    def log(cwd: str = ".", limit: int = 5) -> Dict[str, Any]:
        if not _validate_path(cwd):
            return {"success": False, "error": "Invalid working directory path"}

        # Validate limit is a reasonable integer
        try:
            limit = int(limit)
            if limit < 1 or limit > 1000:
                limit = 5
        except (ValueError, TypeError):
            limit = 5

        return CLITool.execute_safe(["git", "log", "-n", str(limit), "--oneline"], cwd)

    @staticmethod
    def clone(repo_url: str, target_dir: str = None) -> Dict[str, Any]:
        # Validate repository URL
        if not _validate_repo_url(repo_url):
            return {"success": False, "error": "Invalid or blocked repository URL"}

        # Validate target directory if provided
        if target_dir and not _validate_path(target_dir):
            return {"success": False, "error": "Invalid target directory path"}

        # Build command as argument list (safe from injection)
        args = ["git", "clone", repo_url]
        if target_dir:
            args.append(target_dir)

        return CLITool.execute_safe(args, ".")

    @staticmethod
    def commit_all(message: str, cwd: str = ".") -> Dict[str, Any]:
        if not _validate_path(cwd):
            return {"success": False, "error": "Invalid working directory path"}

        # Sanitize commit message
        message = _sanitize_git_message(message)

        # Stage all files using safe execution
        add_res = CLITool.execute_safe(["git", "add", "-A"], cwd)
        if not add_res["success"]:
            return add_res

        # Commit with message as argument (safe from injection)
        return CLITool.execute_safe(["git", "commit", "-m", message], cwd)

    @staticmethod
    def push(cwd: str = ".") -> Dict[str, Any]:
        if not _validate_path(cwd):
            return {"success": False, "error": "Invalid working directory path"}
        return CLITool.execute_safe(["git", "push"], cwd)

    @staticmethod
    def pull(cwd: str = ".") -> Dict[str, Any]:
        """Pull latest changes from remote."""
        if not _validate_path(cwd):
            return {"success": False, "error": "Invalid working directory path"}
        return CLITool.execute_safe(["git", "pull"], cwd)

    @staticmethod
    def branch(cwd: str = ".", branch_name: str = None) -> Dict[str, Any]:
        """List branches or create a new branch."""
        if not _validate_path(cwd):
            return {"success": False, "error": "Invalid working directory path"}

        if branch_name:
            # Validate branch name (alphanumeric, dashes, underscores, slashes)
            if not re.match(r'^[\w\-/]+$', branch_name):
                return {"success": False, "error": "Invalid branch name"}
            return CLITool.execute_safe(["git", "branch", branch_name], cwd)
        else:
            return CLITool.execute_safe(["git", "branch"], cwd)
