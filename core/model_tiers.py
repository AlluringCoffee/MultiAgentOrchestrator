"""
Model Tier System for Auto-Switching Based on Categories and Limits
"""
import time
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

class ModelTier(Enum):
    """Model performance tiers"""
    S = "S"  # Premium/Best
    A = "A"  # High-performance free
    B = "B"  # Good free
    C = "C"  # Basic free
    D = "D"  # Local/Low-resource

class TaskCategory(Enum):
    """Task categories for model selection"""
    CODING = "coding"
    WRITING = "writing"
    DESIGNING = "designing"
    GRAPHICS = "graphics"
    ART = "art"
    GENERAL = "general"

class ModelTierManager:
    """
    Manages model tiers and automatic switching when limits are hit.
    """

    # Tier definitions by category (provider_id: model_name)
    TIERS = {
        TaskCategory.CODING: {
            ModelTier.S: ["claude-sonnet", "gpt-oss:120b"],
            ModelTier.A: ["deepseek-r1:32b", "qwen3:30b", "groq_free:llama-3.3-70b-versatile"],
            ModelTier.B: ["qwen2.5-coder:32b", "gemma3:12b", "phi4:14b"],
            ModelTier.C: ["ollama:llama3.1:70b", "mistral-small3.2:24b", "deepseek-v3:671b"],
            ModelTier.D: ["ollama:llama3.2:3b", "ollama:phi3", "ollama:smollm:1.7b"]
        },
        TaskCategory.WRITING: {
            ModelTier.S: ["claude-sonnet"],
            ModelTier.A: ["google_ai_free:gemini-1.5-pro", "claude_haiku_free:claude-3-haiku-20240307", "deepseek-r1:14b"],
            ModelTier.B: ["ollama:llama3.1:70b", "qwen3:8b", "gpt-oss:20b"],
            ModelTier.C: ["google_ai_free:gemini-1.5-flash", "mistral-small3.2:24b", "gemma3:4b"],
            ModelTier.D: ["ollama:llama3.2:3b", "ollama:phi3", "ollama:smollm:360m"]
        },
        TaskCategory.DESIGNING: {
            ModelTier.S: ["claude-sonnet"],
            ModelTier.A: ["google_ai_free:gemini-1.5-pro", "qwen3-vl:30b", "llama3.2-vision:90b"],
            ModelTier.B: ["google_ai_free:gemini-2.0-flash", "claude_haiku_free:claude-3-haiku-20240307", "deepseek-r1:14b"],
            ModelTier.C: ["ollama:llama3.1:70b", "qwen2.5vl:32b", "gemma3:12b"],
            ModelTier.D: ["ollama:smollm:1.7b", "ollama:llama3.2:3b"]
        },
        TaskCategory.GRAPHICS: {
            ModelTier.S: ["claude-sonnet"],
            ModelTier.A: ["google_ai_free:gemini-1.5-pro", "deepseek-r1:14b", "qwen3:8b"],
            ModelTier.B: ["claude_haiku_free:claude-3-haiku-20240307", "ollama:llama3.1:70b", "google_ai_free:gemini-1.5-flash"],
            ModelTier.C: ["gemma3:4b", "mistral-small3.2:24b", "phi4:14b"],
            ModelTier.D: ["ollama:llama3.2:3b", "ollama:smollm:1.7b"]
        },
        TaskCategory.ART: {
            ModelTier.S: ["claude-sonnet"],
            ModelTier.A: ["google_ai_free:gemini-1.5-pro", "deepseek-r1:14b", "qwen3:8b"],
            ModelTier.B: ["claude_haiku_free:claude-3-haiku-20240307", "ollama:llama3.1:70b", "google_ai_free:gemini-1.5-flash"],
            ModelTier.C: ["gemma3:4b", "mistral-small3.2:24b", "phi4:14b"],
            ModelTier.D: ["ollama:llama3.2:3b", "ollama:smollm:1.7b"]
        },
        TaskCategory.GENERAL: {
            ModelTier.S: ["claude-sonnet", "gpt-oss:120b"],
            ModelTier.A: ["deepseek-r1:14b", "google_ai_free:gemini-1.5-pro", "groq_free:llama-3.3-70b-versatile"],
            ModelTier.B: ["claude_haiku_free:claude-3-haiku-20240307", "ollama:llama3.1:70b", "qwen3:8b"],
            ModelTier.C: ["google_ai_free:gemini-1.5-flash", "mistral-small3.2:24b", "gpt-oss:20b"],
            ModelTier.D: ["ollama:llama3.2:3b", "ollama:phi3", "ollama:smollm:1.7b"]
        }
    }

    def __init__(self):
        self.limit_cooldowns = {}  # provider_id -> cooldown_until timestamp
        self.current_usage = {}    # provider_id -> usage_count

    def get_best_available_model(self, category: TaskCategory, current_provider: str = None) -> Optional[str]:
        """
        Get the best available model for a category, considering limits and cooldowns.

        Args:
            category: Task category
            current_provider: Current provider being used (to avoid switching unnecessarily)

        Returns:
            provider:model format or None if no models available
        """
        now = time.time()

        # Start from highest tier
        for tier in [ModelTier.S, ModelTier.A, ModelTier.B, ModelTier.C, ModelTier.D]:
            if tier not in self.TIERS[category]:
                continue

            for model_spec in self.TIERS[category][tier]:
                # Parse provider:model
                if ":" in model_spec:
                    provider_id, model_name = model_spec.split(":", 1)
                else:
                    # Fallback model without provider
                    continue

                # Check if provider is on cooldown
                if provider_id in self.limit_cooldowns:
                    if now < self.limit_cooldowns[provider_id]:
                        logger.info(f"Provider {provider_id} on cooldown until {self.limit_cooldowns[provider_id]}")
                        continue
                    else:
                        # Cooldown expired, remove it
                        del self.limit_cooldowns[provider_id]

                # If this is the current provider, prefer to keep using it
                if current_provider == provider_id:
                    return model_spec

                # Check if this provider has available capacity (simplified check)
                if self._has_capacity(provider_id):
                    return model_spec

        logger.warning(f"No available models found for category {category.value}")
        return None

    def report_limit_hit(self, provider_id: str):
        """
        Report that a provider hit its limit. Set cooldown for 1 hour.
        """
        cooldown_until = time.time() + 3600  # 1 hour
        self.limit_cooldowns[provider_id] = cooldown_until
        logger.info(f"Provider {provider_id} hit limit, cooldown until {cooldown_until}")

    def _has_capacity(self, provider_id: str) -> bool:
        """
        Check if provider has capacity (simplified - in real implementation,
        this would check actual API limits, tokens used, etc.)
        """
        # For free tiers, assume limited capacity
        free_providers = ["groq_free", "google_ai_free", "claude_haiku_free"]
        if provider_id in free_providers:
            usage = self.current_usage.get(provider_id, 0)
            # Assume 1000 requests per hour limit for free tiers
            return usage < 1000

        # Local/Ollama has unlimited capacity
        if provider_id == "ollama":
            return True

        # OpenCode has capacity
        if "opencode" in provider_id:
            return True

        return True  # Assume paid tiers have capacity

    def record_usage(self, provider_id: str):
        """Record usage for a provider"""
        self.current_usage[provider_id] = self.current_usage.get(provider_id, 0) + 1

    def reset_usage(self, provider_id: str):
        """Reset usage counter (call hourly)"""
        if provider_id in self.current_usage:
            self.current_usage[provider_id] = 0

    def get_tier_info(self, category: TaskCategory) -> Dict[str, List[str]]:
        """Get tier information for a category"""
        return {tier.value: models for tier, models in self.TIERS[category].items()}

# Global instance
tier_manager = ModelTierManager()