import asyncio
import os
import json
import logging
import re
import aiofiles
from typing import List, Dict, Any, Optional, Union, Callable

logger = logging.getLogger(__name__)

# Import failover manager for automatic model switching on rate limits/errors
try:
    from providers.failover_manager import get_failover_manager, FailoverManager
    FAILOVER_ENABLED = True
except ImportError:
    FAILOVER_ENABLED = False
    logger.warning("Failover manager not available - automatic model switching disabled")

class AgentNode:
    """
    Standard Agent/LLM Node with Tool Support and Validation.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.max_retries = 3

    async def execute(self, inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Context extraction from the 'context' dict provided by WorkflowEngine
        workflow_engine = context.get('engine')
        node = context.get('node')
        input_text = inputs.get('text') or inputs.get('query', '')
        raw_context = context.get('context_str', '') # Pre-built context from predecessors
        persona_override = context.get('persona_override')
        
        if not workflow_engine or not node:
            return {"ok": False, "error": "Missing engine or node in execution context"}

        # Increment iteration count (moved from WorkflowEngine)
        node.iteration_count += 1
        
        provider = await workflow_engine._get_provider(node)
        if not provider:
            return {"ok": False, "error": f"Provider {node.provider} not available"}
        
        current_retry = 0
        correction_message = ""
        
        while current_retry < self.max_retries:
            try:
                # Enhanced AntiGravity Tool Injection with Project Builder capabilities
                tools_prompt = """
## 🛠️ ANTIGRAVITY TOOLS - Full Development Capabilities

You have FULL ACCESS to create, modify, and manage game projects. Use these XML blocks in your output:

### FILE OPERATIONS
<read_file path="path/to/file"/> : Read file content
<write_file path="path/to/file">content here</write_file> : Create/overwrite file
<append_file path="path/to/file">content to append</append_file> : Append to file
<delete_file path="path/to/file"/> : Delete a file

### DIRECTORY OPERATIONS
<create_dir path="path/to/directory"/> : Create directory (including parents)
<list_dir path="path/to/directory"/> : List directory contents
<delete_dir path="path/to/directory"/> : Delete directory and contents
<copy path="source" to="destination"/> : Copy file or directory
<move path="source" to="destination"/> : Move/rename file or directory

### PROJECT SCAFFOLDING
<scaffold_project name="project-name" template="template-type"/>
Templates available: web-game, incremental-game, tower-defense

### PACKAGE MANAGEMENT
<install_package name="package-name" manager="npm"/> : Install a package (npm, yarn, pip)
<install_tool name="tool-name"/> : Install approved tools

Approved tools: phaser, pixijs, three, babylon, kaboom, vite, typescript, jest,
lodash, howler, gsap, matter-js, pygame, sharp, webpack, esbuild

### COMMAND EXECUTION
<run_command command="your command here" timeout="120"/> : Execute shell command
<run_build command="npm run build"/> : Run project build
<start_dev_server command="npm run dev"/> : Start development server

### PROJECT STRUCTURE EXAMPLE
For a Tower Defense Incremental game, create this structure:
```
exports/games/your_project/
├── src/
│   ├── core/         (Game state, save system, tick system)
│   ├── entities/     (Towers, enemies, projectiles)
│   ├── systems/      (Combat, economy, prestige, upgrades)
│   ├── ui/           (HUD, menus, panels)
│   └── data/         (JSON configs for towers, waves, prestige tiers)
├── public/
│   └── assets/       (images/, audio/, fonts/)
├── docs/             (GDD.md, BALANCE.md, technical docs)
└── package.json
```

### IMPORTANT GUIDELINES
1. ALWAYS create proper directory structures before writing files
2. Use JSON files for game data (towers, enemies, upgrades, prestige tiers)
3. Create comprehensive documentation in docs/ folder
4. Initialize npm/package.json for JavaScript projects
5. Install required dependencies (phaser, vite, typescript, etc.)
6. Build incrementally - create core systems first, then expand

