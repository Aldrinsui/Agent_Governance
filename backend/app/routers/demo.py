"""
Reproducible evaluation scenarios.

Each scenario provisions a fresh agent + profile, replays a scripted
sequence of agent calls through the *real* ingestion/detection/response
pipeline (the same code path as POST /events), and returns the full trace
(events, findings, agent state, audit log) so results are never fabricated
-- they are generated live from the running application.

For Scenario D (human approval), the scenario stops once the agent is
PAUSED and returns the finding_id; the caller then exercises
POST /findings/{id}/approve or /reject to complete the loop (mirrors real
usage -- a human decision genuinely needs to happen out of band).
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, AgentProfile, AllowedTool, AllowedDataSource, AllowedAction, Guardrail
from app.schemas import ProfileCreate, GuardrailIn
from app.routers.events import ingest_event
from app.schemas import EventCreate
from app.demo_agent import (
    SUPPORT_AGENT_PROFILE, normal_run, unauthorized_tool_run,
    guardrail_escalation_run, unauthorized_data_access_run, new_run_id,
)

router = APIRouter(prefix="/demo", tags=["demo"])


def _provision_agent(db: Session, name: str) -> Agent:
    agent = Agent(name=name)
    db.add(agent)
    db.flush()

    profile = AgentProfile(agent_id=agent.id, name=SUPPORT_AGENT_PROFILE["name"], is_active=True)
    db.add(profile)
    db.flush()

    for tool in SUPPORT_AGENT_PROFILE["allowed_tools"]:
        db.add(AllowedTool(profile_id=profile.id, tool_name=tool))
    for ds in SUPPORT_AGENT_PROFILE["allowed_data_sources"]:
        db.add(AllowedDataSource(profile_id=profile.id, data_source_name=ds))
    for action in SUPPORT_AGENT_PROFILE["allowed_actions"]:
        db.add(AllowedAction(profile_id=profile.id, action_name=action))
    for g in SUPPORT_AGENT_PROFILE["guardrails"]:
        db.add(Guardrail(profile_id=profile.id, **g))

    agent.active_profile_id = profile.id
    db.commit()
    db.refresh(agent)
    return agent


def _replay(db: Session, agent: Agent, calls, run_id, auto_approve_critical: bool = False) -> list[dict]:
    """
    Replay scripted calls through the real ingestion pipeline.

    auto_approve_critical: when True (used by Scenario C, which is meant to
    demonstrate the *full* WARNING -> CRITICAL -> LIMIT escalation in one
    run), a REQUIRE_APPROVAL finding auto-approves as "ops@flyyy.ai" so the
    scripted run can continue to the LIMIT threshold. This mirrors a real
    operator clicking Approve in the UI -- it is not a bypass of the state
    machine, just a stand-in for the human step so the scenario is fully
    reproducible via a single command. Scenario D deliberately does NOT use
    this, because its entire point is to stop and show the pending
    approval.
    """
    from app.state_machine import approve as sm_approve

    trace = []
    for call in calls:
        db.refresh(agent)
        if agent.state.value == "PAUSED" and auto_approve_critical:
            from app.models import Finding, ResponseAction
            pending = (
                db.query(Finding)
                .filter(Finding.agent_id == agent.id, Finding.response_action == ResponseAction.REQUIRE_APPROVAL)
                .order_by(Finding.created_at.desc())
                .first()
            )
            if pending:
                sm_approve(db, agent, pending, actor="ops@flyyy.ai",
                           reason="Auto-approved for scenario replay")
                db.commit()
                db.refresh(agent)
                trace.append({"auto_approved_finding": str(pending.id), "actor": "ops@flyyy.ai"})

        if agent.state.value != "ACTIVE":
            trace.append({"skipped": True, "reason": f"agent state is {agent.state.value}"})
            break
        payload = EventCreate(**call.as_event_payload(agent.id, run_id))
        try:
            result = ingest_event(payload, db)
            trace.append({
                "tool_used": call.tool_used,
                "data_source_used": call.data_source_used,
                "action": call.action,
                "findings": [f.explanation for f in result.findings],
                "severities": [f.severity.value for f in result.findings],
                "responses": [f.response_action.value for f in result.findings],
                "agent_state_after": result.agent_state.value,
            })
        except HTTPException as e:
            trace.append({"blocked_before_call": True, "detail": e.detail})
            break
    return trace


@router.post("/run-scenario/{name}")
def run_scenario(name: str, db: Session = Depends(get_db)):
    if name == "A":
        agent = _provision_agent(db, "Support Agent - Scenario A (Normal)")
        run_id = new_run_id()
        trace = _replay(db, agent, normal_run(), run_id)
        db.refresh(agent)
        return {"scenario": "A - Normal behavior", "agent_id": str(agent.id),
                "final_state": agent.state.value, "trace": trace}

    if name == "B":
        agent = _provision_agent(db, "Support Agent - Scenario B (Unauthorized tool)")
        run_id = new_run_id()
        trace = _replay(db, agent, unauthorized_tool_run(), run_id)
        db.refresh(agent)
        return {"scenario": "B - Unauthorized tool", "agent_id": str(agent.id),
                "final_state": agent.state.value, "trace": trace}

    if name == "C":
        agent = _provision_agent(db, "Support Agent - Scenario C (Guardrail escalation)")
        run_id = new_run_id()
        trace = _replay(db, agent, guardrail_escalation_run(10), run_id, auto_approve_critical=True)
        db.refresh(agent)
        return {"scenario": "C - Guardrail escalation", "agent_id": str(agent.id),
                "final_state": agent.state.value, "trace": trace}

    if name == "D":
        agent = _provision_agent(db, "Support Agent - Scenario D (Human approval)")
        run_id = new_run_id()
        trace = _replay(db, agent, unauthorized_data_access_run(), run_id)
        db.refresh(agent)
        pending_finding_id = None
        if agent.state.value == "PAUSED":
            from app.models import Finding, ResponseAction
            f = (
                db.query(Finding)
                .filter(Finding.agent_id == agent.id, Finding.response_action == ResponseAction.REQUIRE_APPROVAL)
                .order_by(Finding.created_at.desc())
                .first()
            )
            pending_finding_id = str(f.id) if f else None
        return {
            "scenario": "D - Human approval",
            "agent_id": str(agent.id),
            "state_after_deviation": agent.state.value,
            "pending_finding_id": pending_finding_id,
            "trace": trace,
            "next_step": (
                f"POST /findings/{pending_finding_id}/approve or /reject to complete the loop"
                if pending_finding_id else "No pending approval was generated."
            ),
        }

    raise HTTPException(404, "Unknown scenario. Use one of: A, B, C, D")
