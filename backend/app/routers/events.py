from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, AgentProfile, Event, AgentState
from app.schemas import EventCreate, EventIngestResult
from app.detection import detect_profile_deviation, detect_guardrail_breach
from app.state_machine import apply_response

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventIngestResult, status_code=201)
def ingest_event(payload: EventCreate, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == payload.agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")

    if agent.state != AgentState.ACTIVE:
        raise HTTPException(
            409,
            f"Agent is {agent.state.value} and cannot process new events "
            f"until it is ACTIVE again (approve/reject the pending finding first).",
        )

    profile = (
        db.query(AgentProfile)
        .filter(AgentProfile.agent_id == agent.id, AgentProfile.is_active.is_(True))
        .first()
    )
    if not profile:
        raise HTTPException(400, "Agent has no active profile; cannot evaluate behavior.")

    event = Event(
        agent_id=agent.id,
        run_id=payload.run_id,
        tool_used=payload.tool_used,
        data_source_used=payload.data_source_used,
        action=payload.action,
        event_metadata=payload.event_metadata,
    )
    db.add(event)
    db.flush()  # event.id available for findings before commit

    findings = []
    findings += detect_profile_deviation(db, agent, profile, event)
    findings += detect_guardrail_breach(db, agent, profile, event)

    # Apply responses in order; if an earlier finding already blocked the
    # agent, later findings in the same batch still get recorded (evidence
    # is never dropped) but won't further "un-block" it, since apply_response
    # only escalates state, never de-escalates.
    for finding in findings:
        apply_response(db, agent, finding)

    db.commit()
    db.refresh(event)
    db.refresh(agent)
    for f in findings:
        db.refresh(f)

    return EventIngestResult(event=event, findings=findings, agent_state=agent.state)
