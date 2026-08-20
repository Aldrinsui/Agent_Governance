import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Agent, AgentProfile, AllowedTool, AllowedDataSource, AllowedAction, Guardrail
)
from app.schemas import ProfileCreate, ProfileUpdate, ProfileOut

router = APIRouter(tags=["profiles"])


def _serialize(profile: AgentProfile) -> dict:
    return {
        "id": profile.id,
        "agent_id": profile.agent_id,
        "name": profile.name,
        "is_active": profile.is_active,
        "allowed_tools": [t.tool_name for t in profile.allowed_tools],
        "allowed_data_sources": [d.data_source_name for d in profile.allowed_data_sources],
        "allowed_actions": [a.action_name for a in profile.allowed_actions],
        "guardrails": [
            {
                "metric_name": g.metric_name,
                "max_value": g.max_value,
                "warning_pct": g.warning_pct,
                "critical_pct": g.critical_pct,
                "last_warning_level": g.last_warning_level.value,
            }
            for g in profile.guardrails
        ],
    }


@router.post("/agents/{agent_id}/profiles", response_model=ProfileOut, status_code=201)
def create_profile(agent_id: uuid.UUID, payload: ProfileCreate, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")

    # Deactivate any existing active profile -- only one active profile per agent.
    db.query(AgentProfile).filter(
        AgentProfile.agent_id == agent_id, AgentProfile.is_active.is_(True)
    ).update({"is_active": False})

    profile = AgentProfile(agent_id=agent_id, name=payload.name, is_active=True)
    db.add(profile)
    db.flush()

    for tool in payload.allowed_tools:
        db.add(AllowedTool(profile_id=profile.id, tool_name=tool))
    for ds in payload.allowed_data_sources:
        db.add(AllowedDataSource(profile_id=profile.id, data_source_name=ds))
    for action in payload.allowed_actions:
        db.add(AllowedAction(profile_id=profile.id, action_name=action))
    for g in payload.guardrails:
        db.add(Guardrail(
            profile_id=profile.id, metric_name=g.metric_name, max_value=g.max_value,
            warning_pct=g.warning_pct, critical_pct=g.critical_pct,
        ))

    agent.active_profile_id = profile.id
    db.commit()
    db.refresh(profile)
    return _serialize(profile)


@router.get("/agents/{agent_id}/profiles/active", response_model=ProfileOut)
def get_active_profile(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    profile = (
        db.query(AgentProfile)
        .options(joinedload(AgentProfile.allowed_tools),
                 joinedload(AgentProfile.allowed_data_sources),
                 joinedload(AgentProfile.allowed_actions),
                 joinedload(AgentProfile.guardrails))
        .filter(AgentProfile.agent_id == agent_id, AgentProfile.is_active.is_(True))
        .first()
    )
    if not profile:
        raise HTTPException(404, "No active profile for this agent")
    return _serialize(profile)


@router.patch("/profiles/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: uuid.UUID, payload: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(404, "Profile not found")

    if payload.name is not None:
        profile.name = payload.name

    if payload.allowed_tools is not None:
        db.query(AllowedTool).filter(AllowedTool.profile_id == profile_id).delete()
        for tool in payload.allowed_tools:
            db.add(AllowedTool(profile_id=profile_id, tool_name=tool))

    if payload.allowed_data_sources is not None:
        db.query(AllowedDataSource).filter(AllowedDataSource.profile_id == profile_id).delete()
        for ds in payload.allowed_data_sources:
            db.add(AllowedDataSource(profile_id=profile_id, data_source_name=ds))

    if payload.allowed_actions is not None:
        db.query(AllowedAction).filter(AllowedAction.profile_id == profile_id).delete()
        for action in payload.allowed_actions:
            db.add(AllowedAction(profile_id=profile_id, action_name=action))

    if payload.guardrails is not None:
        db.query(Guardrail).filter(Guardrail.profile_id == profile_id).delete()
        for g in payload.guardrails:
            db.add(Guardrail(
                profile_id=profile_id, metric_name=g.metric_name, max_value=g.max_value,
                warning_pct=g.warning_pct, critical_pct=g.critical_pct,
            ))

    db.commit()
    db.refresh(profile)
    return _serialize(profile)
