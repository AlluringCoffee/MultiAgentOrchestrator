"""
LLM Provider base class and registry for multi-backend support.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, TypeVar, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Available LLM provider types."""
    SIMULATION = "simulation"
    MOCK = "simulation" # Alias for backward compatibility
    OLLAMA = "ollama"
    CLI_BRIDGE = "cli_bridge"
    OPENCODE = "opencode"
    GROQ = "groq"
    GOOGLE_AI = "google_ai"
    CLAUDE_CODE = "claude_code"
    ANTHROPIC = "anthropic"  # Alias for claude_code


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Each provider implements async generate for its specific backend.
    """
    
    provider_type: ProviderType = ProviderType.SIMULATION
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config.get('model', 'default')
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider connection. Returns True if successful."""
        pass
    
    @abstractmethod
    async def generate(self, system_prompt: str, user_message: str, context: Optional[str] = None, on_thought: Optional[Callable] = None, model_override: Optional[str] = None) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available."""
        pass
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    def get_info(self) -> Dict[str, Any]:
        """Get provider info for UI display."""
        return {
            "type": self.provider_type.value,
            "model": self.model,
            "initialized": self._initialized
        }


class ProviderRegistry:
    """
    Registry for LLM providers.
    Manages provider instances and provides factory methods.
    """
    
    _providers: Dict[str, Type[LLMProvider]] = {}
    _instances: Dict[str, LLMProvider] = {}
    
    @classmethod
    def register(cls, provider_type: str, provider_class: Type[LLMProvider]):
        """Register a provider class."""
        cls._providers[provider_type] = provider_class
        logger.info(f"Registered LLM provider: {provider_type}")
    
    @classmethod
    def create(cls, provider_type: str, config: Dict[str, Any], instance_id: Optional[str] = None) -> LLMProvider:
        """
        Create a provider instance.
        
        Args:
            provider_type: Type of provider (ollama, groq, etc.)
            config: Provider configuration
            instance_id: Optional unique ID for caching
        """
        if provider_type not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_type}. Available: {list(cls._providers.keys())}")
        
        # Check for cached instance
        if instance_id and instance_id in cls._instances:
            return cls._instances[instance_id]
        
        provider = cls._providers[provider_type](config)
        
        if instance_id:
            cls._instances[instance_id] = provider
        
        return provider
    
    @classmethod
    def get_available(cls) -> List[str]:
        """List available provider types."""
        return list(cls._providers.keys())
    
    @classmethod
    def get_instance(cls, instance_id: str) -> Optional[LLMProvider]:
        """Get a cached provider instance."""
        return cls._instances.get(instance_id)
    
    @classmethod
    def clear_instances(cls):
        """Clear all cached instances."""
        cls._instances.clear()


# Import and register providers when this module loads
def _register_providers():
    """Register all available providers."""
    from providers.mock import MockProvider
    from providers.ollama import OllamaProvider
    from providers.cli_bridge import CLIBridgeProvider, GeminiCLIProvider
    from providers.groq import GroqProvider
    from providers.google_ai import GoogleAIProvider
    from providers.claude_code import ClaudeCodeProvider, ClaudeSonnetProvider, ClaudeOpusProvider, ClaudeHaikuProvider

    ProviderRegistry.register("simulation", MockProvider)
    ProviderRegistry.register("ollama", OllamaProvider)
    ProviderRegistry.register("cli_bridge", CLIBridgeProvider)
    ProviderRegistry.register("opencode", CLIBridgeProvider)  # Use CLIBridge for OpenCode
    ProviderRegistry.register("gemini", GeminiCLIProvider)
    ProviderRegistry.register("groq", GroqProvider)
    ProviderRegistry.register("google_ai", GoogleAIProvider)
    # Claude Code CLI providers - uses your Anthropic API subscription
    ProviderRegistry.register("claude_code", ClaudeCodeProvider)
    ProviderRegistry.register("anthropic", ClaudeCodeProvider)  # Alias
    ProviderRegistry.register("claude-sonnet", ClaudeSonnetProvider)
    ProviderRegistry.register("claude-opus", ClaudeOpusProvider)
    ProviderRegistry.register("claude-haiku", ClaudeHaikuProvider)


# Register on load
_register_providers()
