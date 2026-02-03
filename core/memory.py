import json
import os
import uuid
import re
import math
import tempfile
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple, Set

logger = logging.getLogger(__name__)

# File lock for thread safety
_file_locks: Dict[str, threading.Lock] = {}


def _get_file_lock(filepath: str) -> threading.Lock:
    """Get or create a lock for the given filepath."""
    if filepath not in _file_locks:
        _file_locks[filepath] = threading.Lock()
    return _file_locks[filepath]


class TextProcessor:
    """Helper for pure-python text processing."""
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple regex tokenizer with input validation."""
        if not text or not isinstance(text, str):
            return []
        # Limit text length to prevent DoS
        text = text[:100000] if len(text) > 100000 else text
        return re.findall(r'\b\w+\b', text.lower())

    @staticmethod
    def get_ngrams(tokens: List[str], n: int = 1) -> Set[str]:
        if n == 1:
            return set(tokens)
        return set([' '.join(tokens[i:i+n]) for i in range(len(tokens)-n+1)])


class VectorStore:
    """
    A dependency-free 'VectorStore' that uses Jaccard/TF-IDF similarity
    instead of actual embeddings (for now).
    Designed to be drop-in replaced by a real embedding engine later.

    Security/Reliability improvements:
    - Atomic file writes (write to temp, then rename)
    - File locking for thread safety
    - Input validation and size limits
    - Proper exception handling
    """
    MAX_MEMORIES = 10000  # Prevent unbounded growth
    MAX_CONTENT_LENGTH = 50000  # Max characters per memory entry

    def __init__(self, filepath: str = "memory_store.json"):
        # Validate filepath
        if not filepath or '..' in filepath:
            raise ValueError("Invalid filepath")
        self.filepath = os.path.abspath(filepath)
        self.memories: List[Dict[str, Any]] = []
        self.idf_cache: Dict[str, float] = {}
        self._lock = _get_file_lock(self.filepath)
        self.load()

    def load(self):
        """Load memories from file with error handling."""
        with self._lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Validate loaded data
                        if isinstance(data, list):
                            self.memories = data[:self.MAX_MEMORIES]
                        else:
                            logger.warning("Invalid memory file format, starting fresh")
                            self.memories = []
                    self._recalculate_idf()
                except json.JSONDecodeError as e:
                    logger.error(f"[MemoryStore] Corrupted memory file: {e}")
                    self.memories = []
                    # Backup corrupted file
                    backup_path = f"{self.filepath}.corrupted.{uuid.uuid4().hex[:8]}"
                    try:
                        os.rename(self.filepath, backup_path)
                        logger.info(f"Backed up corrupted file to {backup_path}")
                    except OSError:
                        pass
                except OSError as e:
                    logger.error(f"[MemoryStore] Failed to load memory: {e}")
                    self.memories = []
            else:
                self.memories = []

    def save(self):
        """Save memories atomically using write-to-temp-then-rename pattern."""
        with self._lock:
            try:
                # Get directory of target file
                dir_path = os.path.dirname(self.filepath) or '.'

                # Write to temporary file first
                fd, temp_path = tempfile.mkstemp(
                    suffix='.json',
                    prefix='memory_',
                    dir=dir_path
                )
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as f:
                        json.dump(self.memories, f, indent=2)

                    # Atomic rename (on POSIX; on Windows, may need to remove first)
                    if os.name == 'nt':
                        # Windows: remove target first if exists
                        if os.path.exists(self.filepath):
                            os.remove(self.filepath)
                    os.rename(temp_path, self.filepath)

                except Exception:
                    # Clean up temp file on error
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise

            except OSError as e:
                logger.error(f"[MemoryStore] Failed to save memory: {e}")

    def _recalculate_idf(self):
        """Calculate Inverse Document Frequency for TF-IDF scoring."""
        doc_count = len(self.memories)
        if doc_count == 0:
            self.idf_cache = {}
            return

        term_counts: Dict[str, int] = {}
        for mem in self.memories:
            tokens = set(TextProcessor.tokenize(mem['content']))
            for t in tokens:
                term_counts[t] = term_counts.get(t, 0) + 1
        
        self.idf_cache = {
            t: math.log(doc_count / (count + 1)) 
            for t, count in term_counts.items()
        }

    def add(self, content: str, tags: List[str] = None) -> str:
        """Add a new memory entry with validation."""
        # Input validation
        if not content or not isinstance(content, str):
            raise ValueError("Content must be a non-empty string")

        # Truncate content if too long
        if len(content) > self.MAX_CONTENT_LENGTH:
            logger.warning(f"Content truncated from {len(content)} to {self.MAX_CONTENT_LENGTH}")
            content = content[:self.MAX_CONTENT_LENGTH]

        # Check memory limit
        if len(self.memories) >= self.MAX_MEMORIES:
            logger.warning("Memory limit reached, removing oldest entry")
            self.memories.pop(0)

        # Validate and sanitize tags
        if tags is None:
            tags = []
        else:
            # Ensure tags are strings and limit count
            tags = [str(t)[:100] for t in tags[:20] if t]

        memory_id = str(uuid.uuid4())
        entry = {
            "id": memory_id,
            "content": content,
            "tags": tags,
            "timestamp": str(uuid.uuid1().time),
            # Cache tokens for speed
            "_tokens": TextProcessor.tokenize(content)
        }
        self.memories.append(entry)

        # Incremental IDF update (imperative for performance, full recalc on load)
        self._recalculate_idf()
        self.save()
        return memory_id

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search memories using a hybrid score of Jaccard Similarity and TF-IDF.
        """
        query_tokens = TextProcessor.tokenize(query)
        if not query_tokens:
            return []
            
        query_set = set(query_tokens)
        scored_results: List[Tuple[float, Dict[str, Any]]] = []

        for mem in self.memories:
            # 1. Jaccard Similarity (Set Overlap)
            mem_tokens = set(mem.get('_tokens', TextProcessor.tokenize(mem['content'])))
            
            intersection = query_set.intersection(mem_tokens)
            union = query_set.union(mem_tokens)
            
            jaccard_score = len(intersection) / len(union) if union else 0.0
            
            # 2. Simplified TF-IDF (Term Importance)
            # Sum of IDF scores for matching terms
            tfidf_score = 0.0
            for token in intersection:
                tfidf_score += self.idf_cache.get(token, 0.0)
            
            # 3. Tag Bonus
            tag_score = 0.0
            for tag in mem.get('tags', []):
                if tag.lower() in query_tokens:
                    tag_score += 0.5

            # Final Weighted Score
            # TF-IDF gives rarity value, Jaccard gives coverage ratio
            final_score = (jaccard_score * 0.4) + (tfidf_score * 0.4) + (tag_score * 0.2)
            
            if final_score > 0.05: # Threshold to reduce noise
                mem_with_score = mem.copy()
                mem_with_score['score'] = final_score
                scored_results.append((final_score, mem_with_score))
        
        # Sort by score desc
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        return [r[1] for r in scored_results[:limit]]

    def clear(self):
        self.memories = []
        self.save()

