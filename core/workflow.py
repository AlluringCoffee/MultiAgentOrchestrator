"""
Workflow Engine - DAG-based execution of agent nodes with agreement parameters.
"""
import asyncio
import os
import json
import uuid
import logging
import aiofiles
from datetime import datetime
from typing import Dict, Any, Optional, List, Set, Callable, Union
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from core.tools import CLITool, GitTool, HFTool
from core.traffic_controller import global_traffic_controller, Priority


class NodeType(str, Enum):
    """Types of nodes in the workflow."""
    AGENT = "agent"
    AUDITOR = "auditor"
    INPUT = "input"
    OUTPUT = "output"
    ROUTER = "router"
    CHARACTER = "character"
    DIRECTOR = "director"
    OPTIMIZER = "optimizer"
    SCRIPT = "script"
    MEMORY = "memory"
    GITHUB = "github"
    HUGGINGFACE = "huggingface"
    HTTP = "http"
    OPENAPI = "openapi"
    NOTION = "notion"
    RAG = "rag"
    GOOGLE = "google"
    MCP = "mcp"
    COMFY = "comfy"
    ARCHITECT = "architect"
    CRITIC = "critic"
    TELEGRAM_TRIGGER = "telegram_trigger"
    DISCORD_TRIGGER = "discord_trigger"
    BROWSER = "browser"
    SHELL = "shell"
    SYSTEM = "system"
    A2UI = "a2ui"
    DISCOVERY = "discovery"

from core.memory import MemoryStore
from core.nodes.registry import NodeRegistry, initialize_default_registry
initialize_default_registry()


class NodeStatus(str, Enum):
    """Execution status of a node."""
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    PAUSED = "paused"


class AgreementRule(BaseModel):
    """A rule that must be satisfied to proceed to the next node."""
    name: str
    type: str = Field(default="contains", description="Type: contains, not_contains, min_words, max_words, regex, custom")
    value: Any = Field(default=None, description="Value to check against")
    required: bool = Field(default=True, description="If true, failure blocks progression")


class ExecutionSnapshot(BaseModel):
    """A snapshot of the workflow state at a specific point in time."""
    step_index: int
    node_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    blackboard: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list) # simplified log storage



class WorkflowNode(BaseModel):
    """A node in the workflow graph."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    type: Union[NodeType, str] = NodeType.AGENT
    
    # Visual positioning
    x: float = Field(default=100)
    y: float = Field(default=100)
    
    # Agent configuration
    persona: str = Field(default="", description="System prompt/persona")
    provider: str = Field(default="mock", description="LLM provider type")
    model: str = Field(default="default", description="Model name for provider")
    provider_config: Dict[str, Any] = Field(default_factory=dict)
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Static inputs for the node")
    
    # Narrative fields
    backstory: str = Field(default="", description="Character backstory or role description")
    requires_approval: bool = Field(default=False, description="Pause for human approval before completion")
    
    # Persistent Storage
    save_enabled: bool = Field(default=False, description="Whether to save this node's output to a file")
    save_path: Optional[str] = Field(default=None, description="Path to save the output file")
    
    # Execution state
    status: NodeStatus = NodeStatus.IDLE
    display_status: Optional[str] = Field(default=None, description="Custom status text for UI")
    output: Optional[str] = None
    error: Optional[str] = None
    
    # Recycling
    max_iterations: int = Field(default=1, description="Maximum number of times this node can run")
    iteration_count: int = Field(default=0, description="Current run count")
    
    # Agreement parameters
    agreement_rules: List[AgreementRule] = Field(default_factory=list)

    # Sub-Workflow / Fractal Capability
    # Sub-workflow attachments (Supports multiple)
    sub_workflows: List[Dict[str, Any]] = Field(default_factory=list, description="List of attached sub-workflows: {'path': '...', 'content': '...'}")
    return_event_bubble: bool = Field(default=True, description="If True, sub-workflow events bubble up to parent stream")
    
    # Dynamic Scaling / Optimizer
    internet_access: bool = Field(default=True, description="Enable internet-based tools (CLI/Browser)")
    tier: str = Field(default="free", description="Resource tier: 'free' or 'paid'")
    tier_config: Dict[str, Any] = Field(default_factory=dict, description="Configuration for tier-specific behavior")
    token_budget: int = Field(default=4096, description="Max token allowance for this node")
    
    # SCRIPT / Logic Node
    script_code: str = Field(default="", description="Python code for SCRIPT nodes")
    
    # Memory Config
    memory_config: Dict[str, Any] = Field(default_factory=lambda: {"action": "store"}, description="Configuration for Memory Node")

    class Config:
        use_enum_values = True


class WorkflowEdge(BaseModel):
    """A connection between two nodes."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str = Field(alias="source")
    target_id: str = Field(alias="target")
    label: Optional[str] = None
    
    # Conditional routing
    condition: Optional[str] = None  # "approve", "reject", "always"
    
    # Feedback/Loop edge (does not block initial execution)
    feedback: bool = Field(default=False, description="If True, predecessor completion is not required for execution")

    class Config:
        populate_by_name = True


