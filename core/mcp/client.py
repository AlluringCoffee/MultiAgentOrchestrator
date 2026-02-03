import asyncio
import json
import logging
import uuid
import os

logger = logging.getLogger("MCPClient")

class MCPClient:
    def __init__(self, command: str, args: list = None, env: dict = None, cwd: str = None):
        self.command = command
        self.args = args or []
        self.env = env or os.environ.copy()
        self.cwd = cwd
        self.process = None
        self.pending_requests = {}
        self.reader_task = None
        self.server_capabilities = {}
        self.server_info = {}

    async def connect(self):
        """Starts the MCP server subprocess."""
        logger.info(f"Starting MCP Server: {self.command} {self.args}")
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
                cwd=self.cwd
            )
            self.reader_task = asyncio.create_task(self._read_loop())
            self.stderr_task = asyncio.create_task(self._read_stderr())
            logger.info("MCP Server subprocess started.")
        except Exception as e:
            logger.error(f"Failed to start MCP Server: {e}")
            raise

    async def _read_loop(self):
        """Reads JSON-RPC messages from stdout."""
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                
                line_str = line.decode('utf-8').strip()
                if not line_str:
                    continue
                
                try:
                    message = json.loads(line_str)
                    await self._handle_message(message)
                except json.JSONDecodeError:
                    logger.warning(f"MCP: Received invalid JSON: {line_str}")
        except Exception as e:
            logger.error(f"MCP Read Loop Error: {e}")
        finally:
            logger.info("MCP Read Loop ended.")

    async def _read_stderr(self):
        """Reads stderr from the subprocess."""
        try:
            while True:
                line = await self.process.stderr.readline()
                if not line:
                    break
                logger.error(f"MCP STDERR: {line.decode('utf-8').strip()}")
        except Exception as e:
            logger.error(f"MCP Stderr Loop Error: {e}")

    async def _handle_message(self, message):
        """Dispatches incoming JSON-RPC messages."""
        # Handle Responses
        if "id" in message and ("result" in message or "error" in message):
            req_id = message["id"]
            if req_id in self.pending_requests:
                future = self.pending_requests.pop(req_id)
                if "error" in message:
                    future.set_exception(Exception(f"MCP Error: {message['error']}"))
                else:
                    future.set_result(message["result"])
            return

        # Handle Notifications/Requests from Server (Not fully implemented yet)
        if "method" in message:
            logger.info(f"MCP Notification received: {message['method']}")
            # TODO: Handle server-to-client requests if needed (e.g. sampling)

    async def send_request(self, method, params=None):
        """Sends a JSON-RPC request and waits for the response."""
        req_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        
        future = asyncio.Future()
        self.pending_requests[req_id] = future
        
        await self._send_json(request)
        return await future

    async def send_notification(self, method, params=None):
        """Sends a JSON-RPC notification."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        await self._send_json(notification)

    async def _send_json(self, data):
        """Writes JSON to stdin."""
        if not self.process:
            raise Exception("MCP Client not connected")
        
        json_str = json.dumps(data) + "\n"
        self.process.stdin.write(json_str.encode('utf-8'))
        await self.process.stdin.drain()

    async def initialize(self):
        """Performs the MCP handshake."""
        response = await self.send_request("initialize", {
            "protocolVersion": "0.1.0",
            "capabilities": {
                "roots": {"listChanged": False},
                "sampling": {} 
            },
            "clientInfo": {
                "name": "AntigravityOrchestrator",
                "version": "1.0.0"
            }
        })
        
        self.server_capabilities = response.get("capabilities", {})
        self.server_info = response.get("serverInfo", {})
        
        await self.send_notification("notifications/initialized")
        return response

    async def list_tools(self):
        """Lists available tools."""
        return await self.send_request("tools/list")

    async def call_tool(self, name, arguments):
        """Calls a tool."""
        return await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

    async def close(self):
        """Terminates the server."""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self.process.kill()
