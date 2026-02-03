"""
Pydantic models for configuration validation and API schemas.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class AgentRole(str, Enum):
    """Roles an agent can take in the orchestration."""
    PROPOSER = "Proposer"
    ADVERSARY = "Adversary"
    CONSENSUS_GATE = "ConsensusGate"


class PersonaConfig(BaseModel):
    """Schema for a single agent persona in the registry."""
    name: str = Field(..., description="Display name of the agent")
    role: AgentRole = Field(..., description="Role in the orchestration flow")
    model: str = Field(default="gpt-4o", description="LLM model identifier")
    system_prompt: str = Field(..., description="System prompt for the agent")
    
    class Config:
        use_enum_values = True


class ConsensusCriteria(BaseModel):
    """Configurable criteria for the consensus gate."""
    brevity: bool = Field(default=True, description="Check word count limit")
    max_words: int = Field(default=500, description="Max words for brevity check")
    citations: bool = Field(default=True, description="Require citation markers")
    custom_checks: List[str] = Field(default_factory=list, description="Custom check names")


class RegistryConfig(BaseModel):
    """Full registry configuration schema."""
    architect: PersonaConfig
    critic: PersonaConfig
    auditor: PersonaConfig
    consensus_criteria: ConsensusCriteria = Field(default_factory=ConsensusCriteria)


class MissionRequest(BaseModel):
    """API request schema for submitting a mission."""
    prompt: str = Field(..., min_length=1, description="The mission prompt")


class AgentStatus(str, Enum):
    """Status of an agent during mission execution."""
    IDLE = "idle"
    WORKING = "working"
    COMPLETE = "complete"
    ERROR = "error"


class LogEntry(BaseModel):
    """A single log entry from the orchestration."""
    timestamp: datetime = Field(default_factory=datetime.now)
    speaker: str
    message: str
    level: str = Field(default="info")


class ConsensusDecision(BaseModel):
    """Result from the consensus gate validation."""
    status: str = Field(..., description="Green Light or Red Light")
    checks: Dict[str, bool] = Field(default_factory=dict)
    auditor_feedback: str


class MissionResult(BaseModel):
    """Complete result of a mission execution."""
    mission_id: str
    prompt: str
    proposal: str
    feedback: str
    decision: ConsensusDecision
    success: bool
    logs: List[LogEntry] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None


class WebSocketMessage(BaseModel):
    """Message format for WebSocket communication."""
    type: str = Field(..., description="Message type: log, status, result")
    data: Dict[str, Any]