class Workflow(BaseModel):
    """A complete workflow graph."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(default="New Workflow")
    description: str = Field(default="")
    
    nodes: Dict[str, WorkflowNode] = Field(default_factory=dict)
    edges: List[WorkflowEdge] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Runtime session fields (not persisted)
    session_folder: Optional[str] = Field(default=None, exclude=True)
    session_id: Optional[str] = Field(default=None, exclude=True)
    memory: Optional[Any] = Field(default=None, exclude=True)
    
    model_config = {"extra": "allow"}  # Allow dynamic attributes
    
    def add_node(self, node: WorkflowNode) -> str:
        """Add a node to the workflow."""
        self.nodes[node.id] = node
        self.updated_at = datetime.now()
        return node.id
    
    def remove_node(self, node_id: str):
        """Remove a node and its edges."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            self.edges = [e for e in self.edges if e.source_id != node_id and e.target_id != node_id]
            self.updated_at = datetime.now()
    
    def add_edge(self, edge: WorkflowEdge) -> str:
        """Add an edge between nodes."""
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            raise ValueError("Edge references non-existent nodes")
        self.edges.append(edge)
        self.updated_at = datetime.now()
        return edge.id
    
    def get_entry_nodes(self) -> List[str]:
        """Get nodes with no incoming edges (entry points)."""
        targets = {e.target_id for e in self.edges}
        return [nid for nid in self.nodes if nid not in targets]
    
    def get_successors(self, node_id: str) -> List[str]:
        """Get nodes that follow the given node."""
        return [e.target_id for e in self.edges if e.source_id == node_id]
    
    def get_predecessors(self, node_id: str) -> List[str]:
        """Get nodes that precede the given node."""
        return [e.source_id for e in self.edges if e.target_id == node_id]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize workflow for API/storage."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": {nid: n.model_dump() for nid, n in self.nodes.items()},
            "edges": [e.model_dump() for e in self.edges],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def validate(self, allow_cycles: bool = False):
        """Validate workflow for cycles and connectivity."""
        if allow_cycles:
            return True

        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        
        def is_cyclic(v, current_stack):
            visited.add(v)
            current_stack.add(v)
            
            # Only consider non-feedback edges for DAG validation
            successors = [e.target_id for e in self.edges if e.source_id == v and not e.feedback]
            
            for neighbor in successors:
                if neighbor not in visited:
                    if is_cyclic(neighbor, current_stack):
                        return True
                elif neighbor in current_stack:
                    return True
            
            current_stack.remove(v)
            return False
            
        for node_id in self.nodes:
            if node_id not in visited:
                if is_cyclic(node_id, rec_stack):
                    raise ValueError(f"Cycle detected involving node {self.nodes[node_id].name}")
        
        return True


class AgreementValidator:
    """Validates output against agreement rules."""
    
    @staticmethod
    def validate(output: str, rules: List[AgreementRule]) -> Dict[str, Any]:
        """
        Validate output against all rules.
        Returns dict with 'passed', 'results', and 'failed_required'.
        """
        results = {}
        failed_required = []
        
        for rule in rules:
            passed = AgreementValidator._check_rule(output, rule)
            results[rule.name] = {
                "passed": passed,
                "type": rule.type,
                "required": rule.required
            }
            if not passed and rule.required:
                failed_required.append(rule.name)
        
        return {
            "passed": len(failed_required) == 0,
            "results": results,
            "failed_required": failed_required
        }
    
    @staticmethod
    def _check_rule(output: str, rule: AgreementRule) -> bool:
        """Check a single rule."""
        output_lower = output.lower()
        
        if rule.type == "contains":
            return str(rule.value).lower() in output_lower
        elif rule.type == "not_contains":
            return str(rule.value).lower() not in output_lower
        elif rule.type == "min_words":
            return len(output.split()) >= int(rule.value)
        elif rule.type == "max_words":
            return len(output.split()) <= int(rule.value)
        elif rule.type == "regex":
            import re
            return bool(re.search(str(rule.value), output))
        elif rule.type == "json":
            import json
            try:
                # Attempt to extract JSON if it's wrapped in markers or surrounded by text
                import re
                match = re.search(r'(\{.*\})|(\[.*\])', output, re.DOTALL)
                if match:
                    json.loads(match.group(0))
                    return True
                json.loads(output)
                return True
            except:
                return False
        elif rule.type == "schema":
            import json
            import jsonschema # Note: might need to install or use simple check
            try:
                # Basic validation: check if keys exist
                import re
                match = re.search(r'(\{.*\})|(\[.*\])', output, re.DOTALL)
                target = match.group(0) if match else output
                data = json.loads(target)
                
                # If rule.value is a list of required keys
                if isinstance(rule.value, list):
                    return all(k in data for k in rule.value)
                # If it's a dict, we assume it's a simple key-value presence check or jsonschema
                if isinstance(rule.value, dict):
                    # Basic presence check for now
                    return all(k in data for k in rule.value.keys())
                return True
            except:
                return False
        
        return True  # Unknown rules pass by default


