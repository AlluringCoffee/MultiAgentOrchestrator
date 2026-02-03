"""
Consensus Gate - Validates proposals against configurable criteria.
"""
import re
import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from core.models import ConsensusDecision, ConsensusCriteria

logger = logging.getLogger(__name__)


class ConsensusGate:
    """
    The ConsensusGate acts as the 'Adjudication' layer.
    It ensures that the output from an agent meets specific 'Agreement Parameters'
    before allowing the process to move to the next stage in the chain.
    """

    def __init__(self, auditor_persona: Dict[str, Any], criteria: Optional[ConsensusCriteria] = None):
        self.auditor = auditor_persona
        self.criteria = criteria or ConsensusCriteria()
        self._custom_validators: Dict[str, Callable[[str], bool]] = {}
        logger.info(f"ConsensusGate initialized with criteria: {self.criteria.model_dump()}")

    def register_validator(self, name: str, validator: Callable[[str], bool]):
        """Register a custom validation function."""
        self._custom_validators[name] = validator
        logger.debug(f"Registered custom validator: {name}")

    async def validate(
        self, 
        proposal: str, 
        feedback: str,
        on_status: Optional[Callable[[str], None]] = None
    ) -> ConsensusDecision:
        """
        Validates the proposal against the criteria and the adversary's feedback.
        
        Args:
            proposal: The output from the Proposer (Agent A).
            feedback: The output from the Adversary (Agent B).
            on_status: Callback for status updates.

        Returns:
            ConsensusDecision with status, checks, and reasoning.
        """
        if on_status:
            on_status("Running validation checks...")
        
        results: Dict[str, bool] = {}
        
        # Run configured checks
        if self.criteria.brevity:
            results['brevity'] = self._check_brevity(proposal)
            logger.debug(f"Brevity check: {results['brevity']}")
        
        if self.criteria.citations:
            results['citations'] = self._check_citations(proposal)
            logger.debug(f"Citations check: {results['citations']}")
        
        # Run custom validators
        for name in self.criteria.custom_checks:
            if name in self._custom_validators:
                results[name] = self._custom_validators[name](proposal)
                logger.debug(f"Custom check '{name}': {results[name]}")
        
        # Consult auditor (async)
        if on_status:
            on_status(f"{self.auditor['name']} is reviewing...")
        
        auditor_decision = await self._consult_auditor(proposal, feedback)
        
        # Combine hard checks and Auditor judgment
        all_passed = all(results.values()) and auditor_decision['approved']
        
        decision = ConsensusDecision(
            status="Green Light" if all_passed else "Red Light",
            checks=results,
            auditor_feedback=auditor_decision['reasoning']
        )
        
        logger.info(f"Consensus decision: {decision.status}")
        return decision

    def _check_brevity(self, text: str) -> bool:
        """Check if text is within word limit."""
        word_count = len(text.split())
        passed = word_count <= self.criteria.max_words
        logger.debug(f"Word count: {word_count}/{self.criteria.max_words}")
        return passed

    def _check_citations(self, text: str) -> bool:
        """Check for the presence of citation markers."""
        citation_pattern = r'\[\d+\]|\(Source: .+\)|http[s]?://|References?:'
        return bool(re.search(citation_pattern, text))

    async def _consult_auditor(self, proposal: str, feedback: str) -> Dict[str, Any]:
        """
        Simulates (or performs) the LLM call to the Auditor persona.
        """
        logger.info(f"{self.auditor['name']} reviewing proposal against feedback...")
        
        # Simulate async processing
        await asyncio.sleep(0.3)
        
        # Logic simulation: Material Breach detection
        breach_keywords = ["material breach", "critical flaw", "security risk", "reject"]
        feedback_lower = feedback.lower()
        
        has_breach = any(kw in feedback_lower for kw in breach_keywords)
        
        if has_breach:
            return {
                "approved": False,
                "reasoning": "The Critic identified critical concerns. Additional review required before proceeding."
            }
        
        return {
            "approved": True,
            "reasoning": "The proposal adequately addresses the prompt and withstands critique. Consensus achieved."
        }