# Alias for compatibility if needed
MemoryStore = VectorStore

class SummaryBufferMemory:
    """
    Maintains a buffer of recent messages and a running summary of older ones.
    """
    def __init__(self, max_buffer_tokens: int = 1500, provider: Any = None):
        self.buffer: List[Dict[str, str]] = [] # [{role: "user", content: "..."}]
        self.summary: str = ""
        self.max_buffer_tokens = max_buffer_tokens
        self.provider = provider # LLM provider to use for summarization

    def add_message(self, role: str, content: str):
        self.buffer.append({"role": role, "content": content})
        # In a real app, we'd check token count here and trigger summarization

    async def get_context(self) -> str:
        """Returns the summary + buffered messages as a string."""
        history = ""
        if self.summary:
            history += f"## Cumulative Summary of Previous Conversation:\n{self.summary}\n\n"
        
        if self.buffer:
            history += "## Recent Messages:\n"
            for msg in self.buffer:
                history += f"{msg['role'].upper()}: {msg['content']}\n"
        
        return history

    async def prune(self, provider: Any):
        """Summarizes the buffer if it's too long."""
        # Simplified: if buffer > 10 messages, summarize first 5
        if len(self.buffer) > 10:
            to_summarize = self.buffer[:5]
            self.buffer = self.buffer[5:]
            
            summary_prompt = "Summarize the following conversation snippet concisely, preserving key facts and decisions:\n\n"
            for msg in to_summarize:
                summary_prompt += f"{msg['role']}: {msg['content']}\n"
            
            new_summary = await provider.generate(
                system_prompt="You are a context manager. Summarize conversation history.",
                user_message=f"Current Summary: {self.summary}\n\nNew Snippet:\n{summary_prompt}"
            )
            self.summary = new_summary
