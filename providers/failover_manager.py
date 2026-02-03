"""
Failover Manager - Automatic model switching when rate limits or errors occur.

This module provides intelligent failover capabilities:
1. Detects rate limits, timeouts, and API errors
2. Automatically switches to the next best available model/provider
3. Maintains a priority queue of fallback options
4. Tracks provider health and adjusts priorities dynamically
5. Integrates with ModelTierManager for category-based tier switching
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Import tier manager
try:
    from core.model_tiers import tier_manager, TaskCategory
    TIER_ENABLED = True
except ImportError:
    TIER_ENABLED = False
    logger.warning("Model tier manager not available - category-based switching disabled")


class FailoverReason(Enum):
    """Reasons for triggering failover."""
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    AUTHENTICATION = "authentication"
    QUOTA_EXCEEDED = "quota_exceeded"
    MODEL_UNAVAILABLE = "model_unavailable"
    UNKNOWN = "unknown"


@dataclass
class ProviderHealth:
    """Tracks health and performance of a provider."""
    provider_id: str
    provider_type: str
    model: str
    success_count: int = 0
    failure_count: int = 0
    last_success: float = 0
    last_failure: float = 0
    cooldown_until: float = 0  # Timestamp when cooldown ends
    priority: int = 0  # Lower = higher priority
    avg_response_time: float = 0

    @property
    def is_available(self) -> bool:
        """Check if provider is available (not in cooldown)."""
        return time.time() > self.cooldown_until

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 1.0

    def record_success(self, response_time: float):
        """Record a successful request."""
        self.success_count += 1
        self.last_success = time.time()
        # Update rolling average
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time * 0.9) + (response_time * 0.1)

    def record_failure(self, reason: FailoverReason, cooldown_seconds: int = 60):
        """Record a failure and apply cooldown."""
        self.failure_count += 1
        self.last_failure = time.time()

        # Apply cooldown based on failure reason
        cooldown_map = {
            FailoverReason.RATE_LIMIT: 300,      # 5 minutes
            FailoverReason.QUOTA_EXCEEDED: 3600, # 1 hour
            FailoverReason.TIMEOUT: 60,          # 1 minute
            FailoverReason.API_ERROR: 120,       # 2 minutes
            FailoverReason.AUTHENTICATION: 0,    # Don't retry auth errors
            FailoverReason.MODEL_UNAVAILABLE: 600,  # 10 minutes
            FailoverReason.UNKNOWN: 60
        }

        self.cooldown_until = time.time() + cooldown_map.get(reason, cooldown_seconds)
        logger.warning(f"Provider {self.provider_id}/{self.model} in cooldown until {self.cooldown_until}")


@dataclass
class FailoverConfig:
    """Configuration for failover behavior."""
    enabled: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0
    priority_order: List[str] = field(default_factory=list)

    # Model equivalence groups (models that can substitute for each other)
    model_groups: Dict[str, List[str]] = field(default_factory=lambda: {
        "high_capability": [
            "opus", "claude-opus", "gpt-4", "gemini-1.5-pro",
            "llama-3.3-70b-versatile", "deepseek-r1"
        ],
        "balanced": [
            "sonnet", "claude-sonnet", "gpt-4-turbo", "gemini-1.5-flash",
            "llama3-8b-8192", "mistral", "llama3"
        ],
        "fast": [
            "haiku", "claude-haiku", "gpt-3.5-turbo", "gemini-2.0-flash",
            "phi3", "mixtral-8x7b-32768"
        ]
    })


class FailoverManager:
    """
    Manages automatic failover between providers and models.

    Usage:
        manager = FailoverManager()
        manager.register_provider("claude_code", "claude_code", ["sonnet", "opus", "haiku"])
        manager.register_provider("groq", "groq", ["llama-3.3-70b-versatile"])

        async def generate_with_failover(prompt):
            return await manager.execute_with_failover(
                provider_id="claude_code",
                model="sonnet",
                task=lambda p, m: some_provider.generate(prompt)
            )
    """

    def __init__(self, config: Optional[FailoverConfig] = None):
        self.config = config or FailoverConfig()
        self.providers: Dict[str, ProviderHealth] = {}
        self.fallback_chains: Dict[str, List[Tuple[str, str]]] = {}

    def register_provider(
        self,
        provider_id: str,
        provider_type: str,
        models: List[str],
        priority: int = 100
    ):
        """Register a provider and its models."""
        for model in models:
            key = f"{provider_id}/{model}"
            self.providers[key] = ProviderHealth(
                provider_id=provider_id,
                provider_type=provider_type,
                model=model,
                priority=priority
            )
            logger.info(f"Registered failover provider: {key} (priority: {priority})")

    def set_fallback_chain(
        self,
        provider_id: str,
        model: str,
        fallbacks: List[Tuple[str, str]]
    ):
        """
        Set explicit fallback chain for a provider/model.

        Args:
            provider_id: Primary provider ID
            model: Primary model name
            fallbacks: List of (provider_id, model) tuples to try in order
        """
        key = f"{provider_id}/{model}"
        self.fallback_chains[key] = fallbacks
        logger.info(f"Set fallback chain for {key}: {fallbacks}")

    def _get_fallback_candidates(
        self,
        provider_id: str,
        model: str,
        task_category: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """Get ordered list of fallback candidates."""
        key = f"{provider_id}/{model}"

        # Check for explicit fallback chain
        if key in self.fallback_chains:
            return self.fallback_chains[key]

        # Use tier manager if available and category provided
        if TIER_ENABLED and task_category:
            try:
                category = TaskCategory(task_category.lower())
                tier_model = tier_manager.get_best_available_model(category, provider_id)
                if tier_model and ":" in tier_model:
                    fallback_provider, fallback_model = tier_model.split(":", 1)
                    if fallback_provider != provider_id or fallback_model != model:
                        # Report limit hit for tier switching
                        tier_manager.report_limit_hit(provider_id)
                        return [(fallback_provider, fallback_model)]
            except ValueError:
                logger.warning(f"Unknown task category: {task_category}")

        # Build automatic fallback chain based on model capability
        candidates = []

        # Find which capability group the model belongs to
        model_group = None
        for group, models in self.config.model_groups.items():
            if model.lower() in [m.lower() for m in models]:
                model_group = group
                break

        # Get all available providers in the same capability group
        if model_group:
            for pkey, health in self.providers.items():
                if pkey == key:
                    continue
                if not health.is_available:
                    continue
                if health.model.lower() in [m.lower() for m in self.config.model_groups[model_group]]:
                    candidates.append((health.provider_id, health.model))

        # Sort by priority and success rate
        candidates.sort(key=lambda x: (
            self.providers.get(f"{x[0]}/{x[1]}", ProviderHealth("", "", "")).priority,
            -self.providers.get(f"{x[0]}/{x[1]}", ProviderHealth("", "", "")).success_rate
        ))

        # If no candidates in same group, try any available provider
        if not candidates:
            for pkey, health in self.providers.items():
                if pkey == key or not health.is_available:
                    continue
                candidates.append((health.provider_id, health.model))
            candidates.sort(key=lambda x: self.providers.get(f"{x[0]}/{x[1]}", ProviderHealth("", "", "")).priority)

        return candidates

    def detect_failure_reason(self, error: str) -> FailoverReason:
        """Detect the reason for failure from error message."""
        error_lower = error.lower()

        if any(x in error_lower for x in ['rate limit', 'too many requests', '429', 'throttl']):
            return FailoverReason.RATE_LIMIT
        elif any(x in error_lower for x in ['timeout', 'timed out']):
            return FailoverReason.TIMEOUT
        elif any(x in error_lower for x in ['quota', 'exceeded', 'limit exceeded']):
            return FailoverReason.QUOTA_EXCEEDED
        elif any(x in error_lower for x in ['auth', 'unauthorized', '401', '403', 'api key']):
            return FailoverReason.AUTHENTICATION
        elif any(x in error_lower for x in ['not found', '404', 'unavailable', 'does not exist']):
            return FailoverReason.MODEL_UNAVAILABLE
        elif any(x in error_lower for x in ['error', '500', '502', '503']):
            return FailoverReason.API_ERROR

        return FailoverReason.UNKNOWN

    async def execute_with_failover(
        self,
        provider_id: str,
        model: str,
        task: Callable[[str, str], Any],
        on_failover: Optional[Callable[[str, str, str, str, str], None]] = None,
        task_category: Optional[str] = None
    ) -> Tuple[Any, str, str]:
        """
        Execute a task with automatic failover on failure.

        Args:
            provider_id: Primary provider ID
            model: Primary model name
            task: Async function(provider_id, model) -> result
            on_failover: Callback(old_provider, old_model, new_provider, new_model, reason)

        Returns:
            Tuple of (result, final_provider_id, final_model)
        """
        if not self.config.enabled:
            result = await task(provider_id, model)
            return result, provider_id, model

        key = f"{provider_id}/{model}"
        attempts = [(provider_id, model)]
        last_error = None

        # Try primary provider
        for attempt in range(self.config.max_retries + 1):
            current_provider, current_model = attempts[-1]
            current_key = f"{current_provider}/{current_model}"

            try:
                start_time = time.time()
                result = await task(current_provider, current_model)

                # Check if result indicates an error
                if isinstance(result, str) and result.startswith("Error:"):
                    raise Exception(result)

                # Record success
                elapsed = time.time() - start_time
                if current_key in self.providers:
                    self.providers[current_key].record_success(elapsed)

                return result, current_provider, current_model

            except Exception as e:
                last_error = str(e)
                reason = self.detect_failure_reason(last_error)
                logger.warning(f"Failover triggered for {current_key}: {reason.value} - {last_error[:100]}")

                # Record failure
                if current_key in self.providers:
                    self.providers[current_key].record_failure(reason)

                # Get fallback candidates
                fallbacks = self._get_fallback_candidates(current_provider, current_model, task_category)

                # Find next available fallback
                next_fallback = None
                for fb_provider, fb_model in fallbacks:
                    fb_key = f"{fb_provider}/{fb_model}"
                    if fb_key not in [f"{p}/{m}" for p, m in attempts]:
                        if fb_key in self.providers and self.providers[fb_key].is_available:
                            next_fallback = (fb_provider, fb_model)
                            break

                if next_fallback:
                    if on_failover:
                        on_failover(
                            current_provider, current_model,
                            next_fallback[0], next_fallback[1],
                            reason.value
                        )
                    attempts.append(next_fallback)
                    logger.info(f"Failing over from {current_key} to {next_fallback[0]}/{next_fallback[1]}")

                    # Brief delay before retry
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    # No more fallbacks available
                    break

        # All attempts failed
        error_msg = f"All failover attempts exhausted. Last error: {last_error}"
        logger.error(error_msg)
        return error_msg, attempts[-1][0], attempts[-1][1]

    def get_status(self) -> Dict[str, Any]:
        """Get current status of all providers."""
        return {
            key: {
                "available": health.is_available,
                "success_rate": health.success_rate,
                "avg_response_time": health.avg_response_time,
                "cooldown_remaining": max(0, health.cooldown_until - time.time())
            }
            for key, health in self.providers.items()
        }


# Global failover manager instance
_failover_manager: Optional[FailoverManager] = None


def get_failover_manager() -> FailoverManager:
    """Get or create the global failover manager."""
    global _failover_manager
    if _failover_manager is None:
        _failover_manager = FailoverManager()

        # Register default providers and fallback chains
        _failover_manager.register_provider("claude_code", "claude_code", ["opus", "sonnet", "haiku"], priority=10)
        _failover_manager.register_provider("groq", "groq", ["llama-3.3-70b-versatile", "llama3-8b-8192", "mixtral-8x7b-32768"], priority=20)
        _failover_manager.register_provider("ollama", "ollama", ["deepseek-r1", "llama3", "mistral", "phi3"], priority=30)
        _failover_manager.register_provider("google_ai", "google_ai", ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"], priority=25)

        # Set fallback chains for premium models
        _failover_manager.set_fallback_chain("claude_code", "opus", [
            ("claude_code", "sonnet"),
            ("groq", "llama-3.3-70b-versatile"),
            ("google_ai", "gemini-1.5-pro"),
            ("ollama", "deepseek-r1")
        ])

        _failover_manager.set_fallback_chain("claude_code", "sonnet", [
            ("groq", "llama-3.3-70b-versatile"),
            ("google_ai", "gemini-1.5-flash"),
            ("ollama", "llama3"),
            ("claude_code", "haiku")
        ])

    return _failover_manager
