"""
Groq LLM Provider - Fast inference with generous free tier.
"""
import asyncio
import aiohttp
import os
import logging
from typing import Optional, Dict, Any, List, Callable
from providers import LLMProvider, ProviderType

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """
    Groq provider for fast LLM inference.
    
    Free tier: 30 requests/minute
    Models: llama-3.3-70b-versatile, mixtral-8x7b-32768, etc.
    """
    
    provider_type = ProviderType.GROQ
    BASE_URL = "https://api.groq.com/openai/v1"
    
    AVAILABLE_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('GROQ_API_KEY')
        self.model = config.get('model', 'llama-3.3-70b-versatile')
        self.timeout = config.get('timeout', 60)
        self.max_tokens = config.get('max_tokens', 2048)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize HTTP session."""
        if not self.api_key:
            logger.warning("Groq API key not set. Set GROQ_API_KEY env var or pass api_key in config.")
            return False
        
        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if await self.health_check():
                self._initialized = True
                logger.info(f"Groq provider initialized with model: {self.model}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize Groq provider: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if Groq API is accessible."""
        try:
            if not self._session:
                return False
            
            async with self._session.get(f"{self.BASE_URL}/models") as response:
                return response.status == 200
        except Exception:
            return False
    
    async def generate(self, system_prompt: str, user_message: str, context: Optional[str] = None, on_thought: Optional[Callable] = None, model_override: Optional[str] = None) -> str:
        """Generate response using Groq API."""
        if not self._session:
            if not await self.initialize():
                return "Error: Groq provider not initialized"
        
        current_model = model_override if model_override else self.model
        
        # Emit status thought
        if on_thought:
            on_thought(f"Sending request to Groq inference engine (model: {current_model})...")
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if context:
            messages.append({"role": "assistant", "content": f"Context: {context}"})
        
        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": current_model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.7,
        }
        
        try:
            async with self._session.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data['choices'][0]['message']['content']
                    
                    # Check for deepseek-style thoughts in content if we are using a reasoning model
                    # (Simple check for now)
                    if on_thought and '<think>' in content:
                        import re
                        thoughts = re.findall(r'<think>(.*?)</think>', content, re.DOTALL)
                        for t in thoughts:
                            on_thought(t.strip())
                            
                    return content
                elif response.status == 429:
                    logger.warning("Groq rate limit hit")
                    return "Error: Rate limit exceeded. Please wait a moment."
                else:
                    error = await response.text()
                    logger.error(f"Groq API error: {error}")
                    return f"Error: Groq API returned {response.status}"
                    
        except asyncio.TimeoutError:
            logger.error("Groq request timed out")
            return "Error: Request timed out"
        except Exception as e:
            logger.error(f"Groq generate error: {e}")
            return f"Error: {str(e)}"
    
    async def list_models(self) -> List[str]:
        """List available Groq models."""
        return self.AVAILABLE_MODELS
    
    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
