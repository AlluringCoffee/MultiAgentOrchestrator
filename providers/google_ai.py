"""
Google AI Studio Provider - Free tier Gemini access.
"""
import asyncio
import aiohttp
import os
import logging
from typing import Optional, Dict, Any, List, Callable
from providers import LLMProvider, ProviderType

logger = logging.getLogger(__name__)


class GoogleAIProvider(LLMProvider):
    """
    Google AI Studio provider for Gemini models.
    
    Free tier: 60 requests/minute
    Models: gemini-1.5-flash, gemini-1.5-pro, etc.
    """
    
    provider_type = ProviderType.GOOGLE_AI
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    
    AVAILABLE_MODELS = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-lite-preview-02-05", # Adding some modern versions
        "gemini-2.5-pro",
        "gemini-2.5-flash",
    ]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('GOOGLE_AI_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.model = config.get('model', 'gemini-1.5-flash')
        self.timeout = config.get('timeout', 60)
        self.max_tokens = config.get('max_tokens', 2048)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize HTTP session."""
        if not self.api_key:
            logger.warning("Google AI API key not set. Set GOOGLE_AI_API_KEY or GEMINI_API_KEY env var.")
            return False
        
        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
            
            if await self.health_check():
                self._initialized = True
                logger.info(f"Google AI provider initialized with model: {self.model}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize Google AI provider: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if Google AI API is accessible."""
        try:
            if not self._session or not self.api_key:
                return False
            
            url = f"{self.BASE_URL}/models?key={self.api_key}"
            async with self._session.get(url) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def generate(self, system_prompt: str, user_message: str, context: Optional[str] = None, on_thought: Optional[Callable] = None, model_override: Optional[str] = None) -> str:
        """Generate response using Google AI API."""
        if not self._session:
            if not await self.initialize():
                return "Error: Google AI provider not initialized"
        
        # Refresh API key from env in case it was set late
        if not self.api_key:
             self.api_key = os.getenv('GOOGLE_AI_API_KEY') or os.getenv('GEMINI_API_KEY')
        
        current_model = model_override if model_override else self.model
        
        if on_thought:
            on_thought(f"Processing with Gemini model: {current_model}...")
        
        # Build content parts
        contents = []
        
        # Move system instruction to a leading user turn for better compatibility
        all_parts = []
        all_parts.append({"text": f"### SYSTEM DIRECTIVE:\n{system_prompt}\n\n"})
        
        if context:
            all_parts.append({"text": f"### REFERENCE CONTEXT:\n{context}\n\n"})
        
        all_parts.append({"text": f"### MISSION INPUT:\n{user_message}"})
        
        contents.append({
            "role": "user",
            "parts": all_parts
        })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 4096,
                "temperature": 0.3, # Slightly higher for creative but safe code
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        
        url = f"{self.BASE_URL}/models/{current_model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        try:
            async with self._session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    candidates = data.get('candidates', [])
                    if candidates:
                        content = candidates[0].get('content', {})
                        parts = content.get('parts', [])
                        
                        # Extract usage metadata
                        usage = data.get('usageMetadata', {})
                        if usage and on_thought:
                            import json
                            # Normalize keys
                            metrics = {
                                "input_tokens": usage.get("promptTokenCount", 0),
                                "output_tokens": usage.get("candidatesTokenCount", 0),
                                "total_tokens": usage.get("totalTokenCount", 0)
                            }
                            # Emit hidden usage event
                            on_thought(f"<<<USAGE: {json.dumps(metrics)}>>>")

                        if parts:
                            res_text = parts[0].get('text', '')
                            print(f"DEBUG GEMINI SUCCESS: {current_model} - {len(res_text)} chars")
                            return res_text
                    print(f"DEBUG GEMINI EMPTY: {data}")
                    return "No response generated"
                elif response.status == 429:
                    logger.warning("Google AI rate limit hit")
                    return "Error: Rate limit exceeded. Please wait a moment."
                else:
                    error = await response.text()
                    logger.error(f"Google AI API error: {error}")
                    print(f"DEBUG GEMINI ERROR: {response.status} - {error}")
                    return f"Error: Google AI API returned {response.status}"
                    
        except asyncio.TimeoutError:
            logger.error("Google AI request timed out")
            return "Error: Request timed out"
        except Exception as e:
            logger.error(f"Google AI generate error: {e}")
            return f"Error: {str(e)}"
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using embedding-001."""
        if not self._session:
            await self.initialize()
            
        model = "models/text-embedding-004" # Newer, better model
        url = f"{self.BASE_URL}/{model}:embedContent?key={self.api_key}"
        
        payload = {
            "content": {
                "parts": [{"text": text}]
            }
        }
        
        try:
            async with self._session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("embedding", {}).get("values", [])
                else:
                    logger.error(f"Embedding failed: {response.status} - {await response.text()}")
                    return []
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return []

    async def list_models(self) -> List[str]:
        """List available Google AI models."""
        return self.AVAILABLE_MODELS
    
    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
