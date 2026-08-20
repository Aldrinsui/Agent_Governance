import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, Finding, ResponseAction
from app.schemas import FindingOut, ApprovalDecision, AgentOut
from app.state_machine import approve as sm_approve, reject as sm_reject

router = APIRouter(tags=["findings"])


@router.get("/agents/{agent_id}/findings", response_model=list[FindingOut])
def list_findings(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(Finding)
        .filter(Finding.agent_id == agent_id)
        .order_by(Finding.created_at.desc())
        .all()
    )


@router.get("/findings/{finding_id}", response_model=FindingOut)
def get_finding(finding_id: uuid.UUID, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(404, "Finding not found")
    return finding


def _get_finding_and_agent(db: Session, finding_id: uuid.UUID) -> tuple[Finding, Agent]:
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(404, "Finding not found")
    if finding.response_action != ResponseAction.REQUIRE_APPROVAL:
        raise HTTPException(
            400,
            f"Finding {finding_id} has response_action="
            f"{finding.response_action.value}, not REQUIRE_APPROVAL; nothing to decide.",
        )
    agent = db.query(Agent).filter(Agent.id == finding.agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    return finding, agent


@router.post("/findings/{finding_id}/approve", response_model=AgentOut)
def approve_finding(finding_id: uuid.UUID, payload: ApprovalDecision, db: Session = Depends(get_db)):
    finding, agent = _get_finding_and_agent(db, finding_id)
    try:
        sm_approve(db, agent, finding, actor=payload.actor, reason=payload.reason)
    except ValueError as e:
        raise HTTPException(409, str(e))
    db.commit()
    db.refresh(agent)
    return agent


@router.post("/findings/{finding_id}/reject", response_model=AgentOut)
def reject_finding(finding_id: uuid.UUID, payload: ApprovalDecision, db: Session = Depends(get_db)):
    finding, agent = _get_finding_and_agent(db, finding_id)
    try:
        sm_reject(db, agent, finding, actor=payload.actor, reason=payload.reason)
    except ValueError as e:
        raise HTTPException(409, str(e))
    db.commit()
    db.refresh(agent)
    return agent
