import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, ForeignKey, DateTime, Enum as SAEnum, JSON, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR

from app.database import Base


# --- Portable UUID type: native uuid on Postgres, CHAR(36) on SQLite (used in tests) ---
class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(str(value))


def new_uuid():
    return uuid.uuid4()


def utcnow():
    return datetime.now(timezone.utc)


# ---------- Enums ----------

class AgentState(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"


class FindingType(str, enum.Enum):
    UNAUTHORIZED_TOOL = "UNAUTHORIZED_TOOL"
    UNAUTHORIZED_DATA = "UNAUTHORIZED_DATA"
    UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"
    GUARDRAIL_WARNING = "GUARDRAIL_WARNING"
    GUARDRAIL_CRITICAL = "GUARDRAIL_CRITICAL"
    GUARDRAIL_LIMIT = "GUARDRAIL_LIMIT"


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ResponseAction(str, enum.Enum):
    NOTIFY = "NOTIFY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"


class WarningLevel(str, enum.Enum):
    NONE = "NONE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    LIMIT = "LIMIT"


class AuditEventType(str, enum.Enum):
    FINDING_CREATED = "FINDING_CREATED"
    STATE_CHANGED = "STATE_CHANGED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ---------- Tables ----------

class Agent(Base):
    __tablename__ = "agents"

    id = Column(GUID(), primary_key=True, default=new_uuid)
    name = Column(String, nullable=False)
    state = Column(SAEnum(AgentState), nullable=False, default=AgentState.ACTIVE)
    # Soft reference (no FK constraint) to avoid a circular FK dependency
    # between agents <-> agent_profiles. The single source of truth for
    # "which profile is active" is AgentProfile.is_active; this column is a
    # denormalized pointer kept in sync by the profile-creation endpoint for
    # fast lookups, not a constraint boundary.
    active_profile_id = Column(GUID(), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    profiles = relationship(
        "AgentProfile", back_populates="agent", foreign_keys="AgentProfile.agent_id"
    )
    events = relationship("Event", back_populates="agent")
    findings = relationship("Finding", back_populates="agent")
    audit_logs = relationship("AuditLog", back_populates="agent")


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id = Column(GUID(), primary_key=True, default=new_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    agent = relationship("Agent", back_populates="profiles", foreign_keys=[agent_id])
    allowed_tools = relationship(
        "AllowedTool", back_populates="profile", cascade="all, delete-orphan"
    )
    allowed_data_sources = relationship(
        "AllowedDataSource", back_populates="profile", cascade="all, delete-orphan"
    )
    allowed_actions = relationship(
        "AllowedAction", back_populates="profile", cascade="all, delete-orphan"
    )
    guardrails = relationship(
        "Guardrail", back_populates="profile", cascade="all, delete-orphan"
    )


class AllowedTool(Base):
    __tablename__ = "allowed_tools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(GUID(), ForeignKey("agent_profiles.id"), nullable=False)
    tool_name = Column(String, nullable=False)

    profile = relationship("AgentProfile", back_populates="allowed_tools")


class AllowedDataSource(Base):
    __tablename__ = "allowed_data_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(GUID(), ForeignKey("agent_profiles.id"), nullable=False)
    data_source_name = Column(String, nullable=False)

    profile = relationship("AgentProfile", back_populates="allowed_data_sources")


class AllowedAction(Base):
    __tablename__ = "allowed_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(GUID(), ForeignKey("agent_profiles.id"), nullable=False)
    action_name = Column(String, nullable=False)

    profile = relationship("AgentProfile", back_populates="allowed_actions")


class Guardrail(Base):
    __tablename__ = "guardrails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(GUID(), ForeignKey("agent_profiles.id"), nullable=False)
    metric_name = Column(String, nullable=False)  # e.g. "calls_per_day"
    max_value = Column(Integer, nullable=False)
    warning_pct = Column(Integer, default=80)
    critical_pct = Column(Integer, default=90)
    last_warning_level = Column(SAEnum(WarningLevel), default=WarningLevel.NONE)

    profile = relationship("AgentProfile", back_populates="guardrails")


class Event(Base):
    __tablename__ = "events"

    id = Column(GUID(), primary_key=True, default=new_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    run_id = Column(GUID(), nullable=False)
    tool_used = Column(String, nullable=True)
    data_source_used = Column(String, nullable=True)
    action = Column(String, nullable=True)
    event_metadata = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), default=utcnow)

    agent = relationship("Agent", back_populates="events")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(GUID(), primary_key=True, default=new_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    run_id = Column(GUID(), nullable=False)
    event_id = Column(GUID(), ForeignKey("events.id"), nullable=True)
    finding_type = Column(SAEnum(FindingType), nullable=False)
    expected = Column(String, nullable=False)
    actual = Column(String, nullable=False)
    explanation = Column(String, nullable=False)
    severity = Column(SAEnum(Severity), nullable=False)
    response_action = Column(SAEnum(ResponseAction), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    agent = relationship("Agent", back_populates="findings")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(GUID(), primary_key=True, default=new_uuid)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    finding_id = Column(GUID(), ForeignKey("findings.id"), nullable=True)
    event_type = Column(SAEnum(AuditEventType), nullable=False)
    from_state = Column(String, nullable=True)
    to_state = Column(String, nullable=True)
    actor = Column(String, nullable=False, default="system")
    reason = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    agent = relationship("Agent", back_populates="audit_logs")
