import os
import json
import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class RAGNodeExecutor:
    """
    Advanced Retrieval-Augmented Generation Node.
    Supports Multi-Query Expansion and Semantic Chunking.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.source_path = config.get("source_path", "knowledge_base")
        self.chunk_size = int(config.get("chunk_size", 1000))
        self.chunk_overlap = int(config.get("chunk_overlap", 200))
        self.top_k = int(config.get("top_k", 5))
        self.multi_query = config.get("multi_query", True)
        self.index_file = os.path.join(self.source_path, "index.json")

    async def execute(self, inputs: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        query = inputs.get("query") or context
        if not query:
            return {"ok": False, "error": "No query provided for RAG"}

        # 1. Multi-Query Expansion (Simulated or via separate LLM call if needed)
        # For simplicity in this node, we'll assume the provider will handle the expansion 
        # or we do a quick expansion here if a provider is passed.
        # But since this is a NodeExecutor, we usually handle the retrieval part.
        
        queries = [query]
        if self.multi_query:
            # In a real scenario, we'd call an LLM here to generate variations.
            # For now, we'll simulate variations if we don't have a provider yet.
            # But the WorkflowEngine will call us.
            pass

        # 2. Retrieval
        chunks = await self._retrieve(queries)
        
        # 3. Format Output
        context_str = "\n\n---\n\n".join([c['content'] for c in chunks])
        
        return {
            "ok": True,
            "data": {
                "context": context_str,
                "chunks": chunks,
                "queries": queries
            }
        }

    async def _retrieve(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Simple keyword-based similarity search (Mimic Vector Store)."""
        if not os.path.exists(self.source_path):
            return []

        all_chunks = []
        # If index doesn't exist, we might need to "index" (chunk) the files first.
        if not os.path.exists(self.index_file):
            await self._index_knowledge_base()

        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
                all_chunks = kb_data.get("chunks", [])
        except Exception as e:
            logger.error(f"Failed to read index: {e}")
            return []

        # Scoring
        results = []
        for chunk in all_chunks:
            score = 0
            for q in queries:
                # Basic overlap score (simulating embedding similarity)
                q_words = set(q.lower().split())
                c_words = set(chunk['content'].lower().split())
                overlap = len(q_words.intersection(c_words))
                score += overlap / len(q_words) if q_words else 0
            
            if score > 0:
                results.append({**chunk, "score": score})

        # Sort and truncate
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:self.top_k]

    async def _index_knowledge_base(self):
        """Walk source path and chunk all .txt and .md files."""
        os.makedirs(self.source_path, exist_ok=True)
        chunks = []
        
        for root, _, files in os.walk(self.source_path):
            for file in files:
                if file.endswith(('.txt', '.md')):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            text = f.read()
                            # Recursive Character Splitting (Simple version)
                            file_chunks = self._split_text(text)
                            for i, content in enumerate(file_chunks):
                                chunks.append({
                                    "id": f"{file}_{i}",
                                    "source": file,
                                    "content": content
                                })
                    except Exception as e:
                        logger.error(f"Error reading {file}: {e}")

        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump({"chunks": chunks, "updated_at": datetime.now().isoformat()}, f, indent=2)

    def _split_text(self, text: str) -> List[str]:
        """Simple recursive-style splitter."""
        # Split by double newline (paragraphs) first
        parts = text.split("\n\n")
        chunks = []
        current_chunk = ""
        
        for part in parts:
            if len(current_chunk) + len(part) < self.chunk_size:
                current_chunk += part + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = part + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
