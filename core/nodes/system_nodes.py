import os
import asyncio
import logging
import base64
import re
import shlex
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# URL validation for browser navigation
ALLOWED_BROWSER_SCHEMES = {'http', 'https', 'file'}
BLOCKED_BROWSER_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}


def validate_browser_url(url: str) -> tuple[bool, str]:
    """Validate URL for browser navigation."""
    if not url:
        return False, "Empty URL"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    if parsed.scheme.lower() not in ALLOWED_BROWSER_SCHEMES:
        return False, f"Protocol '{parsed.scheme}' not allowed"

    # For file:// URLs, be extra cautious
    if parsed.scheme == 'file':
        # Only allow file URLs if explicitly enabled
        return False, "file:// URLs are not allowed by default"

    return True, ""


class BrowserNode:
    """
    Executes browser-based tasks using Playwright.
    Supports "Live View" by emitting screenshots to the thought stream.

    Security improvements:
    - Configurable sandbox mode (defaults to sandboxed)
    - URL validation
    - Resource limits
    - Timeout protection
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.headless = config.get("headless", True)
        self.browser_type = config.get("browser", "chromium")
        # Security: Enable sandbox by default (disable only if explicitly needed)
        self.disable_sandbox = config.get("disable_sandbox", False)
        self.timeout = config.get("timeout", 30000)  # 30 second default

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        url = inputs.get("url")
        action = inputs.get("action", "navigate")
        selector = inputs.get("selector")
        text = inputs.get("text")

        if not url and action == "navigate":
            return {"ok": False, "error": "No URL provided for navigation"}

        # Validate URL
        if url:
            is_valid, error = validate_browser_url(url)
            if not is_valid:
                return {"ok": False, "error": f"Invalid URL: {error}"}

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {"ok": False, "error": "Playwright not installed"}

        async with async_playwright() as p:
            try:
                browser_launcher = getattr(p, self.browser_type)

                # Build browser args
                browser_args: List[str] = []
                if self.disable_sandbox:
                    # Only disable sandbox if explicitly configured
                    logger.warning("Browser sandbox disabled - this reduces security")
                    browser_args.extend(["--no-sandbox", "--disable-setuid-sandbox"])
                browser_args.append("--disable-dev-shm-usage")

                browser = await browser_launcher.launch(
                    headless=self.headless,
                    args=browser_args
                )
                page = await browser.new_page()
                
                try:
                    if action == "navigate" or url:
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                    
                    if action == "click" and selector:
                        await page.click(selector)
                    elif action == "type" and selector and text:
                        await page.type(selector, text)
                    elif action == "extract":
                        content = await page.content()
                        # Return content
                        await browser.close()
                        return {"ok": True, "output": content, "data": {"content": content}}
                    
                    # Take a screenshot for "Live View"
                    screenshot = await page.screenshot(type="jpeg", quality=50)
                    b64_screenshot = base64.b64encode(screenshot).decode('utf-8')
                    
                    final_url = page.url
                    final_title = await page.title()
                    content = await page.content()
                    
                    await browser.close()
                    return {
                        "ok": True, 
                        "output": f"Browser action '{action}' completed on {url}",
                        "data": {
                            "screenshot": b64_screenshot,
                            "url": final_url,
                            "title": final_title,
                            "content": content
                        }
                    }
                except Exception as e:
                    import traceback
                    err_msg = f"{str(e)}\n{traceback.format_exc()}"
                    logger.error(f"Browser internal error: {err_msg}")
                    await browser.close()
                    return {"ok": False, "error": err_msg}
            except Exception as e:
                import traceback
                err_msg = f"Failed to launch browser: {str(e)}\n{traceback.format_exc()}"
                logger.error(err_msg)
                return {"ok": False, "error": err_msg}

class ShellNode:
    """
    Executes local shell commands.

    Security improvements:
    - Command validation against blocked patterns
    - Configurable command whitelist
    - Working directory validation
    - Output size limits
    """
    # Dangerous command patterns to block
    BLOCKED_PATTERNS = [
        r'rm\s+(-rf?|--recursive).*/',  # Recursive delete of root paths
        r'mkfs\.',  # Format filesystems
        r'dd\s+.*if=/dev/(zero|random)',  # Dangerous dd operations
        r':\(\)\{.*\};:',  # Fork bomb
        r'>\s*/dev/sd[a-z]',  # Write to raw disk
        r'chmod\s+777\s+/',  # Dangerous permission changes at root
    ]

    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.cwd = config.get("cwd", ".")
        self.timeout = config.get("timeout", 30)
        self.max_output = config.get("max_output", 1024 * 1024)  # 1MB default
        self.allowed_commands: Optional[List[str]] = config.get("allowed_commands")

    def _validate_command(self, command: str) -> tuple[bool, str]:
        """Validate command against security rules."""
        if not command or not isinstance(command, str):
            return False, "Empty command"

        command_lower = command.lower()

        # Check blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, command_lower):
                return False, "Command matches blocked pattern"

        # Check whitelist if configured
        if self.allowed_commands is not None:
            first_word = command.split()[0] if command.strip() else ''
            if first_word not in self.allowed_commands:
                return False, f"Command '{first_word}' not in allowed list"

        return True, ""

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        command = inputs.get("command") or self.config.get("command")
        if not command:
            return {"ok": False, "error": "No command provided"}

        # Validate command
        is_valid, error = self._validate_command(command)
        if not is_valid:
            logger.warning(f"Command blocked: {error}")
            return {"ok": False, "error": f"Command blocked: {error}"}

        # Validate working directory
        if not os.path.isdir(self.cwd):
            return {"ok": False, "error": f"Invalid working directory: {self.cwd}"}

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()  # Ensure process is cleaned up
                return {"ok": False, "error": f"Command timed out after {self.timeout}s"}

            # Limit output size
            output = stdout[:self.max_output].decode('utf-8', errors='replace').strip()
            error_output = stderr[:self.max_output].decode('utf-8', errors='replace').strip()

            if len(stdout) > self.max_output or len(stderr) > self.max_output:
                logger.warning("Command output truncated due to size limit")

            if process.returncode == 0:
                return {"ok": True, "output": output, "data": {"stdout": output, "stderr": error_output}}
            else:
                return {
                    "ok": False,
                    "error": error_output or f"Command failed with code {process.returncode}",
                    "data": {"stdout": output, "stderr": error_output}
                }
        except OSError as e:
            logger.error(f"Shell execution error: {e}")
            return {"ok": False, "error": f"Execution error: {type(e).__name__}"}

class SystemNode:
    """
    Handles system-level actions like notifications.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        action = inputs.get("action", "notify")
        message = inputs.get("message") or inputs.get("text")
        
        if action == "notify" and message:
            try:
                # Basic notification simulation or use player/os specific tools
                # In a real app, you'd use plyer or similar
                logger.info(f"SYSTEM NOTIFICATION: {message}")
                return {"ok": True, "output": f"Notification sent: {message}"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        
        return {"ok": False, "error": f"Unsupported dynamic system action: {action}"}
