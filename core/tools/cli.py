import subprocess
import shlex
import logging
import re
import os
from typing import Dict, Any, List, Union

logger = logging.getLogger(__name__)

# Blocked commands that could be dangerous
BLOCKED_COMMANDS = {
    'rm -rf /',
    'rm -rf /*',
    'mkfs',
    'dd if=/dev/zero',
    ':(){:|:&};:',  # Fork bomb
}

# Allowed commands whitelist (optional, can be enabled for stricter security)
ALLOWED_COMMAND_PREFIXES = None  # Set to a list like ['git', 'python', 'npm'] to restrict


class CLITool:
    """
    Executes shell commands on the host system.
    WARNING: This provides powerful access. Use with caution.

    Security improvements:
    - Command validation and sanitization
    - Option to use argument lists instead of shell=True
    - Blocked dangerous command patterns
    - Configurable command whitelist
    """

    @staticmethod
    def _validate_command(command: str) -> bool:
        """Validate command against blocked patterns."""
        command_lower = command.lower().strip()

        # Check blocked commands
        for blocked in BLOCKED_COMMANDS:
            if blocked in command_lower:
                logger.warning(f"Blocked dangerous command pattern: {command}")
                return False

        # Check whitelist if enabled
        if ALLOWED_COMMAND_PREFIXES is not None:
            first_word = command_lower.split()[0] if command_lower else ''
            if not any(first_word.startswith(prefix) for prefix in ALLOWED_COMMAND_PREFIXES):
                logger.warning(f"Command not in whitelist: {command}")
                return False

        return True

    @staticmethod
    def execute(command: str, cwd: str = ".", use_shell: bool = True, timeout: int = 60) -> Dict[str, Any]:
        """
        Runs a command and returns the output.

        Args:
            command: The command to execute
            cwd: Working directory
            use_shell: If False, parses command into args list (safer but no pipes/redirects)
            timeout: Command timeout in seconds
        """
        # Validate working directory
        if not os.path.isdir(cwd):
            return {"success": False, "error": f"Invalid working directory: {cwd}"}

        # Validate command
        if not CLITool._validate_command(command):
            return {"success": False, "error": "Command blocked by security policy"}

        logger.info(f"Executing CLI command: {command} in {cwd}")

        try:
            if use_shell:
                # Shell mode - needed for pipes, redirects, etc.
                # Less secure but more flexible
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            else:
                # Argument list mode - safer, no shell injection possible
                args = shlex.split(command)
                result = subprocess.run(
                    args,
                    cwd=cwd,
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out ({timeout}s limit)"}
        except ValueError as e:
            # shlex.split can raise ValueError on malformed input
            logger.error(f"Invalid command syntax: {e}")
            return {"success": False, "error": f"Invalid command syntax: {e}"}
        except Exception as e:
            logger.error(f"CLI Error: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def execute_safe(args: List[str], cwd: str = ".", timeout: int = 60) -> Dict[str, Any]:
        """
        Execute a command using an argument list (no shell injection possible).

        Args:
            args: List of command arguments, e.g., ['git', 'status']
            cwd: Working directory
            timeout: Command timeout in seconds
        """
        if not args:
            return {"success": False, "error": "No command provided"}

        # Validate working directory
        if not os.path.isdir(cwd):
            return {"success": False, "error": f"Invalid working directory: {cwd}"}

        logger.info(f"Executing CLI command (safe): {' '.join(args)} in {cwd}")

        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out ({timeout}s limit)"}
        except Exception as e:
            logger.error(f"CLI Error: {e}")
            return {"success": False, "error": str(e)}
