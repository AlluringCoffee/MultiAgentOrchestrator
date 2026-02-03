"""
Enhanced Tool Processor - Handles all AntiGravity tool XML blocks in agent output.

This module provides comprehensive tool processing for:
- File operations (read, write, append, delete)
- Directory operations (create, list, delete, copy, move)
- Project scaffolding
- Package management
- Command execution
- Build operations
"""

import os
import re
import asyncio
import shutil
import aiofiles
import logging
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolProcessor:
    """Processes AntiGravity tool XML blocks from agent output."""

    def __init__(self, engine: Any, node: Any, base_dir: Optional[str] = None):
        self.engine = engine
        self.node = node
        self.base_dir = base_dir or os.getcwd()
        self.results: Dict[str, list] = {
            "files_created": [],
            "files_deleted": [],
            "dirs_created": [],
            "commands_run": [],
            "packages_installed": [],
            "errors": [],
        }

    def _safe_path(self, path: str) -> Optional[str]:
        """Validate and return safe absolute path within base_dir."""
        target = os.path.normpath(os.path.join(self.base_dir, path))
        if not target.startswith(self.base_dir):
            return None
        return target

    async def log(self, message: str):
        """Log a message through the engine."""
        if self.engine and hasattr(self.engine, 'log'):
            await self.engine.log(self.node.name, message)
        else:
            logger.info(f"[{self.node.name}] {message}")

    async def emit_thought(self, content: str):
        """Emit a thought through the engine."""
        if self.engine and hasattr(self.engine, 'emit_thought'):
            await self.engine.emit_thought(self.node.name, content)

    async def process_all(self, output: str):
        """Process all tool blocks in the output."""
        await self._process_write_file(output)
        await self._process_read_file(output)
        await self._process_list_dir(output)
        await self._process_create_dir(output)
        await self._process_delete_file(output)
        await self._process_delete_dir(output)
        await self._process_append_file(output)
        await self._process_copy(output)
        await self._process_move(output)
        await self._process_scaffold_project(output)
        await self._process_install_package(output)
        await self._process_install_tool(output)
        await self._process_run_command(output)
        await self._process_run_build(output)

        return self.results

    def _clean_content(self, content: str) -> str:
        """Clean content by removing markdown code fences and extra whitespace."""
        content = content.strip()
        # Remove markdown code fences like ```typescript or ```json
        content = re.sub(r'^```\w*\s*\n?', '', content)
        content = re.sub(r'\n?```\s*$', '', content)
        return content.strip()

    async def _process_write_file(self, output: str):
        """Handle <write_file path="...">content</write_file>"""
        matches = re.finditer(r'<write_file\s+path=["\'](.*?)["\']>(.*?)</write_file>', output, re.DOTALL)
        for match in matches:
            file_path = match.group(1)
            content = self._clean_content(match.group(2))
            target = self._safe_path(file_path)
            if not target:
                await self.log(f"❌ Security: blocked write to {file_path}")
                self.results["errors"].append(f"Blocked write: {file_path}")
                continue
            if not content:
                await self.log(f"⚠️ Skipped empty file: {file_path}")
                continue
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                async with aiofiles.open(target, "w", encoding="utf-8") as f:
                    await f.write(content)
                await self.log(f"💾 Created/Updated: {file_path} ({len(content)} chars)")
                self.results["files_created"].append(file_path)
            except Exception as e:
                await self.log(f"❌ Write Error: {e}")
                self.results["errors"].append(str(e))

    async def _process_read_file(self, output: str):
        """Handle <read_file path="..."/>"""
        matches = re.finditer(r'<read_file\s+path=["\'](.*?)["\']\s*/>', output)
        for match in matches:
            file_path = match.group(1)
            target = self._safe_path(file_path)
            if not target:
                await self.log(f"❌ Security: blocked read of {file_path}")
                continue
            try:
                if os.path.exists(target):
                    async with aiofiles.open(target, "r", encoding="utf-8") as f:
                        content = await f.read()
                    preview = content[:2000] + ("\n*(truncated...)*" if len(content) > 2000 else "")
                    await self.emit_thought(f"### READ FILE: `{file_path}`\n```\n{preview}\n```")
                    await self.log(f"📖 Read: {file_path}")
                else:
                    await self.log(f"⚠️ File not found: {file_path}")
            except Exception as e:
                await self.log(f"❌ Read Error: {e}")

    async def _process_list_dir(self, output: str):
        """Handle <list_dir path="..."/>"""
        matches = re.finditer(r'<list_dir\s+path=["\'](.*?)["\']\s*/>', output)
        for match in matches:
            dir_path = match.group(1)
            target = self._safe_path(dir_path)
            if not target:
                await self.log(f"❌ Security: blocked list of {dir_path}")
                continue
            try:
                if os.path.exists(target) and os.path.isdir(target):
                    items = os.listdir(target)
                    formatted = "\n".join([f"- {'📁 ' if os.path.isdir(os.path.join(target, f)) else '📄 '}{f}" for f in items])
                    await self.emit_thought(f"### LIST DIR: `{dir_path}`\n{formatted}")
                    await self.log(f"📂 Listed: {dir_path} ({len(items)} items)")
                else:
                    await self.log(f"⚠️ Directory not found: {dir_path}")
            except Exception as e:
                await self.log(f"❌ List Error: {e}")

    async def _process_create_dir(self, output: str):
        """Handle <create_dir path="..."/>"""
        matches = re.finditer(r'<create_dir\s+path=["\'](.*?)["\']\s*/>', output)
        for match in matches:
            dir_path = match.group(1)
            target = self._safe_path(dir_path)
            if not target:
                await self.log(f"❌ Security: blocked mkdir {dir_path}")
                continue
            try:
                os.makedirs(target, exist_ok=True)
                await self.log(f"📁 Created directory: {dir_path}")
                self.results["dirs_created"].append(dir_path)
            except Exception as e:
                await self.log(f"❌ Mkdir Error: {e}")

    async def _process_delete_file(self, output: str):
        """Handle <delete_file path="..."/>"""
        matches = re.finditer(r'<delete_file\s+path=["\'](.*?)["\']\s*/>', output)
        for match in matches:
            file_path = match.group(1)
            target = self._safe_path(file_path)
            if not target:
                await self.log(f"❌ Security: blocked delete {file_path}")
                continue
            try:
                if os.path.exists(target) and os.path.isfile(target):
                    os.unlink(target)
                    await self.log(f"🗑️ Deleted file: {file_path}")
                    self.results["files_deleted"].append(file_path)
            except Exception as e:
                await self.log(f"❌ Delete Error: {e}")

    async def _process_delete_dir(self, output: str):
        """Handle <delete_dir path="..."/>"""
        matches = re.finditer(r'<delete_dir\s+path=["\'](.*?)["\']\s*/>', output)
        for match in matches:
            dir_path = match.group(1)
            target = self._safe_path(dir_path)
            if not target:
                await self.log(f"❌ Security: blocked rmdir {dir_path}")
                continue
            try:
                if os.path.exists(target) and os.path.isdir(target):
                    shutil.rmtree(target)
                    await self.log(f"🗑️ Deleted directory: {dir_path}")
            except Exception as e:
                await self.log(f"❌ Rmdir Error: {e}")

    async def _process_append_file(self, output: str):
        """Handle <append_file path="...">content</append_file>"""
        matches = re.finditer(r'<append_file\s+path=["\'](.*?)["\']>(.*?)</append_file>', output, re.DOTALL)
        for match in matches:
            file_path = match.group(1)
            content = match.group(2).strip()
            target = self._safe_path(file_path)
            if not target:
                await self.log(f"❌ Security: blocked append to {file_path}")
                continue
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                async with aiofiles.open(target, "a", encoding="utf-8") as f:
                    await f.write(content + "\n")
                await self.log(f"📝 Appended to: {file_path}")
            except Exception as e:
                await self.log(f"❌ Append Error: {e}")

    async def _process_copy(self, output: str):
        """Handle <copy path="..." to="..."/>"""
        matches = re.finditer(r'<copy\s+path=["\'](.*?)["\']\s+to=["\'](.*?)["\']\s*/>', output)
        for match in matches:
            src, dst = match.group(1), match.group(2)
            src_path = self._safe_path(src)
            dst_path = self._safe_path(dst)
            if not src_path or not dst_path:
                await self.log(f"❌ Security: blocked copy")
                continue
            try:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
                await self.log(f"📋 Copied: {src} → {dst}")
            except Exception as e:
                await self.log(f"❌ Copy Error: {e}")

    async def _process_move(self, output: str):
        """Handle <move path="..." to="..."/>"""
        matches = re.finditer(r'<move\s+path=["\'](.*?)["\']\s+to=["\'](.*?)["\']\s*/>', output)
        for match in matches:
            src, dst = match.group(1), match.group(2)
            src_path = self._safe_path(src)
            dst_path = self._safe_path(dst)
            if not src_path or not dst_path:
                await self.log(f"❌ Security: blocked move")
                continue
            try:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.move(src_path, dst_path)
                await self.log(f"📦 Moved: {src} → {dst}")
            except Exception as e:
                await self.log(f"❌ Move Error: {e}")

    async def _process_scaffold_project(self, output: str):
        """Handle <scaffold_project name="..." template="..."/>"""
        matches = re.finditer(r'<scaffold_project\s+name=["\'](.*?)["\'](?:\s+template=["\'](.*?)["\'])?\s*/>', output)
        for match in matches:
            name = match.group(1)
            template = match.group(2) or "web-game"
            try:
                from core.tools.project_builder import scaffold_project
                await self.log(f"🏗️ Scaffolding: {name} (template: {template})")
                result = await scaffold_project(name, template)
                if result["success"]:
                    await self.log(f"✅ Project created: {result['project_path']}")
                    await self.emit_thought(f"### PROJECT SCAFFOLDED\nPath: {result['project_path']}\nTemplate: {template}")
                else:
                    await self.log(f"❌ Scaffold Error: {result.get('error')}")
            except Exception as e:
                await self.log(f"❌ Scaffold Error: {e}")

    async def _process_install_package(self, output: str):
        """Handle <install_package name="..." manager="..."/>"""
        matches = re.finditer(r'<install_package\s+name=["\'](.*?)["\'](?:\s+manager=["\'](.*?)["\'])?\s*/>', output)
        for match in matches:
            package = match.group(1)
            manager = match.group(2) or "npm"
            try:
                await self.log(f"📦 Installing: {package} via {manager}")
                cmd_map = {
                    "npm": f"npm install {package}",
                    "yarn": f"yarn add {package}",
                    "pip": f"pip install {package}",
                    "pnpm": f"pnpm add {package}",
                }
                cmd = cmd_map.get(manager, f"npm install {package}")
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.base_dir
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
                if process.returncode == 0:
                    await self.log(f"✅ Installed: {package}")
                    self.results["packages_installed"].append(package)
                else:
                    await self.log(f"⚠️ Install warning: {stderr.decode()[:200]}")
            except asyncio.TimeoutError:
                await self.log(f"⏱️ Install timed out: {package}")
            except Exception as e:
                await self.log(f"❌ Install Error: {e}")

    async def _process_install_tool(self, output: str):
        """Handle <install_tool name="..."/>"""
        matches = re.finditer(r'<install_tool\s+name=["\'](.*?)["\']\s*/>', output)
        for match in matches:
            tool_name = match.group(1)
            try:
                from core.tools.project_builder import APPROVED_TOOLS
                if tool_name not in APPROVED_TOOLS:
                    await self.log(f"❌ Tool not approved: {tool_name}")
                    continue
                info = APPROVED_TOOLS[tool_name]
                if info["type"] == "system":
                    await self.log(f"⚠️ {tool_name} requires manual install")
                    continue
                await self.log(f"🔧 Installing tool: {tool_name} ({info['description']})")
                cmd = f"npm install {info['package']}" if info["type"] == "npm" else f"pip install {info['package']}"
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.base_dir
                )
                await asyncio.wait_for(process.communicate(), timeout=300)
                if process.returncode == 0:
                    await self.log(f"✅ Tool installed: {tool_name}")
                    self.results["packages_installed"].append(tool_name)
            except Exception as e:
                await self.log(f"❌ Tool Install Error: {e}")

    async def _process_run_command(self, output: str):
        """Handle <run_command command="..." timeout="..."/>"""
        matches = re.finditer(r'<run_command\s+command=["\'](.*?)["\'](?:\s+timeout=["\'](\d+)["\'])?\s*/>', output)
        for match in matches:
            cmd = match.group(1)
            timeout = int(match.group(2)) if match.group(2) else 120

            # Security check
            dangerous = ['rm -rf /', 'mkfs', 'dd if=/dev/', ':(){', 'chmod -R 777 /']
            if any(d in cmd.lower() for d in dangerous):
                await self.log(f"❌ Blocked dangerous command: {cmd[:50]}")
                continue

            try:
                await self.log(f"⚙️ Executing: {cmd}")
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.base_dir
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                result = stdout.decode().strip() or stderr.decode().strip() or "Success (No Output)"
                await self.emit_thought(f"### COMMAND: `{cmd}`\n```\n{result[:2000]}\n```")
                self.results["commands_run"].append(cmd)
            except asyncio.TimeoutError:
                await self.log(f"⏱️ Command timed out: {cmd}")
            except Exception as e:
                await self.log(f"❌ Command Error: {e}")

    async def _process_run_build(self, output: str):
        """Handle <run_build command="..."/>"""
        matches = re.finditer(r'<run_build(?:\s+command=["\'](.*?)["\'])?\s*/>', output)
        for match in matches:
            cmd = match.group(1) or "npm run build"
            try:
                await self.log(f"🔨 Running build: {cmd}")
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.base_dir
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
                if process.returncode == 0:
                    await self.log(f"✅ Build complete")
                else:
                    await self.log(f"❌ Build failed: {stderr.decode()[:500]}")
            except Exception as e:
                await self.log(f"❌ Build Error: {e}")


async def process_tools(output: str, node: Any, engine: Any, base_dir: Optional[str] = None) -> Dict[str, list]:
    """
    Convenience function to process all tools in an output string.

    Args:
        output: The agent output containing tool XML blocks
        node: The workflow node
        engine: The workflow engine
        base_dir: Base directory for file operations

    Returns:
        Dictionary of results (files_created, commands_run, etc.)
    """
    processor = ToolProcessor(engine, node, base_dir)
    return await processor.process_all(output)
