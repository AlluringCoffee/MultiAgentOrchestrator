"""
Mock LLM Provider for testing without external dependencies.
"""
import asyncio
from typing import Optional, List, Callable, Dict, Any
from providers import LLMProvider, ProviderType


class MockProvider(LLMProvider):
    """Mock provider for testing the workflow without real LLM calls."""
    
    provider_type = ProviderType.MOCK
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.delay = config.get('delay', 0.5)
    
    async def initialize(self) -> bool:
        self._initialized = True
        return True
    
    async def health_check(self) -> bool:
        return True
    
    async def generate(self, system_prompt: str, user_message: str, context: Optional[str] = None, on_thought: Optional[Callable] = None, model_override: Optional[str] = None) -> str:
        try:
            with open("mock_debug.log", "a") as f:
                f.write(f"MockProvider generate called. Prompt: {user_message[:20]}... on_thought present: {on_thought is not None}\n")
        except Exception:
            pass

        await asyncio.sleep(self.delay)
        
        # Generate role-appropriate mock responses
        prompt_lower = system_prompt.lower()
        
        # Simulate thinking if requested
        # Always emit thoughts if the callback is available to demonstrate the feature
        # This ensures the "Live Thought Stream" is active and visible to the user
        if on_thought:
            thoughts = [
                "Analyzing the request parameters...",
                "Checking knowledge base restrictions...",
                "Formulating response strategy...",
                "Drafting response content..."
            ]
            
            # If prompt implies a specific role, add flavor
            if 'adversary' in prompt_lower or 'critic' in prompt_lower:
                thoughts.insert(1, "Scanning for logical fallacies...")
            elif 'proposer' in prompt_lower or 'architect' in prompt_lower:
                thoughts.insert(1, "Consulting design patterns...")
                
            for thought in thoughts:
                on_thought(thought)
                await asyncio.sleep(0.5) # Delay for UI visualization
        
        if 'proposer' in prompt_lower or 'architect' in prompt_lower:
            return self._proposer_response(user_message)
        elif 'adversary' in prompt_lower or 'critic' in prompt_lower:
            return self._adversary_response(user_message, context or "")
        elif 'auditor' in prompt_lower or 'consensus' in prompt_lower:
            return self._auditor_response(context or "")
        
        return f"Mock response to: {user_message[:100]}..."
    
    def _proposer_response(self, user_message: str) -> str:
        return f"""**Proposal for: {user_message}**

## Architecture Overview
We should implement a modular architecture with:
1. **Core Module** - Central processing unit [1]
2. **API Layer** - RESTful interface with authentication [2]
3. **Data Store** - Persistent storage with caching [3]

This ensures scalability, security, and maintainability.

[1] Best Practices Guide 2024
[2] API Design Patterns
[3] Database Optimization"""

    def _adversary_response(self, user_message: str, proposal: str) -> str:
        if any(kw in user_message.lower() for kw in ['security', 'login', 'auth', 'password']):
            return """## Critical Analysis

**Concerns Identified:**
1. Security tier lacks specific encryption protocols
2. No mention of rate limiting or DDoS protection
3. Authentication flow unspecified - potential **Material Breach**

**Recommendation:** Address security concerns before proceeding."""
        
        return """## Critical Analysis

The proposal is fundamentally sound but lacks:
- Detailed implementation timeline
- Cost analysis
- Failure recovery procedures

**Overall:** Acceptable with noted improvements."""

    def _auditor_response(self, context: str) -> str:
        if 'material breach' in context.lower():
            return "REJECT: Critical concerns identified require resolution."
        return "APPROVE: Proposal meets agreement parameters."
