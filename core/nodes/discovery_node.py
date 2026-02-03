import os
import shutil
import logging
import importlib
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DiscoveryNode:
    """
    Electronic Merchant for capabilities.
    Search and install new node types from the ./library/ repository.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.library_path = config.get("library_path", "./library")
        self.target_path = config.get("target_path", "./core/nodes")

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        engine = context.get('engine')
        action = inputs.get("action", "list") # list, info, install
        query = inputs.get("query", "").lower()

        if action == "list":
            return await self._list_available(query)
        elif action == "install":
            return await self._install_node(query, engine)
        
        return {"ok": False, "error": f"Unknown discovery action: {action}"}

    async def _list_available(self, query: str) -> Dict[str, Any]:
        if not os.path.exists(self.library_path):
            os.makedirs(self.library_path, exist_ok=True)
            return {"ok": True, "output": "Library is empty.", "data": {"available": []}}

        available = []
        for f in os.listdir(self.library_path):
            if f.endswith(".py") and query in f.lower():
                node_name = f.replace(".py", "")
                available.append(node_name)
        
        if not available:
            return {"ok": True, "output": f"No nodes found matching '{query}'.", "data": {"available": []}}
        
        output = "### 📦 Available Dynamic Nodes:\n" + "\n".join([f"- {n}" for n in available])
        return {"ok": True, "output": output, "data": {"available": available}}

    async def _install_node(self, node_name: str, engine: Any) -> Dict[str, Any]:
        source = os.path.join(self.library_path, f"{node_name}.py")
        dest = os.path.join(self.target_path, f"{node_name}.py")

        if not os.path.exists(source):
            return {"ok": False, "error": f"Source node {node_name} not found in library."}

        try:
            shutil.copy2(source, dest)
            # Dynamic Import and Registration
            module_path = f"core.nodes.{node_name}"
            # Reload if exists, but for first install just import
            module = importlib.import_module(module_path)
            
            # Convention: each node file should have a class named [NodeName]Node
            # e.g., weather.py -> WeatherNode
            class_name = "".join([part.capitalize() for part in node_name.split("_")]) + "Node"
            node_class = getattr(module, class_name, None)
            
            if not node_class:
                return {"ok": False, "error": f"Class {class_name} not found in {node_name}.py"}

            from core.nodes.registry import NodeRegistry
            NodeRegistry.register(node_name, node_class)
            
            await engine.log("System", f"✨ **DYNAMIC INSTALL**: Node `{node_name}` is now ready for use.")
            return {
                "ok": True, 
                "output": f"Successfully installed and registered {node_name}.",
                "data": {"node_type": node_name}
            }
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            return {"ok": False, "error": str(e)}
