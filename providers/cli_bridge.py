"""
CLI Bridge Provider - Bridges to Gemini CLI/OpenCode via subprocess.
"""
import asyncio
import subprocess
import logging
import os
import json
from typing import Optional, Dict, List, Any, Callable
from providers import LLMProvider, ProviderType

logger = logging.getLogger(__name__)


class CLIBridgeProvider(LLMProvider):
    """
    CLI Bridge provider that routes prompts through external CLI tools.
    
    Supports:
    - Gemini CLI (gemini)
    - OpenCode CLI
    - Any CLI that accepts stdin and returns stdout
    """
    
    provider_type = ProviderType.CLI_BRIDGE
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.cli_command = config.get('command', 'gemini')
        self.cli_args = config.get('args', [])
        self.timeout = config.get('timeout', 120)
        self.shell = config.get('shell', True)
        self.working_dir = config.get('working_dir', os.getcwd())
    
    async def initialize(self) -> bool:
        """Verify the CLI tool is available."""
        try:
            # Check if command exists
            result = await asyncio.create_subprocess_shell(
                f"where {self.cli_command}" if os.name == 'nt' else f"which {self.cli_command}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            
            if result.returncode == 0:
                self._initialized = True
                logger.info(f"CLI Bridge initialized with command: {self.cli_command}")
                return True
            
            logger.warning(f"CLI command not found: {self.cli_command}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize CLI Bridge: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if the CLI tool is accessible."""
        return self._initialized
    
    async def generate(self, system_prompt: str, user_message: str, context: Optional[str] = None, on_thought: Optional[Callable] = None, model_override: Optional[str] = None) -> str:
        """Generate response by calling the CLI tool."""
        
        if on_thought:
            escaped_cmd = self.cli_command.replace('\\', '\\\\')
            on_thought(f"Executing CLI command: {escaped_cmd}...")
        
        # Build the prompt to send
        full_prompt = self._build_prompt(system_prompt, user_message, context)
        
        try:
            # Create the command
            cmd = self._build_command(full_prompt)
            
            # Execute the CLI command
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir
            )
            
            # Send prompt and wait for response
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=full_prompt.encode()),
                timeout=self.timeout
            )
            
            if process.returncode == 0:
                response = stdout.decode().strip()
                return response if response else "No response from CLI"
            else:
                error = stderr.decode().strip()
                logger.error(f"CLI error: {error}")
                return f"CLI Error: {error}"
                
        except asyncio.TimeoutError:
            logger.error("CLI command timed out")
            return "Error: CLI command timed out"
        except Exception as e:
            logger.error(f"CLI Bridge error: {e}")
            return f"Error: {str(e)}"
    
    def _build_prompt(self, system_prompt: str, user_message: str, context: Optional[str]) -> str:
        """Build the full prompt string."""
        parts = [f"System: {system_prompt}"]
        if context:
            parts.append(f"\nContext:\n{context}")
        parts.append(f"\nUser: {user_message}")
        return "\n".join(parts)
    
    def _escape_for_shell(self, text: str, for_wsl: bool = False) -> str:
        """
        Properly escape text for shell execution.

        This uses a more robust escaping strategy:
        - For Windows/PowerShell: escape special characters
        - For Unix/WSL: use single quotes with proper escaping
        """
        if not text:
            return '""'

        # Replace newlines with spaces
        text = text.replace('\n', ' ').replace('\r', '')

        if for_wsl or os.name != 'nt':
            # Unix-style escaping: wrap in single quotes, escape existing single quotes
            # 'text' -> 'text' (already quoted)
            # text's -> 'text'\''s' (break out of quotes, add escaped quote, continue)
            escaped = text.replace("'", "'\"'\"'")
            return f"'{escaped}'"
        else:
            # Windows-style escaping: escape double quotes and special chars
            # Use ^ to escape special characters in cmd.exe
            special_chars = ['&', '|', '<', '>', '^', '%']
            for char in special_chars:
                text = text.replace(char, f'^{char}')
            text = text.replace('"', '\\"')
            return f'"{text}"'

    def _build_command(self, prompt: str) -> str:
        """Build the CLI command string with proper escaping."""
        # Build command based on CLI type
        cmd_lower = self.cli_command.lower()

        # Check if we should use WSL
        use_wsl = 'wsl' in cmd_lower or '/home/' in cmd_lower

        # Escape the prompt appropriately
        escaped_prompt = self._escape_for_shell(prompt, for_wsl=use_wsl)

        if use_wsl:
            # Format for WSL execution
            # Ensure we use the full path to opencode if provided
            executable = self.cli_command
            if '/home/' in executable and not executable.startswith('wsl'):
                executable = f'wsl -d Ubuntu -e {executable}'

            if 'gemini' in cmd_lower:
                return f'{executable} --prompt {escaped_prompt}'
            elif 'opencode' in cmd_lower:
                # OpenCode run message
                return f'{executable} run {escaped_prompt}'
            else:
                return f'{executable} {escaped_prompt}'

        if 'gemini' in cmd_lower:
            # Use stdin piping - safer than command line arguments
            return f'echo {escaped_prompt} | {self.cli_command}'
        elif 'opencode' in cmd_lower:
            return f'{self.cli_command} run {escaped_prompt}'
        else:
            args = ' '.join(self.cli_args)
            return f'{self.cli_command} {args} {escaped_prompt}'


class GeminiCLIProvider(CLIBridgeProvider):
    """Specialized CLI Bridge for Gemini CLI."""
    
    def __init__(self, config: Dict[str, Any]):
        config.setdefault('command', 'gemini')
        super().__init__(config)
    
    async def generate(self, system_prompt: str, user_message: str, context: Optional[str] = None, on_thought: Optional[Callable] = None, model_override: Optional[str] = None) -> str:
        """Use Gemini CLI with proper formatting."""
        if on_thought:
            on_thought("Sending to Gemini CLI...")
        
        full_prompt = self._build_prompt(system_prompt, user_message, context)
        
        try:
            # Gemini CLI typically reads from interactive input
            # We'll use a temp file approach for complex prompts
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(full_prompt)
                temp_path = f.name
            
            try:
                process = await asyncio.create_subprocess_shell(
                    f'{self.cli_command} < "{temp_path}"',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.working_dir
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
                
                return stdout.decode().strip() if stdout else "No response"
                
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Gemini CLI error: {e}")
            return f"Error: {str(e)}"
