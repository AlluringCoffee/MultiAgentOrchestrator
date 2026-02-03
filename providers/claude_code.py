"""
Claude Code CLI Provider - Bridges to Claude Code CLI for using Anthropic API subscription.
"""
import asyncio
import subprocess
import logging
import os
import json
import tempfile
from typing import Optional, Dict, List, Any, Callable
from providers import LLMProvider, ProviderType

logger = logging.getLogger(__name__)


class ClaudeCodeProvider(LLMProvider):
    """
    Claude Code CLI provider that uses your existing Anthropic API subscription.

    Uses the `claude` CLI tool which handles authentication, context management,
    and provides access to Claude models (Sonnet, Opus, Haiku).
    """

    provider_type = ProviderType.CLI_BRIDGE

    # Model mapping for Claude Code CLI
    MODELS = {
        'claude-sonnet': 'sonnet',
        'claude-opus': 'opus',
        'claude-haiku': 'haiku',
        'sonnet': 'sonnet',
        'opus': 'opus',
        'haiku': 'haiku',
        'default': 'sonnet'
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.cli_path = config.get('cli_path', 'claude')
        self.default_model = config.get('model', 'sonnet')
        self.timeout = config.get('timeout', 300)  # 5 min default for Claude
        self.max_tokens = config.get('max_tokens', 4096)
        self.working_dir = config.get('working_dir', os.getcwd())
        self._initialized = False

    async def initialize(self) -> bool:
        """Verify Claude Code CLI is available and authenticated."""
        try:
            # Check if claude command exists
            result = await asyncio.create_subprocess_shell(
                f'"{self.cli_path}" --version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                version = stdout.decode().strip()
                logger.info(f"Claude Code CLI initialized: {version}")
                self._initialized = True
                return True

            logger.warning(f"Claude Code CLI not found or not authenticated")
            return False

        except Exception as e:
            logger.error(f"Failed to initialize Claude Code CLI: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if Claude Code CLI is accessible."""
        if not self._initialized:
            return await self.initialize()
        return self._initialized

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[str] = None,
        on_thought: Optional[Callable] = None,
        model_override: Optional[str] = None
    ) -> str:
        """Generate response using Claude Code CLI."""

        model = self.MODELS.get(model_override or self.default_model, 'sonnet')

        if on_thought:
            on_thought(f"Sending to Claude Code CLI (model: {model})...")

        # Build the full prompt
        full_prompt = self._build_prompt(system_prompt, user_message, context)

        try:
            # Write prompt to temp file for clean handling
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(full_prompt)
                temp_path = f.name

            try:
                # Use claude CLI with print mode for non-interactive output
                # --print flag outputs response directly without interactive mode
                cmd = f'"{self.cli_path}" --print --model {model} < "{temp_path}"'

                if on_thought:
                    on_thought(f"Executing: claude --print --model {model}")

                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.working_dir
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )

                if process.returncode == 0:
                    response = stdout.decode('utf-8', errors='replace').strip()
                    if on_thought:
                        on_thought(f"Claude response received ({len(response)} chars)")
                    return response if response else "No response from Claude"
                else:
                    error = stderr.decode('utf-8', errors='replace').strip()
                    logger.error(f"Claude CLI error: {error}")

                    # Check for common errors
                    if 'not authenticated' in error.lower():
                        return "Error: Claude Code CLI not authenticated. Run 'claude login' first."
                    elif 'rate limit' in error.lower():
                        return "Error: Rate limit exceeded. Please wait before retrying."

                    return f"Claude CLI Error: {error}"

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass

        except asyncio.TimeoutError:
            logger.error(f"Claude CLI timed out after {self.timeout}s")
            return f"Error: Claude CLI timed out after {self.timeout} seconds"
        except Exception as e:
            logger.error(f"Claude Code CLI error: {e}")
            return f"Error: {str(e)}"

    def _build_prompt(self, system_prompt: str, user_message: str, context: Optional[str]) -> str:
        """Build the full prompt string for Claude."""
        parts = []

        if system_prompt:
            parts.append(f"<system>\n{system_prompt}\n</system>")

        if context:
            parts.append(f"<context>\n{context}\n</context>")

        parts.append(f"<user>\n{user_message}\n</user>")

        return "\n\n".join(parts)

    async def list_models(self) -> List[str]:
        """Return available Claude models."""
        return list(self.MODELS.keys())


class ClaudeSonnetProvider(ClaudeCodeProvider):
    """Claude Sonnet - balanced speed and capability."""

    def __init__(self, config: Dict[str, Any]):
        config.setdefault('model', 'sonnet')
        super().__init__(config)


class ClaudeOpusProvider(ClaudeCodeProvider):
    """Claude Opus - most capable model for complex reasoning."""

    def __init__(self, config: Dict[str, Any]):
        config.setdefault('model', 'opus')
        config.setdefault('timeout', 600)  # 10 min for complex tasks
        super().__init__(config)


class ClaudeHaikuProvider(ClaudeCodeProvider):
    """Claude Haiku - fastest model for simple tasks."""

    def __init__(self, config: Dict[str, Any]):
        config.setdefault('model', 'haiku')
        config.setdefault('timeout', 120)  # 2 min for quick tasks
        super().__init__(config)