YOU HAVE FULL PERMISSION to create files, install packages, and run commands.
"""
                # Build rich system prompt
                system_prompt_parts = [persona_override if persona_override else node.persona]
                
                if node.backstory:
                    system_prompt_parts.append(f"\n## Backstory & Context\n{node.backstory}")
                
                # Memory Context Injection
                if workflow_engine.current_workflow.memory:
                    mem_context = await workflow_engine.current_workflow.memory.get_context()
                    if mem_context:
                        system_prompt_parts.append(f"\n## Conversation History (Summarized)\n{mem_context}")

                system_prompt_parts.append("\n" + tools_prompt)
                
                final_system_prompt = "\n".join(system_prompt_parts)

                # Prepare final user message (with correction if needed)
                final_user_message = input_text
                if correction_message:
                    final_user_message += f"\n\n⚠️ **ERROR IN PREVIOUS ATTEMPT:**\n{correction_message}\n\nPlease fix the output and try again."

                # Add to memory buffer before generating
                if workflow_engine.current_workflow.memory:
                    workflow_engine.current_workflow.memory.add_message("user", input_text)

                # Dynamic Model Selection (Model Weight Auditing)
                current_model = node.model
                current_provider_id = node.provider
                if node.tier == "paid" and len(final_user_message) > 5000:
                    # Scale to 'large' model if on paid tier and input is heavy
                    if "deepseek-r1" in current_model.lower():
                        current_model = "gpt-4o" # Example upgrade path
                        await workflow_engine.log(node.name, f"🚀 **[HIGH WEIGHT]** Context heavy ({len(final_user_message)} chars). Scaled to {current_model}.")

                # Use failover manager for automatic model switching on rate limits/errors
                if FAILOVER_ENABLED:
                    failover_mgr = get_failover_manager()

                    async def generate_task(prov_id: str, model: str):
                        """Task wrapper for failover execution."""
                        # Get the provider for the specified type
                        task_provider = await workflow_engine._get_provider_by_type(prov_id, model)
                        if not task_provider:
                            raise Exception(f"Provider {prov_id} not available")
                        return await task_provider.generate(
                            system_prompt=final_system_prompt,
                            user_message=final_user_message,
                            context=raw_context if raw_context else None,
                            model_override=model,
                            on_thought=lambda t: asyncio.create_task(workflow_engine.emit_thought(node.name, t))
                        )

                    def on_failover(old_prov, old_model, new_prov, new_model, reason):
                        """Callback when failover occurs."""
                        # Log synchronously (will be handled by workflow engine)
                        logger.info(f"Failover: {old_prov}/{old_model} → {new_prov}/{new_model} (Reason: {reason})")

                    # Determine task category from node type or context
                    task_category = getattr(node, 'category', 'general')
                    if not task_category or task_category not in ['coding', 'writing', 'designing', 'graphics', 'art', 'general']:
                        # Infer from content
                        content_lower = (input_text + final_system_prompt).lower()
                        if any(word in content_lower for word in ['code', 'programming', 'function', 'script', 'bug', 'debug']):
                            task_category = 'coding'
                        elif any(word in content_lower for word in ['write', 'story', 'article', 'essay', 'text']):
                            task_category = 'writing'
                        elif any(word in content_lower for word in ['design', 'ui', 'layout', 'interface']):
                            task_category = 'designing'
                        elif any(word in content_lower for word in ['graphic', 'image', 'visual', 'artwork']):
                            task_category = 'graphics'
                        elif any(word in content_lower for word in ['art', 'creative', 'drawing', 'painting']):
                            task_category = 'art'
                        else:
                            task_category = 'general'

                    output, final_provider, final_model = await failover_mgr.execute_with_failover(
                        provider_id=current_provider_id,
                        model=current_model,
                        task=generate_task,
                        on_failover=on_failover,
                        task_category=task_category
                    )

                    # Log if model changed
                    if final_provider != current_provider_id or final_model != current_model:
                        await workflow_engine.log(
                            node.name,
                            f"✅ **[FAILOVER SUCCESS]** Completed using {final_provider}/{final_model}"
                        )
                else:
                    # Fallback to direct generation without failover
                    output = await provider.generate(
                        system_prompt=final_system_prompt,
                        user_message=final_user_message,
                        context=raw_context if raw_context else None,
                        model_override=current_model,
                        on_thought=lambda t: asyncio.create_task(workflow_engine.emit_thought(node.name, t))
                    )

                # Add assistant output to memory buffer
                if workflow_engine.current_workflow.memory:
                    history_output = workflow_engine._strip_thinking(output, node.name)
                    workflow_engine.current_workflow.memory.add_message("assistant", history_output[:500] + ("..." if len(history_output) > 500 else ""))
                    # Periodic pruning
                    await workflow_engine.current_workflow.memory.prune(provider)

                # Tool Extraction & Execution (Simplified move from Engine)
                # Note: These tools could eventually be separate MCP tools!
                await self._process_tools(output, node, workflow_engine)

                # Blackboard State Updates
                workflow_engine._process_blackboard_tags(output)

                # New: Catch any thoughts that weren't streamed but are in the final output
                output = workflow_engine._strip_thinking(output, node.name)
                
                # ============ Auto-fixing Validation ============
                from core.workflow import AgreementValidator
                validator = AgreementValidator()
                validation_res = validator.validate(output, node.agreement_rules)
                
                if validation_res["passed"]:
                    return {"ok": True, "output": output}
                else:
                    failed = validation_res["failed_required"]
                    if failed:
                        current_retry += 1
                        if current_retry < self.max_retries:
                            await workflow_engine.log(node.name, f"🔄 **Validation Failed** (Required: {', '.join(failed)}). Retrying {current_retry}/{self.max_retries}...")
                            correction_message = f"Your output failed the following validation rules: {', '.join(failed)}."
                            if any(r.type in ["json", "schema"] for r in node.agreement_rules if r.name in failed):
                                correction_message += " Please ensure your output is valid JSON or matches the requested schema."
                            continue
                        else:
                            return {"ok": False, "error": f"Validation failed: {', '.join(failed)}"}

            except Exception as e:
                import traceback
                logger.error(f"AgentNode Execution Error: {e}\n{traceback.format_exc()}")
                current_retry += 1
                if current_retry >= self.max_retries:
                    return {"ok": False, "error": str(e)}
                await asyncio.sleep(1) # Backoff
        
        return {"ok": False, "error": "Max retries reached"}

    async def _process_tools(self, output: str, node: Any, engine: Any):
        """Handle tool extraction and execution using enhanced ToolProcessor."""
        try:
            from core.tools.tool_processor import process_tools
            results = await process_tools(output, node, engine)

            # Log summary if any tools were used
            total_actions = (
                len(results.get("files_created", [])) +
                len(results.get("dirs_created", [])) +
                len(results.get("commands_run", [])) +
                len(results.get("packages_installed", []))
            )
            if total_actions > 0:
                await engine.log(node.name, f"🔧 Tool Actions: {total_actions} operations completed")
        except ImportError:
            # Fallback to basic tool processing if enhanced processor not available
            await self._process_tools_basic(output, node, engine)

    async def _process_tools_basic(self, output: str, node: Any, engine: Any):
        """Basic fallback tool processing."""
        # 1. <write_file path="...">content</write_file>
        write_matches = re.finditer(r'<write_file\s+path=["\'](.*?)["\']>(.*?)</write_file>', output, re.DOTALL)
        for match in write_matches:
            file_path = match.group(1)
            file_content = match.group(2).strip()
            target_path = os.path.normpath(os.path.join(os.getcwd(), file_path))
            if not target_path.startswith(os.getcwd()):
                 await engine.log(node.name, f"❌ Security Error: blocked write to {file_path}")
                 continue
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                async with aiofiles.open(target_path, "w", encoding="utf-8") as f:
                    await f.write(file_content)
                await engine.log(node.name, f"💾 Created/Updated file: {file_path}")
            except Exception as fe:
                await engine.log(node.name, f"❌ File Tool Error: {fe}")

        # 2. <run_command command="..."/>
        cmd_matches = re.finditer(r'<run_command\s+command=["\'](.*?)["\']\s*/>', output)
        for match in cmd_matches:
            cmd = match.group(1)
            try:
                await engine.log(node.name, f"⚙️ Executing: {cmd}")
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=os.getcwd()
                )
                stdout, stderr = await process.communicate()
                result_text = stdout.decode().strip() or stderr.decode().strip() or "Success (No Output)"
                await engine.emit_thought(node.name, f"### COMMAND RESULT: `{cmd}`\n```\n{result_text}\n```")
            except Exception as ce:
                await engine.log(node.name, f"❌ Command Tool Error: {ce}")
