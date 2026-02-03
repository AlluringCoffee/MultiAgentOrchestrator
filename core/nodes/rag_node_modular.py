import logging
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class RagNode:
    """
    RAG (Retrieval Augmented Generation) Node.
    Handles multi-query expansion and vector retrieval.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        engine = context.get('engine')
        node = context.get('node')
        input_text = inputs.get('text') or inputs.get('query', '')
        
        if not engine: return {"ok": False, "error": "No engine"}

        from core.nodes.rag_node import RAGNodeExecutor # Re-use existing retrieval logic if possible
        
        await engine.log(node.name, f"📚 Consulting the Knowledge Base...")
        
        # Step 1: Multi-Query Expansion
        queries = [input_text]
        if self.config.get("multi_query", True):
            try:
                provider = await engine._get_provider(node)
                if provider:
                    await engine.log(node.name, "🧠 Expanding query for better retrieval...")
                    expansion_prompt = f"Generate 3 diverse search queries based on this user question to retrieve better information from a knowledge base. Output ONLY the queries separated by newlines, no other text.\n\nQUESTION: {input_text}"
                    expansion_resp = await provider.generate(
                        system_prompt="You are a retrieval optimizer.",
                        user_message=expansion_prompt,
                        model_override=node.model
                    )
                    expanded = [q.strip() for q in expansion_resp.split("\n") if q.strip()][:3]
                    if expanded:
                        queries.extend(expanded)
                        await engine.log(node.name, f"🔍 Expanded to {len(queries)} sub-queries.")
            except Exception as e:
                await engine.log(node.name, f"⚠️ Multi-query expansion failed: {e}")

        # Step 2: Retrieval (using RAGNodeExecutor logic)
        executor = RAGNodeExecutor(node_id=self.node_id, config=self.config)
        
        # We might need to override the query in inputs or loop it
        # For now, just execute with the primary query (RAGNodeExecutor should ideally handle multi-query)
        rag_result = await executor.execute({"query": input_text}, context=context)
        
        if rag_result.get("ok"):
            data = rag_result["data"]
            chunks = data.get("chunks", [])
            
            # Emit retrieved chunks as thoughts
            if chunks:
                chunk_summary = "### 📚 Retrieved Context Chunks\n\n"
                for i, chunk in enumerate(chunks, 1):
                    chunk_summary += f"**Chunk {i} (Source: {chunk['source']})**:\n> {chunk['content'][:300]}...\n\n"
                
                await engine.emit_thought(node.name, chunk_summary)
                await engine.log(node.name, f"✅ Retrieved {len(chunks)} relevant chunks.")
            
            return {"ok": True, "output": data["context"], "data": data}
        else:
            return {"ok": False, "error": rag_result.get("error")}