class WorkflowEngine:
    """
    Executes workflows as a DAG, respecting dependencies and agreement rules.
    """
    
    def __init__(
        self,
        on_node_status: Optional[Callable[[str, NodeStatus, Optional[str], Optional[str]], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_thought: Optional[Callable[[str, str], None]] = None, # New callback for thought stream
        on_blackboard_update: Optional[Callable[[Dict[str, Any]], None]] = None, # Global state callback
        check_intervention: Optional[Callable[[], Any]] = None,  # Async callback to check for user intervention
        on_a2ui_event: Optional[Callable[[Dict[str, Any]], None]] = None # New callback for Generative UI
    ):
        self.on_node_status = on_node_status
        self.on_log = on_log
        self.on_thought = on_thought
        self.on_blackboard_update = on_blackboard_update
        self.check_intervention = check_intervention
        self.on_a2ui_event = on_a2ui_event
        self._providers: Dict[str, Any] = {}
        self.log_file = None  # File handle for session logging
        self.blackboard: Dict[str, Any] = {}  # Global shared state (God Mode)
        self.memory_store = MemoryStore() # Long-term memory logic
        self.check_intervention = check_intervention
        self.history: List[ExecutionSnapshot] = [] # Time-Travel History
        # Registry is already initialized globally at import time above


    async def log(self, speaker: str, message: str):
        """Emit a log message asynchronously."""
        logger.info(f"[{speaker}] {message}")
        
        # Write to session log file if open using aiofiles
        if self.log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                await self.log_file.write(f"[{timestamp}] [{speaker}] {message}\n")
                await self.log_file.flush()
            except Exception as e:
                logger.error(f"Failed to write to log file: {e}")

        if self.on_log:
            # Check if on_log is a coroutine or sync function
            if asyncio.iscoroutinefunction(self.on_log):
                await self.on_log(speaker, message)
            else:
                self.on_log(speaker, message)
    
    async def emit_thought(self, speaker: str, text: str):
        """Emit a thought stream message and log it."""
        if self.log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                await self.log_file.write(f"[{timestamp}] [{speaker} (THOUGHT)] {text}\n")
                await self.log_file.flush()
            except Exception:
                pass

        if self.on_thought:
            if asyncio.iscoroutinefunction(self.on_thought):
                await self.on_thought(speaker, text)
            else:
                self.on_thought(speaker, text)
    
    async def emit_trace(self, trace_id: str, parent_id: Optional[str], node_id: str, node_name: str, status: str, inputs: Any = None, outputs: Any = None, error: str = None):
        """Emit a detailed trace packet for the execution tree."""
        if self.on_node_status:
            # We piggyback on on_node_status with a special "TRACE" status to avoid changing the signature too much,
            # OR we check if on_node_status handles a 5th arg. 
            # Better: send a structured dict as 'output' with a specific prefix/flag if we don't want to break API.
            # But the plan says emit detailed trace packets via WebSocket.
            # Let's assume on_node_status propagates to server.py::on_node_status which sends WS.
            # We can use a special status "TRACE_UPDATE" or just rely on standard updates + a new dedicated callback.
            # For strict compliance with "Transform Results tab into a nested tree", we'll emit a special payload.
            
            trace_payload = {
                "type": "trace_event",
                "trace_id": trace_id,
                "parent_id": parent_id,
                "node_id": node_id,
                "node_name": node_name,
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "inputs": inputs,
                "outputs": outputs,
                "error": error
            }
            # We send this as a JSON string in the 'output' field with a special status 'TRACE'
            # Server.py needs to handle this or frontend needs to parse it.
            # Let's use a specific status.
            self.on_node_status(node_id, "TRACE", json.dumps(trace_payload), node_name, None)

    def update_status(self, node: WorkflowNode, status: NodeStatus, output: Optional[str] = None):
        """Update node status and notify listeners."""
        if self.on_node_status:
            self.on_node_status(node.id, status, output, node.name, getattr(node, 'display_status', None))
    
    async def execute(self, workflow: Workflow, initial_input: str, resume: bool = False, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute the workflow from entry nodes to completion.
        
        Args:
            workflow: The workflow to execute
            initial_input: The initial prompt/input
            resume: If True, continue from current state (don't reset)
            context: Optional external context (e.g. session metadata, chat history)
            
        Returns:
            Dict with execution results
        """
        await self.log("System", f"🚀 {'Resuming' if resume else 'Starting'} workflow: {workflow.name}")
        self.current_workflow = workflow
        
        # Attach context to workflow
        workflow.context = context or {}
        
        # Create session output folder with timestamp and UUID
        from pathlib import Path
        from datetime import datetime
        import uuid
        
        if not resume:
            session_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            workflow_slug = workflow.name.replace(' ', '_').lower()[:30]
            session_folder = Path("exports") / workflow_slug / f"{timestamp}_{session_id}"
            session_folder.mkdir(parents=True, exist_ok=True)
            
            # Store session info in workflow metadata for nodes to use
            workflow.session_folder = str(session_folder)
            workflow.session_id = session_id

        # ============ Initialize Summary Memory ============
        if not workflow.memory:
            from core.memory import SummaryBufferMemory
            workflow.memory = SummaryBufferMemory(provider=await self._get_provider(list(workflow.nodes.values())[0]) if workflow.nodes else None)
            
            # Load session history if available in context
            if context and "session_history" in context:
                for msg in context["session_history"]:
                    workflow.memory.add_message(msg.get("role", "user"), msg.get("content", ""))
        
        # Log session start
        if not resume:
            await self.log("System", f"📂 Session Data: {workflow.session_folder}")
            
            # Initialize log file using aiofiles
            try:
                log_path = session_folder / "workflow_execution.log"
                self.log_file = await aiofiles.open(log_path, "a", encoding="utf-8")
                await self.log("System", f"📁 Session logging started: {log_path}")
            except Exception as e:
                logger.error(f"Failed to open log file: {e}")
                
            await self.log("System", f"📁 Session folder: {session_folder}")
        
        # Reset all node states ONLY if not resuming
        if not resume:
            for node in workflow.nodes.values():
                node.status = NodeStatus.IDLE
                node.output = None
                node.error = None
        
        # Track execution
        completed: Set[str] = {n.id for n in workflow.nodes.values() if n.status == NodeStatus.COMPLETE}
        # Pre-load outputs from existing nodes
        outputs: Dict[str, str] = {"__input__": initial_input}
        for n in workflow.nodes.values():
             if n.output:
                 outputs[n.id] = n.output

        # If resuming, find nodes that were waiting or queued
        queue = []
        if resume:
             # Add nodes that were waiting/paused, or whose parents are complete but they are idle
             for nid, node in workflow.nodes.items():
                 if node.status == NodeStatus.WAITING_FOR_APPROVAL:
                     # If we are resuming, we keep it in queue to re-check intervention
                     queue.append(nid)
                 elif node.status == NodeStatus.IDLE:
                     # Check if parents complete
                     preds = workflow.get_predecessors(nid)
                     if preds and all(p in completed for p in preds):
                         queue.append(nid)
        
        if not queue:
             # Get entry nodes if no explicit resume queue (or fresh start)
             if not resume:
                 entry_nodes = workflow.get_entry_nodes()
                 queue = list(entry_nodes)
             else:
                 # If resuming but queue empty, maybe we just approved a node?
                 # Find nodes that are COMPLETE but have IDLE successors
                 for nid in completed:
                     for succ in workflow.get_successors(nid):
                          if workflow.nodes[succ].status == NodeStatus.IDLE and succ not in queue:
                               queue.append(succ)
 
        # Track nodes we've already logged as waiting in this "stall" period
        logged_waiting = set()
        
        while queue:
            # If we've cycled through the whole queue and nobody can run, sleep
            queue_size = len(queue)
            progress_made = False

            for _ in range(queue_size):
                if not queue: break
                node_id = queue.pop(0)
                
                node = workflow.nodes.get(node_id)
                if not node:
                    continue
                
                # Check for recycling (looping)
                if node.status == NodeStatus.COMPLETE:
                    if node.iteration_count < node.max_iterations:
                        # Recycle the node
                        await self.log(node.name, f"🔄 Recycling node (Iteration {node.iteration_count + 1}/{node.max_iterations})")
                        node.status = NodeStatus.IDLE
                        node.output = None
                        # We don't continue here, we let it fall through to predecessor check
                        # But wait, if it's IDLE now, it might need inputs again.
                        # If inputs come from predecessors in the loop, they might be ready.
                    else:
                        # Max iterations reached, skip
                        await self.log(node.name, f"⚠️ Max iterations ({node.max_iterations}) reached. Stopping loop.")
                        continue

                # Check if predecessors are complete
                # Predecessor Check (Robust Feedback Filtering)
                # Find all edges targeting this node that are NOT feedback edges
                blocking_edges = [
                    e for e in workflow.edges 
                    if e.target_id == node_id and not e.feedback
                ]
                required_predecessors = {e.source_id for e in blocking_edges}
                
                # Check if all REQUIRED predecessors are completed
                if not all(p in completed for p in required_predecessors):
                    # Identify missing predecessors for logging
                    missing = [p for p in required_predecessors if p not in completed]
                    
                    # Only log waiting status periodically to reduce spam
                    if node_id not in logged_waiting:
                        edge_info = []
                        for e in workflow.edges:
                            if e.target_id == node_id:
                                fb_status = f"(fb={e.feedback})"
                                edge_info.append(f"{e.source_id}->{e.target_id} {fb_status}")
                        
                        await self.log("System", f"⏳ Node {node_id} waiting for: {missing}. (Edges: {edge_info})")
                        logged_waiting.add(node_id)
                    
                    queue.append(node_id) # Keep in queue
                    continue
                
                # For context building, we still want ALL predecessors that have output
                # regardless of whether they were "blocking" or not.
                predecessors = [e.source_id for e in workflow.edges if e.target_id == node_id]

                # NEW: Check for existing WAITING_FOR_APPROVAL status
                if node.status == NodeStatus.WAITING_FOR_APPROVAL:
                    if self.check_intervention:
                        intervention = await self.check_intervention(node_id)
                        if intervention:
                             await self.log("System", f"DEBUG: {node.name} picked up intervention: {intervention}")
                        else:
                             # Important: Sleep to avoid CPU pegging and log spam
                             await asyncio.sleep(1)
                        if intervention == "APPROVE":
                            await self.log(node.name, "✅ User APPROVED output")
                            node.status = NodeStatus.COMPLETE
                            completed.add(node_id)
                            progress_made = True
                            # Queue successors
                            for succ in workflow.get_successors(node_id):
                                if succ not in completed and succ not in queue:
                                    queue.append(succ)
                            continue
                        elif intervention == "REJECT":
                            await self.log(node.name, "❌ User REJECTED output")
                            node.status = NodeStatus.FAILED
                            continue
                    
                    queue.append(node_id) # Keep in queue
                    continue
                
                # If we get here, the node is starting! Clear waiting log for next time
                if node_id in logged_waiting:
                    logged_waiting.remove(node_id)
                progress_made = True
                
                # Build context from predecessor outputs
                context_parts = []
                story_history = []
                for nid, out in outputs.items():
                    if nid == "__input__" or nid not in workflow.nodes:
                        continue
                    n = workflow.nodes[nid]
                    if n.type in [NodeType.DIRECTOR, NodeType.CHARACTER, NodeType.AUDITOR] and nid in completed:
                        story_history.append(f"[{n.name}]: {out}")
                
                if story_history:
                     context_parts.append("=== SHARED STORY HISTORY ===\n" + "\n\n".join(story_history[-5:]) + "\n==============================") 

                for p in predecessors:
                    raw_output = outputs.get(p, "")
                    # No need to strip here anymore as outputs are cleaned in _execute_node
                    context_parts.append(f"[{workflow.nodes[p].name}]: {raw_output}")
                
                context = "\n\n".join(context_parts) if predecessors else outputs.get("__input__", "")
                
                await self.log("System", f"🚀 {node.name} starting. (Inputs from: {predecessors}, Context: {len(context)} chars)")

                # Execute node
                try:
                    # Inject Tool Hint for project modification & analysis
                    fs_tools = """
You can interact with the file system and execute commands using these tags:
- <write_file path="path/to/file">content</write_file>
- <read_file path="path/to/file"/>
- <list_dir path="path/to/dir"/>
- <run_command command="your command here"/>
- <set_state key="name" value="any_value"/>  # Write to shared blackboard
- <get_state key="name"/>  # Read from shared blackboard
"""
                    net_tools = """
- <browser_open url="..."/>
- <dns_lookup domain="..."/>
- <http_get url="..."/>
""" if node.internet_access else ""
                    
                    # Inject blackboard contents into the persona if it's not empty
                    blackboard_hint = ""
                    if self.blackboard:
                        blackboard_hint = f"\n[CURRENT GLOBAL STATE]:\n{json.dumps(self.blackboard, indent=2)}\n"

                    tool_hint = f"""
[SYSTEM POWER: You have AGENTIC CONTROL over the local environment.]
{fs_tools}
{net_tools}
{blackboard_hint}
Security: { "FULL INTERNET ACCESS ENABLED." if node.internet_access else "Offline mode. Operations scoped to project directory." }
Power Level: FULL AUTONOMY.
[RECOVERY]: If you encounter an error in previous outputs or state, you can output <request_repair node_id="..."/> to trigger an autonomous fix.
"""
                    # Dynamic Scaling: If task is complex and Tier is Paid, upgrade model
                    model_override = node.model
                    if node.tier == "paid":
                        # Simple complexity check: word count > 1000 or specific keywords
                        if len(context) > 2000 or any(kw in context.lower() for kw in ["refactor", "architect", "database", "security audit"]):
                             # Suggest a high-weight model if on Ollama, otherwise keep default
                             if node.provider == "ollama" and node.model in ["llama3", "mistral"]:
                                 model_override = "kimi-k2.5" # Deep thinking model
                                 await self.log(node.name, "🚀 [OPTIMIZER] High complexity detected. Scaling to High-Weight model (Kimi k2.5).")
                             elif node.provider == "google_ai":
                                 model_override = "gemini-1.5-pro"
                                 await self.log(node.name, "🚀 [OPTIMIZER] High complexity detected. Scaling to Gemini 1.5 Pro.")
                    
                    # Backstory Injection
                    base_persona = node.persona if node.persona else ""
                    if node.backstory:
                        base_persona = f"{base_persona}\n\n[BACKSTORY/CONTEXT]:\n{node.backstory}"

                    node_persona = base_persona + tool_hint
                    
                    # Store original model to restore later if needed, but for now we just pass override
                    original_model = node.model
                    node.model = model_override
                    
                    # Create Trace ID for this execution
                    trace_id = str(uuid.uuid4())
                    
                    # Emit START trace
                    await self.emit_trace(trace_id, None, node_id, node.name, "STARTED", inputs={"context_len": len(context), "input_preview": context[:50]})

                    result = await self._execute_node(node, initial_input, context, persona_override=node_persona)
                    
                    # Emit END trace
                    await self.emit_trace(
                        trace_id, None, node_id, node.name, 
                        "COMPLETED" if result["success"] else "FAILED", 
                        outputs=result.get("output"), 
                        error=result.get("error")
                    )

                    # Usage Tracking & Emitting
                    if result["success"]:
                        usage = self._calculate_usage(context, result.get("output", ""))
                        usage_json = json.dumps(usage)
                        await self.emit_thought(node.name, f"<<<USAGE: {usage_json}>>>")

                    # Restore original model for future iterations
                    node.model = original_model

                    
                    if result["success"]:
                        if node.requires_approval:
                             node.status = NodeStatus.WAITING_FOR_APPROVAL
                             node.output = result["output"]
                             outputs[node_id] = result["output"]
                             await self.log(node.name, "⏸️ Waiting for user approval")
                             queue.append(node_id)
                             continue

                        node.status = NodeStatus.COMPLETE
                        node.output = result["output"]
                        outputs[node_id] = result["output"]
                        
                        if node.agreement_rules:
                            validation = AgreementValidator.validate(node.output, node.agreement_rules)
                            if not validation["passed"]:
                                await self.log(node.name, f"⚠️ Agreement validation failed")
                    else:
                        node.status = NodeStatus.FAILED
                        node.error = result.get("error", "Unknown error")
                        
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    node.status = NodeStatus.FAILED
                    node.error = str(e)
                    logger.error(f"Node {node_id} error: {e}")
                
                self.update_status(node, node.status, node.output)
                completed.add(node_id)
                
                # [DYNAMIC DISPATCH HANDLING]
                if result["success"] and result.get("output"):
                    dispatch_instructions = await self._process_dispatch_tags(result["output"], node_id)
                    for instr in dispatch_instructions:
                        if instr["type"] == "sleep":
                            # Simple sleep handling
                            duration = instr["duration"]
                            seconds = 0
                            if "s" in duration: seconds = int(duration.replace("s", ""))
                            elif "m" in duration: seconds = int(duration.replace("m", "")) * 60
                            elif "h" in duration: seconds = int(duration.replace("h", "")) * 3600
                            else: seconds = int(duration) # assume seconds
                            
                            await self.log("System", f"😴 Synchronization Sleep: {seconds}s requested by {node.name}")
                            await asyncio.sleep(seconds)
                            
                        elif instr["type"] == "dispatch":
                            target_name = instr["target"]
                            dispatch_input = instr["input"]
                            
                            # Find node by Name or ID
                            target_node = next((n for n in workflow.nodes.values() if n.name == target_name or n.id == target_name), None)
                            
                            if target_node:
                                await self.log("System", f"⚡ DISPATCHING {node.name} -> {target_node.name}")
                                
                                # 1. Reset Status
                                target_node.status = NodeStatus.IDLE
                                if target_node.id in completed:
                                    completed.remove(target_node.id)
                                
                                # 2. Inject Input (Update context or inputs dict)
                                # We treat this as a direct input override
                                outputs[target_node.id] = dispatch_input # Pretend previous run had this output? No.
                                # Better: Check if target expects "task" or "instruction"
                                context += f"\n\n[PRIORITY DISPATCH from {node.name}]: {dispatch_input}"
                                
                                # Store specific dispatch message in blackboard so it's picked up by _execute_node logic
                                # or easier: just allow the loop to pick it up. 
                                # BUT we need to make sure the target node receives this input.
                                # We can inject it into 'outputs' with a special key
                                outputs[f"__dispatch_{target_node.id}__"] = dispatch_input

                                # 3. Queue it
                                if target_node.id not in queue:
                                    queue.append(target_node.id)
                                    progress_made = True
                            else:
                                await self.log("System", f"❌ Dispatch Failed: Target '{target_name}' not found")

                # Queue successors with conditional edge routing (ONLY if node succeeded)
                output_lower = (node.output or "").lower() if node.output else ""
                
                # Determine which edges to activate based on node type and output
                if node.status == NodeStatus.COMPLETE:
                    for edge in workflow.edges:
                        if edge.source_id != node_id:
                            continue
                        
                        target_id = edge.target_id
                        if target_id in completed or target_id in queue:
                            continue
                    
                        # Auditor/Validator conditional routing
                        if node.type in [NodeType.AUDITOR, "auditor"] and edge.feedback:
                            # Feedback edge: only activate if output indicates failure
                            if any(pattern in output_lower for pattern in [
                                "incomplete", "code_incomplete", "gdd_incomplete",
                                "needs_rework", "rejected", "failed validation",
                                "placeholder detected", "not valid"
                            ]):
                                await self.log("System", f"🔄 VALIDATOR REJECTED: {node.name} → triggering feedback to {target_id}")
                                queue.append(target_id)
                        elif node.type in [NodeType.AUDITOR, "auditor"] and not edge.feedback:
                            # Forward edge: only activate if output indicates success
                            if any(pattern in output_lower for pattern in [
                                "validated", "valid", "approved", "complete", "ready",
                                "gold_standard", "acceptable", "passed"
                            ]):
                                await self.log("System", f"✅ VALIDATOR APPROVED: {node.name} → proceeding to {target_id}")
                                queue.append(target_id)
                        else:
                            # Non-auditor nodes: queue all successors (existing behavior)
                            queue.append(target_id)


                # [TIME-TRAVEL] Capture Snapshot
                snapshot = ExecutionSnapshot(
                    step_index=len(self.history),
                    node_id=node_id,
                    blackboard=self.blackboard.copy(), # Deep copy if needed, but dict.copy() is shallow. For simple types ok.
                    outputs=outputs.copy(),
                    logs=[] # fetching logs is complex, skipping for now or need a way to get recent logs
                )
                self.history.append(snapshot)


            # End of for pass - check progress
            if progress_made:
                logged_waiting.clear()
            elif queue:
                # No progress made in a full pass, sleep to yield control
                await asyncio.sleep(0.5)
        
        # Determine overall success
        all_complete = all(n.status == NodeStatus.COMPLETE for n in workflow.nodes.values())
        
        await self.log("System", "✅ Workflow complete" if all_complete else "⚠️ Workflow completed with issues")
        
        # Close log file
        if self.log_file:
            try:
                await self.log_file.close()
                self.log_file = None
            except Exception:
                pass
        
        return {
            "success": all_complete,
            "outputs": outputs,
            "blackboard": self.blackboard,
            "nodes": {nid: {"status": n.status, "output": n.output, "error": n.error} for nid, n in workflow.nodes.items()}
        }

    async def replay_from(self, step_index: int) -> Dict[str, Any]:
        """
        Time-Travel: Restore state from a snapshot and resume execution.
        """
        if step_index < 0 or step_index >= len(self.history):
            raise ValueError(f"Invalid step index: {step_index}")
            
        snapshot = self.history[step_index]
        await self.log("System", f"⏪ Time-Travel: Replaying from step {step_index} (Node: {snapshot.node_id})")
        
        # 1. Restore State
        self.blackboard = snapshot.blackboard.copy()
        outputs = snapshot.outputs.copy()
        
        # 2. Reset Nodes
        # We need to find which nodes were complete AT that time.
        # Simple heuristic: The snapshot was taken AFTER 'node_id' completed.
        # So 'node_id' and its predecessors (in the snapshot outputs) are complete.
        # Future nodes should be IDLE.
        
        restored_outputs_ids = set(outputs.keys())
        for nid, node in self.current_workflow.nodes.items():
            if nid in restored_outputs_ids and nid != "__input__":
                node.status = NodeStatus.COMPLETE
                node.output = outputs[nid]
            elif nid == "__input__":
                pass
            else:
                 node.status = NodeStatus.IDLE
                 node.output = None
                 node.error = None
        
        # 3. Resume Execution
        # We call execute with resume=True. 
        # But we need to ensure 'outputs' passed to execute matches our restored state?
        # execute() logic re-builds 'outputs' from nodes. So setting node.output is sufficient.
        
        # However, we might want to re-run the node at step_index?
        # A "Replay" usually means "Go back to before this happened" or "Go back to this state".
        # If snapshot is AFTER node execution, then restoring it means that node is DONE.
        # If user wants to RETRY a node, they should go to the snapshot BEFORE it.
        # Let's assume step_index refers to "After step N".
        # If user wants to re-run node X, they load state from Step N-1.
        
        return await self.execute(self.current_workflow, outputs.get("__input__", ""), resume=True)

    async def inject_feedback(self, node_id: str, feedback: str):
        """Inject user feedback into a running workflow."""
        key = f"{node_id}_feedback"
        # Append if exists?
        current = self.blackboard.get(key, "")
        if current:
            self.blackboard[key] = current + "\n" + feedback
        else:
            self.blackboard[key] = feedback
            
        await self.log("System", f"🗣️ User Intervention on {node_id}: {feedback}")
        return True

    
    def _process_blackboard_tags(self, text: str) -> str:
        """Parse <set_state> and <get_state> tags and update blackboard."""
        import re
        
        # 1. Process <set_state key="..." value="..."/> or <set_state key="...">value</set_state>
        # Pattern for short form: <set_state key="k" value="v"/>
        short_pattern = r'<set_state\s+key=["\']([^"\']+)["\']\s+value=["\']([^"\']+)["\']\s*/>'
        for key, value in re.findall(short_pattern, text):
            self.blackboard[key] = value
            logger.info(f"Blackboard SET (short): {key} = {value}")
            
        # Pattern for long form: <set_state key="k">v</set_state>
        long_pattern = r'<set_state\s+key=["\']([^"\']+)["\']\s*>(.*?)</set_state>'
        for key, value in re.findall(long_pattern, text, re.DOTALL):
            self.blackboard[key] = value.strip()
            logger.info(f"Blackboard SET (long): {key} = {value[:20]}...")

        if self.on_blackboard_update and (re.search(short_pattern, text) or re.search(long_pattern, text)):
            self.on_blackboard_update(self.blackboard)
        
        return text

    async def _execute_node(self, node: WorkflowNode, input_text: str, context: str, persona_override: str = None) -> Dict[str, Any]:
        """Execute a single node."""
        
        # 1. Traffic Control
        # Determine Priority
        priority = Priority.STANDARD
        if node.type in [NodeType.DIRECTOR, NodeType.SYSTEM]:
            priority = Priority.VIP
        elif node.type in [NodeType.CRITIC, NodeType.AUDITOR]:
            priority = Priority.BULK
            
        await self.log(node.name, f"🚦 Waiting for execution slot... (Priority: {priority.name})")
        await global_traffic_controller.acquire_slot(node.name, priority)

        try:
            await self.log(node.name, f"⚙️ Processing...")
            self.update_status(node, NodeStatus.RUNNING)
            node.status = NodeStatus.RUNNING
            
            output = ""
            success = True
    
            # Process standard node execution...
            # CHECK FOR INTERVENTION
            feedback_key = f"{node.id}_feedback"
            if feedback_key in self.blackboard:
                feedback = self.blackboard[feedback_key]
                # Append to context effectively
                context += f"\\n\\n[USER INTERVENTION/FEEDBACK]: {feedback}\\n(You must prioritize this instruction over previous ones.)"
                await self.log(node.name, f"⚠️ Applying User Feedback: {feedback[:50]}...")
                
            result = await self.__inner_execute_node(node, input_text, context, persona_override)
        
            if result["success"]:
                output = result["output"]
                # INTERCEPT: Process Blackboard tags from the output
                if isinstance(output, str):
                    self._process_blackboard_tags(output)
                    # Broadcast blackboard update to UI
                    if self.on_node_status:
                        # We reuse on_node_status to send a special 'blackboard_update' signal
                        # This part was cut off in previous edit, need to ensure it's valid
                        pass 

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
             await global_traffic_controller.release_slot()
             
        return result



    async def __inner_execute_node(self, node: WorkflowNode, input_text: str, context: str, persona_override: str = None) -> Dict[str, Any]:
        """Internal execution logic."""
        output = ""
        success = True
        error = None

        if node.type == NodeType.OUTPUT:
            output = context if context else input_text
            if not output:
                output = "No Content"
            
            # Use the node's save_path explicitly for OUTPUT nodes
            save_target = node.save_path
            if save_target:
                try:
                    target_path = os.path.abspath(save_target)
                    # If it's a directory, generate a filename
                    if save_target.endswith('/') or save_target.endswith('\\') or os.path.isdir(target_path):
                        os.makedirs(target_path, exist_ok=True)
                        filename = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                        target_path = os.path.join(target_path, filename)
                    else:
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    async with aiofiles.open(target_path, 'w', encoding='utf-8') as f:
                        await f.write(output)
                    await self.log(node.name, f"💾 Saved to {target_path}")
                    return {"success": True, "output": output}
                except Exception as e:
                    await self.log(node.name, f"❌ Save error: {e}")
                    return {"success": False, "error": f"Failed to save: {e}"}
            else:
                await self.log(node.name, "⚠️ No save_path configured for OUTPUT node")
                return {"success": True, "output": output}
        
        elif node.type == NodeType.INPUT:
            # Input nodes just return the original mission prompt
            output = input_text
            await self.log(node.name, "📥 Received initial input")
            return {"success": True, "output": output}

        # ============ SUB-WORKFLOW EXECUTION ============
        elif node.sub_workflows:
            await self.log(node.name, f"🔗 Executing {len(node.sub_workflows)} attached sub-workflow(s)")
            aggregate_outputs = []
            for i, sw_config in enumerate(node.sub_workflows):
                try:
                    from core.models import Workflow
                    if sw_config.get("content"):
                        wf_data = json.loads(sw_config["content"]) if isinstance(sw_config["content"], str) else sw_config["content"]
                    elif sw_config.get("path"):
                        target_path = os.path.normpath(os.path.join(os.getcwd(), sw_config["path"]))
                        async with aiofiles.open(target_path, "r", encoding="utf-8") as f:
                            wf_data = json.loads(await f.read())
                    else: continue
                    sub_workflow = Workflow(**wf_data)
                    async def bl(s, m): await self.log(f"{node.name}/{s}", m) if node.return_event_bubble else None
                    def bt(s, t): self.on_thought(node.name, f"**[{s}]**: {t}") if node.return_event_bubble and self.on_thought else None
                    def bs(nid, s, o, n, cds=None): 
                        if s == NodeStatus.RUNNING:
                            node.display_status = f"Running {i+1}/{len(node.sub_workflows)}: {n}"
                            self.update_status(node, NodeStatus.RUNNING)
                    child_engine = WorkflowEngine(on_log=bl, on_thought=bt, on_node_status=bs, check_intervention=self.check_intervention)
                    result = await child_engine.execute(sub_workflow, initial_input=context if context else input_text)
                    if result["success"]:
                        out_nodes = [n for n in sub_workflow.nodes.values() if n.type == NodeType.OUTPUT and n.output]
                        aggregate_outputs.append("\n\n".join([n.output for n in out_nodes]) if out_nodes else "Complete")
                    else: return {"success": False, "error": f"Sub-workflow {i+1} failed"}
                except Exception as e: return {"success": False, "error": f"Sub-workflow {i+1} Err: {e}"}
            output = "\n\n--- Sub-Workflow Outputs ---\n\n" + "\n\n".join(aggregate_outputs)
            await self.log(node.name, f"✅ Sub-workflow execution complete")
            return {"success": True, "output": output}

        # ============ REGISTRY / MODULAR EXECUTION ============
        else:
            executor_class = NodeRegistry.get_executor(node.type)
            if executor_class:
                # Custom injection for Factory nodes
                if node.type in [NodeType.ARCHITECT, NodeType.CRITIC]:
                    from core.factory.optimizer import FactoryOptimizer
                    trace_context = {
                        "nodes": {nid: {"name": n.name, "status": n.status, "output": n.output} for nid, n in self.current_workflow.nodes.items()},
                        "edges": [e.model_dump() for e in self.current_workflow.edges]
                    }
                    optimizer = FactoryOptimizer(node.type, self.blackboard, trace_context)
                    persona_override = optimizer.render()

                # Execution Context
                exec_context = {"engine": self, "node": node, "context_str": context, "persona_override": persona_override}
                
                config = node.provider_config or {}
                if node.type == NodeType.MEMORY:
                    config = getattr(node, 'memory_config', {}) or config
                
                node_inputs = node.inputs or {}
                if "text" not in node_inputs: node_inputs["text"] = input_text
                if "query" not in node_inputs: node_inputs["query"] = input_text

                executor = executor_class(node_id=node.id, config=config)
                result = await executor.execute(node_inputs, context=exec_context)
                
                if result.get("ok"):
                    output = result.get("output", "")
                    if result.get("ui_event") == "a2ui_update" and self.on_a2ui_event:
                        self.on_a2ui_event({"node_id": node.id, "node_name": node.name, "schema": result.get("data")})
                    
                    if node.save_enabled:
                        try:
                            from pathlib import Path
                            session_folder = getattr(self.current_workflow, 'session_folder', None)
                            save_file = Path(session_folder) / f"{node.name.replace(' ', '_').lower()}_output.md" if session_folder else Path(node.save_path) if node.save_path else None
                            if save_file:
                                save_file.parent.mkdir(parents=True, exist_ok=True)
                                async with aiofiles.open(save_file, 'w', encoding='utf-8') as f: await f.write(output)
                        except Exception: pass
                    return {"success": True, "output": output}
                else: return {"success": False, "error": result.get("error")}

            # ============ FINAL FALLBACK (AGENT) ============
            else:
                from core.nodes.agent_node import AgentNode
                executor = AgentNode(node_id=node.id, config=node.provider_config or {})
                res = await executor.execute({"text": input_text}, context={"engine": self, "node": node, "context_str": context, "persona_override": persona_override})
                return {"success": res.get("ok", False), "output": res.get("output"), "error": res.get("error")}

    def _process_blackboard_tags(self, text: str):
        """Extract <set_state> tags and update blackboard."""
        import re
        if not text:
            return

        # Short form: <set_state key="foo" value="bar"/>
        short_pattern = re.finditer(r'<set_state\s+key=["\'](.*?)["\']\s+value=["\'](.*?)["\']\s*/>', text)
        updated = False
        
        for match in short_pattern:
            key = match.group(1)
            value = match.group(2)
            self.blackboard[key] = value
            updated = True
            logger.info(f"Blackboard SET (short): {key} = {value}")

        # Long form: <set_state key="foo">bar</set_state>
        long_pattern = re.finditer(r'<set_state\s+key=["\'](.*?)["\']>(.*?)</set_state>', text, re.DOTALL)
        for match in long_pattern:
            key = match.group(1)
            value = match.group(2).strip()
            self.blackboard[key] = value
            updated = True
            logger.info(f"Blackboard SET (long): {key} = {value[:20]}...")


        if updated and self.on_blackboard_update:
            self.on_blackboard_update(self.blackboard)
    
    async def _process_dispatch_tags(self, text: str, current_node_id: str) -> List[Dict[str, Any]]:
        """
        Parse <dispatch_task> and <sleep> tags.
        Returns a list of dispatch instructions.
        """
        if not text:
            return []
            
        import re
        instructions = []
        
        # 1. Parse <dispatch_task node="..." input="...">...</dispatch_task>
        # Supports both attribute 'input' and tag content
        dispatch_pattern = re.finditer(r'<dispatch_task\s+node=["\'](.*?)["\'](?:\s+input=["\'](.*?)["\'])?>(.*?)</dispatch_task>', text, re.DOTALL)
        
        for match in dispatch_pattern:
            target_node_name = match.group(1)
            input_attr = match.group(2) or ""
            content = match.group(3).strip()
            
            final_input = input_attr
            if content:
                final_input = content if not input_attr else f"{input_attr}\n{content}"
            
            instructions.append({
                "type": "dispatch",
                "target": target_node_name,
                "input": final_input,
                "source": current_node_id
            })
            await self.log("System", f"Caught Dynamic Dispatch: {current_node_id} -> {target_node_name}")

        # 2. Parse <sleep duration="..."/>
        sleep_pattern = re.finditer(r'<sleep\s+duration=["\'](.*?)["\']\s*/>', text)
        for match in sleep_pattern:
            duration_str = match.group(1)
            instructions.append({
                "type": "sleep",
                "duration": duration_str
            })
            
        return instructions

    


    async def _get_provider(self, node: WorkflowNode):
        """Get or create a provider instance for the node."""
        
        # Smart Tier Selection Logic
        effective_model = node.model
        tier_data = node.tier_config or {}
        tier = tier_data.get("tier", "paid")
        
        if tier == "free":
            if "gemini" in node.provider.lower() and "flash" not in node.model.lower():
                effective_model = "gemini-1.5-flash"
                await self.log(node.name, f"💰 Tier Optimization: switched to {effective_model}")
            elif "openai" in node.provider.lower() and ("4" in node.model or "o1" in node.model):
                effective_model = "gpt-4o-mini"
                await self.log(node.name, f"💰 Tier Optimization: switched to {effective_model}")
        
        provider_key = f"{node.provider}:{effective_model}"
        
        if provider_key not in self._providers:
            try:
                from providers import ProviderRegistry, _register_providers
                _register_providers()
                
                # Try to get config from ConfigManager if available
                config = {}
                try:
                    from core.config_manager import ProviderConfigManager
                    cm = ProviderConfigManager()
                    # Check for provider by ID or type
                    p_config = cm.get_provider(node.provider)
                    if p_config:
                        config.update(p_config.config)
                    else:
                        # Fallback to defaults or node-specific config
                        config.update(node.provider_config)
                except Exception:
                    config.update(node.provider_config)

                config["model"] = effective_model
                
                # Special handling for OpenCode WSL path (default if not configured)
                if node.provider == "opencode" and "cli_command" not in config:
                    # Provide a sane default or informative error
                    pass 
                
                provider = ProviderRegistry.create(node.provider, config)
                await provider.initialize()
                self._providers[provider_key] = provider
                
            except Exception as e:
                logger.error(f"Failed to create provider {node.provider}: {e}")
                return None
        
        return self._providers.get(provider_key)

    async def _get_provider_by_type(self, provider_type: str, model: str):
        """Get or create a provider instance by type and model for failover support.

        This method is used by the FailoverManager to dynamically switch to
        fallback providers when the primary provider fails (rate limits, timeouts, etc.)

        Args:
            provider_type: The provider type/id (e.g., 'groq', 'ollama', 'claude_code', 'google_ai')
            model: The model to use with this provider

        Returns:
            Configured provider instance or None if creation fails
        """
        provider_key = f"{provider_type}:{model}"

        if provider_key not in self._providers:
            try:
                from providers import ProviderRegistry, _register_providers
                _register_providers()

                # Try to get config from ConfigManager if available
                config = {}
                try:
                    from core.config_manager import ProviderConfigManager
                    cm = ProviderConfigManager()
                    p_config = cm.get_provider(provider_type)
                    if p_config:
                        config.update(p_config.config)
                except Exception:
                    pass  # Use default config if ConfigManager fails

                config["model"] = model

                provider = ProviderRegistry.create(provider_type, config)
                await provider.initialize()
                self._providers[provider_key] = provider

                await self.log("System", f"Failover: Created provider {provider_type}/{model}")

            except Exception as e:
                logger.error(f"Failed to create failover provider {provider_type}/{model}: {e}")
                return None

        return self._providers.get(provider_key)

    def _calculate_usage(self, input_text: str, output_text: str) -> Dict[str, int]:
        """Estimate token usage (rough approximation: 4 chars / token)."""
        return {
            "input_tokens": len(input_text) // 4,
            "output_tokens": len(output_text) // 4,
            "total_tokens": (len(input_text) + len(output_text)) // 4
        }

    def _strip_thinking(self, text: Optional[str], node_name: str = "Unknown") -> str:
        """Remove <think>...</think> blocks from text and emit them."""
        if not text:
            return ""
        import re
        
        # Regex to capture thoughts
        thought_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL | re.IGNORECASE)
        
        # Extract thoughts and emit
        thoughts = thought_pattern.findall(text)
        for thought in thoughts:
            t_content = thought.strip()
            if t_content and self.on_thought:
                logger.debug(f"Engine extracting and emitting thought from {node_name}: {len(t_content)} chars")
                self.on_thought(node_name, t_content)
            
        # Remove thoughts from final output
        # Re-using the pattern to ensure we catch all variations (case-insensitive)
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
        return cleaned_text
