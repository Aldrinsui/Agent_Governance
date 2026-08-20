"""
Agent lifecycle state machine.

    ACTIVE --(NOTIFY)--------------------> ACTIVE          (no state change, just logged)
    ACTIVE --(REQUIRE_APPROVAL)----------> PAUSED
    ACTIVE --(BLOCK)----------------------> BLOCKED
    PAUSED --(approve)--------------------> ACTIVE
    PAUSED --(reject)---------------------> BLOCKED
    BLOCKED -> terminal in this system (manual admin reset is out of scope,
               see README "Limitations")

All transitions are centralized here so agent.state is never mutated
directly anywhere else in the codebase, and every transition writes exactly
one AuditLog row explaining what happened and why.
"""

from sqlalchemy.orm import Session

from app.models import Agent, AgentState, AuditLog, AuditEventType, ResponseAction, Finding


def _write_audit(
    db: Session,
    agent: Agent,
    event_type: AuditEventType,
    reason: str,
    actor: str = "system",
    from_state: str | None = None,
    to_state: str | None = None,
    finding_id=None,
):
    entry = AuditLog(
        agent_id=agent.id,
        finding_id=finding_id,
        event_type=event_type,
        from_state=from_state,
        to_state=to_state,
        actor=actor,
        reason=reason,
    )
    db.add(entry)
    return entry


def apply_response(db: Session, agent: Agent, finding: Finding) -> Agent:
    """Apply the response_action of a newly created finding to the agent's state."""
    prior_state = agent.state

    # Always record that a finding fired, regardless of whether state changes.
    _write_audit(
        db, agent, AuditEventType.FINDING_CREATED,
        reason=finding.explanation, finding_id=finding.id,
        from_state=prior_state.value, to_state=prior_state.value,
    )

    if finding.response_action == ResponseAction.NOTIFY:
        # Notify-only: no state transition, finding + audit entry is the record.
        return agent

    if finding.response_action == ResponseAction.REQUIRE_APPROVAL:
        if agent.state == AgentState.ACTIVE:
            agent.state = AgentState.PAUSED
            _write_audit(
                db, agent, AuditEventType.STATE_CHANGED,
                reason=f"Approval required: {finding.explanation}",
                from_state=prior_state.value, to_state=agent.state.value,
                finding_id=finding.id,
            )
            _write_audit(
                db, agent, AuditEventType.APPROVAL_REQUESTED,
                reason=finding.explanation, finding_id=finding.id,
                from_state=agent.state.value, to_state=agent.state.value,
            )
        return agent

    if finding.response_action == ResponseAction.BLOCK:
        if agent.state != AgentState.BLOCKED:
            agent.state = AgentState.BLOCKED
            _write_audit(
                db, agent, AuditEventType.STATE_CHANGED,
                reason=f"Blocked: {finding.explanation}",
                from_state=prior_state.value, to_state=agent.state.value,
                finding_id=finding.id,
            )
        return agent

    return agent


def approve(db: Session, agent: Agent, finding: Finding, actor: str, reason: str | None) -> Agent:
    if agent.state != AgentState.PAUSED:
        raise ValueError(f"Agent is not PAUSED (current state: {agent.state.value}); nothing to approve.")

    prior_state = agent.state
    agent.state = AgentState.ACTIVE
    _write_audit(
        db, agent, AuditEventType.APPROVED,
        reason=reason or f"Approved by {actor}",
        actor=actor, from_state=prior_state.value, to_state=agent.state.value,
        finding_id=finding.id,
    )
    _write_audit(
        db, agent, AuditEventType.STATE_CHANGED,
        reason=f"Resumed after approval by {actor}",
        actor=actor, from_state=prior_state.value, to_state=agent.state.value,
        finding_id=finding.id,
    )
    return agent


def reject(db: Session, agent: Agent, finding: Finding, actor: str, reason: str | None) -> Agent:
    if agent.state != AgentState.PAUSED:
        raise ValueError(f"Agent is not PAUSED (current state: {agent.state.value}); nothing to reject.")

    prior_state = agent.state
    agent.state = AgentState.BLOCKED
    _write_audit(
        db, agent, AuditEventType.REJECTED,
        reason=reason or f"Rejected by {actor}",
        actor=actor, from_state=prior_state.value, to_state=agent.state.value,
        finding_id=finding.id,
    )
    _write_audit(
        db, agent, AuditEventType.STATE_CHANGED,
        reason=f"Blocked after rejection by {actor}",
        actor=actor, from_state=prior_state.value, to_state=agent.state.value,
        finding_id=finding.id,
    )
    return agent
