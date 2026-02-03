"""
Ollama LLM Provider - Local LLM inference via Ollama.
"""
import asyncio
import aiohttp
import logging
from typing import Optional, Any, Dict, List, Callable
from providers import LLMProvider, ProviderType

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama provider for local LLM inference.
    
    Requires Ollama to be installed and running locally.
    Default endpoint: http://localhost:11434
    """
    
    provider_type = ProviderType.OLLAMA
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('endpoint', 'http://localhost:11434')
        self.model = config.get('model', 'llama3')
        self.timeout = config.get('timeout', 600)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize HTTP session and verify Ollama is running."""
        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
            
            # Check if Ollama is running
            if await self.health_check():
                self._initialized = True
                logger.info(f"Ollama provider initialized with model: {self.model}")
                return True
            
            logger.warning("Ollama health check failed - server may not be running")
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama provider: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200
        except Exception:
            return False
    
    async def generate(self, system_prompt: str, user_message: str, context: Optional[str] = None, on_thought: Optional[Callable] = None, model_override: Optional[str] = None, **kwargs) -> str:
        """Generate response using Ollama Chat API with streaming for thoughts."""
        if not self._session:
            await self.initialize()
            
        current_model = model_override if model_override else self.model
        
        if on_thought:
            on_thought(f"Initializing Ollama generation with model: {current_model}...")
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if context:
            messages.append({"role": "user", "content": f"Context for your task:\n{context}"})
            messages.append({"role": "assistant", "content": "I understand the context. What is the specific task?"})
            
        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": current_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
            }
        }
        
        try:
            full_response = ""
            in_thought = False
            last_thought_pos = 0
            
            async with self._session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            try:
                                import json
                                chunk = json.loads(line.decode('utf-8'))
                                
                                # 1. Check for native 'thought' field (modern Ollama)
                                thought_chunk = chunk.get('message', {}).get('thought', '')
                                if thought_chunk and on_thought:
                                    on_thought(thought_chunk)
                                
                                # 2. Process content and check for tags
                                token = chunk.get('message', {}).get('content', '')
                                full_response += token
                                
                                # Robust thought extraction state machine
                                # Only search for new tags starting from where we left off
                                if not in_thought:
                                    # Search for open tag in the new content (or end of previous)
                                    # We search from a bit before end to catch split tags
                                    search_window_start = max(0, len(full_response) - len(token) - 10)
                                    start_tag_pos = full_response.lower().find('<think>', search_window_start)
                                    
                                    if start_tag_pos != -1:
                                        if start_tag_pos >= last_thought_pos:
                                            in_thought = True
                                            last_thought_pos = start_tag_pos + 7
                                
                                if in_thought:
                                    # Search for close tag
                                    end_tag_pos = full_response.lower().find('</think>', last_thought_pos)
                                    
                                    if end_tag_pos != -1:
                                        # Found end tag
                                        new_thought = full_response[last_thought_pos:end_tag_pos]
                                        if on_thought and new_thought.strip():
                                            on_thought(new_thought.strip())
                                        in_thought = False
                                        last_thought_pos = end_tag_pos + 8
                                    else:
                                        # Still in thought, emit incremental chunk if large enough
                                        current_len = len(full_response)
                                        # Emit everything new
                                        if current_len - last_thought_pos > 10:
                                            chunk_text = full_response[last_thought_pos:]
                                            if on_thought:
                                                on_thought(chunk_text)
                                            last_thought_pos = current_len
                                
                                # Check if done
                                if chunk.get('done', False):
                                    if in_thought and on_thought:
                                        final_thought = full_response[last_thought_pos:]
                                        if final_thought.strip():
                                            on_thought(final_thought.strip())
                                    break
                            except json.JSONDecodeError:
                                continue
                    
                    return full_response
                else:
                    error = await response.text()
                    logger.error(f"Ollama API error: {error}")
                    return f"Error: Ollama returned status {response.status}"
                    
        except asyncio.TimeoutError:
            logger.error("Ollama request timed out")
            return "Error: Request timed out"
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            return f"Error: {str(e)}"
    
    async def list_models(self) -> list:
        """List available Ollama models."""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return [m['name'] for m in data.get('models', [])]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
        return []
    
    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
