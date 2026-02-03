from typing import Dict, Any, List
import shlex
import json
import logging
from core.mcp.client import MCPClient

logger = logging.getLogger("MCPNode")

class MCPNode:
    """
    Executes MCP tools via stdio transport.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
    
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        command_str = self.config.get("command")
        if not command_str:
            return {"ok": False, "error": "MCP: command is required"}
        
        # Parse command string
        try:
            import sys
            import shlex
            posix_mode = sys.platform != 'win32'
            parts = shlex.split(command_str, posix=posix_mode)
            if not posix_mode:
                parts = [p.strip('"\'') for p in parts]
            cmd = parts[0]
            args = parts[1:]
        except Exception as e:
             return {"ok": False, "error": f"Failed to parse command: {e}"}

        logger.info(f"MCP Executing: {cmd} {args}")
        
        client = MCPClient(cmd, args)
        
        try:
            await client.connect()
            await client.initialize()
            
            tool_name = self.config.get("tool_name")
            
            if tool_name:
                logger.info(f"Calling Tool: {tool_name}")
                tool_args = self.config.get("tool_args", {})
                
                # Handle potentially stringified JSON from UI
                if isinstance(tool_args, str):
                    try:
                        if tool_args.strip():
                            tool_args = json.loads(tool_args)
                        else:
                            tool_args = {}
                    except json.JSONDecodeError:
                         return {"ok": False, "error": "Invalid JSON in tool_args"}
                
                # Merge inputs into tool_args if tool_args is empty or explicitly requests it
                # Strategy: If inputs contains keys that match tool_args missing required fields...
                # For now, simple strategy: data = tool_args | inputs (inputs override)
                if inputs:
                    if isinstance(tool_args, dict):
                        # Shallow merge: inputs take precedence for dynamic values
                        tool_args = {**tool_args, **inputs}
                
                result = await client.call_tool(tool_name, tool_args)
                return {
                    "ok": True, 
                    "output": json.dumps(result), 
                    "data": result
                }
            else:
                # Default: List Tools
                logger.info("Listing Tools")
                result = await client.list_tools()
                return {
                    "ok": True, 
                    "output": json.dumps(result), 
                    "data": result
                }
                
        except Exception as e:
            logger.error(f"MCP Execution Error: {e}")
            return {"ok": False, "error": f"MCP Error: {str(e)}"}
        finally:
            await client.close()
