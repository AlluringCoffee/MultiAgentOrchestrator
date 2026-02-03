import logging
from typing import Dict, Any, Type, Optional

logger = logging.getLogger(__name__)

class NodeRegistry:
    """
    Central registry for node executors.
    Supports dynamic registration of new node types.
    """
    _registry: Dict[str, Type] = {}

    @classmethod
    def register(cls, node_type: str, executor_class: Type):
        """Register a new node type with its executor class."""
        cls._registry[node_type] = executor_class
        logger.info(f"Registered node type: {node_type} -> {executor_class.__name__}")

    @classmethod
    def get_executor(cls, node_type: str) -> Optional[Type]:
        """Get the executor class for a node type."""
        return cls._registry.get(node_type)

    @classmethod
    def list_types(cls) -> list:
        """List all registered node types."""
        return list(cls._registry.keys())

def initialize_default_registry():
    """Register all built-in node types."""
    from core.nodes.system_nodes import BrowserNode, ShellNode, SystemNode
    from core.nodes.memory_node import MemoryNode
    from core.nodes.http_node import HttpNode
    from core.nodes.agent_node import AgentNode
    from core.nodes.script_node import ScriptNode
    from core.nodes.github_node import GithubNode
    from core.nodes.huggingface_node import HuggingfaceNode
    from core.nodes.discovery_node import DiscoveryNode
    from core.nodes.rag_node_modular import RagNode
    from core.nodes.ui_nodes import A2UINode
    from core.nodes.mcp_node import MCPNode
    from core.nodes.notion_node import NotionNode
    from core.nodes.google_node import GoogleNode
    from core.nodes.comfy_node import ComfyNode
    from core.nodes.trigger_nodes import TelegramTrigger, DiscordTrigger
    from core.nodes.openapi_node import OpenAPINodeExecutor
    from core.nodes.optimizer_node import OptimizerNode
    
    NodeRegistry.register("browser", BrowserNode)
    NodeRegistry.register("shell", ShellNode)
    NodeRegistry.register("system", SystemNode)
    NodeRegistry.register("memory", MemoryNode)
    NodeRegistry.register("http", HttpNode)
    NodeRegistry.register("script", ScriptNode)
    NodeRegistry.register("github", GithubNode)
    NodeRegistry.register("huggingface", HuggingfaceNode)
    NodeRegistry.register("discovery", DiscoveryNode)
    NodeRegistry.register("rag", RagNode)
    NodeRegistry.register("a2ui", A2UINode)
    NodeRegistry.register("mcp", MCPNode)
    NodeRegistry.register("notion", NotionNode)
    NodeRegistry.register("google", GoogleNode)
    NodeRegistry.register("comfy", ComfyNode)
    NodeRegistry.register("telegram_trigger", TelegramTrigger)
    NodeRegistry.register("discord_trigger", DiscordTrigger)
    NodeRegistry.register("openapi", OpenAPINodeExecutor)
    NodeRegistry.register("optimizer", OptimizerNode)
    
    # Standard LLM nodes use AgentNode
    for t in ["agent", "auditor", "router", "character", "director", "optimizer", "architect", "critic"]:
        NodeRegistry.register(t, AgentNode)
