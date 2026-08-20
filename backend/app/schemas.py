import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.models import (
    AgentState, FindingType, Severity, ResponseAction, AuditEventType
)


# ---------- Agents ----------

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1)


class AgentOut(BaseModel):
    id: uuid.UUID
    name: str
    state: AgentState
    active_profile_id: Optional[uuid.UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Profiles ----------

class GuardrailIn(BaseModel):
    metric_name: str
    max_value: int = Field(..., gt=0)
    warning_pct: int = Field(80, ge=1, le=100)
    critical_pct: int = Field(90, ge=1, le=100)


class ProfileCreate(BaseModel):
    name: str
    allowed_tools: list[str] = []
    allowed_data_sources: list[str] = []
    allowed_actions: list[str] = []
    guardrails: list[GuardrailIn] = []


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    allowed_tools: Optional[list[str]] = None
    allowed_data_sources: Optional[list[str]] = None
    allowed_actions: Optional[list[str]] = None
    guardrails: Optional[list[GuardrailIn]] = None


class GuardrailOut(BaseModel):
    metric_name: str
    max_value: int
    warning_pct: int
    critical_pct: int
    last_warning_level: str

    class Config:
        from_attributes = True


class ProfileOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    name: str
    is_active: bool
    allowed_tools: list[str]
    allowed_data_sources: list[str]
    allowed_actions: list[str]
    guardrails: list[GuardrailOut]

    class Config:
        from_attributes = True


# ---------- Events ----------

class EventCreate(BaseModel):
    agent_id: uuid.UUID
    run_id: uuid.UUID
    tool_used: Optional[str] = None
    data_source_used: Optional[str] = None
    action: Optional[str] = None
    event_metadata: dict = {}


class EventOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    run_id: uuid.UUID
    tool_used: Optional[str]
    data_source_used: Optional[str]
    action: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class EventIngestResult(BaseModel):
    event: EventOut
    findings: list["FindingOut"]
    agent_state: AgentState


# ---------- Findings ----------

class FindingOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    run_id: uuid.UUID
    event_id: Optional[uuid.UUID]
    finding_type: FindingType
    expected: str
    actual: str
    explanation: str
    severity: Severity
    response_action: ResponseAction
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalDecision(BaseModel):
    actor: str = Field(..., min_length=1, description="Identity of the approver")
    reason: Optional[str] = None


# ---------- Audit ----------

class AuditLogOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    finding_id: Optional[uuid.UUID]
    event_type: AuditEventType
    from_state: Optional[str]
    to_state: Optional[str]
    actor: str
    reason: str
    created_at: datetime

    class Config:
        from_attributes = True


EventIngestResult.model_rebuild()
