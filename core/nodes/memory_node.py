from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MemoryNode:
    """
    Handles interaction with Long-Term Memory (LTM).
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        # This logic will be called by WorkflowEngine which already has the memory_store instance.
        # However, to be truly modular, we might want to pass the engine or store as context.
        
        # For compatibility with the current WorkflowEngine._execute_node:
        # We expect context['memory_store'] to be present.
        
        store = context.get('memory_store')
        if not store:
            return {"ok": False, "error": "No MemoryStore available in context"}

        action = self.config.get("action", "retrieve")
        input_text = inputs.get("text") or inputs.get("query")
        
        if not input_text:
            return {"ok": False, "error": "No input text provided for memory operation"}

        if action == "store":
            tags = self.config.get("tags", [])
            if isinstance(tags, str): tags = [t.strip() for t in tags.split(",")]
            
            mem_id = store.add(content=input_text, tags=tags)
            return {
                "ok": True, 
                "output": f"Memory stored successfully. ID: {mem_id}",
                "data": {"memory_id": mem_id}
            }
        else: # Retrieve
            limit = int(self.config.get("limit", 5))
            results = store.search(query=input_text, limit=limit)
            
            if results:
                output = "## Retrieved Memories:\n"
                for i, r in enumerate(results, 1):
                    # Robust check for score
                    score = r.get('score', 0.0)
                    preview = r['content'][:200].replace('\n', ' ')
                    output += f"{i}. [{score:.2f}] {preview}...\n"
                return {"ok": True, "output": output, "data": {"results": results}}
            else:
                return {"ok": True, "output": "No relevant memories found.", "data": {"results": []}}
