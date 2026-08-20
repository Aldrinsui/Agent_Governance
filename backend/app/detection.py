"""
Detection engine.

Two independent detectors run on every ingested event:

1. Profile deviation detector -- did this single event use a tool / data
   source / action that is not in the agent's active profile?

2. Guardrail threshold detector -- has cumulative usage of a tracked metric
   (currently: event count per run, metric_name="calls_per_day") crossed a
   configured warning/critical/limit threshold?

Both detectors are pure functions over (db state, event) -> list[Finding],
kept separate from persistence/response-triggering (see routers/events.py)
so each is independently unit-testable.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Agent, AgentProfile, Event, Finding, FindingType, WarningLevel,
)
from app.policy import resolve_policy


def _make_finding(db: Session, agent: Agent, event: Event, finding_type: FindingType,
                   expected: str, actual: str, explanation: str) -> Finding:
    severity, response = resolve_policy(finding_type)
    finding = Finding(
        agent_id=agent.id,
        run_id=event.run_id,
        event_id=event.id,
        finding_type=finding_type,
        expected=expected,
        actual=actual,
        explanation=explanation,
        severity=severity,
        response_action=response,
    )
    db.add(finding)
    db.flush()  # assign finding.id before it's used by callers
    return finding


def detect_profile_deviation(db: Session, agent: Agent, profile: AgentProfile, event: Event) -> list[Finding]:
    """Compare a single event's tool/data_source/action against the active profile."""
    findings: list[Finding] = []

    allowed_tools = {t.tool_name for t in profile.allowed_tools}
    allowed_data = {d.data_source_name for d in profile.allowed_data_sources}
    allowed_actions = {a.action_name for a in profile.allowed_actions}

    if event.tool_used and event.tool_used not in allowed_tools:
        findings.append(_make_finding(
            db, agent, event, FindingType.UNAUTHORIZED_TOOL,
            expected=f"Tool used must be one of: {sorted(allowed_tools) or '[]'}",
            actual=f"Tool used: {event.tool_used}",
            explanation=(
                f"Agent attempted to use '{event.tool_used}', which is not "
                f"included in its active profile."
            ),
        ))

    if event.data_source_used and event.data_source_used not in allowed_data:
        findings.append(_make_finding(
            db, agent, event, FindingType.UNAUTHORIZED_DATA,
            expected=f"Data source accessed must be one of: {sorted(allowed_data) or '[]'}",
            actual=f"Data source accessed: {event.data_source_used}",
            explanation=(
                f"Agent attempted to access data source '{event.data_source_used}', "
                f"which is not included in its active profile."
            ),
        ))

    if event.action and event.action not in allowed_actions:
        findings.append(_make_finding(
            db, agent, event, FindingType.UNAUTHORIZED_ACTION,
            expected=f"Action performed must be one of: {sorted(allowed_actions) or '[]'}",
            actual=f"Action performed: {event.action}",
            explanation=(
                f"Agent performed action '{event.action}', which is not "
                f"included in its active profile."
            ),
        ))

    return findings


def detect_guardrail_breach(db: Session, agent: Agent, profile: AgentProfile, event: Event) -> list[Finding]:
    """
    Evaluate configured guardrails against cumulative usage for this run.

    Currently supports the "calls_per_day" metric, measured as event count
    within the current run_id (a reasonable, documented simplification of
    "per day" for a demo scenario -- see README Limitations).

    Threshold-crossing semantics: a given warning level is only emitted once
    per guardrail, tracked via guardrail.last_warning_level, so a long run
    doesn't spam duplicate WARNING findings on every subsequent event once
    a level has already been reached.
    """
    findings: list[Finding] = []

    for guardrail in profile.guardrails:
        if guardrail.metric_name != "calls_per_day":
            continue  # only metric implemented for this scope

        current_count = (
            db.query(func.count(Event.id))
            .filter(Event.agent_id == agent.id, Event.run_id == event.run_id)
            .scalar()
        )

        pct = (current_count / guardrail.max_value) * 100 if guardrail.max_value else 0

        new_level = guardrail.last_warning_level
        finding_type = None

        if pct >= 100 and guardrail.last_warning_level != WarningLevel.LIMIT:
            new_level = WarningLevel.LIMIT
            finding_type = FindingType.GUARDRAIL_LIMIT
        elif pct >= guardrail.critical_pct and guardrail.last_warning_level not in (
            WarningLevel.CRITICAL, WarningLevel.LIMIT
        ):
            new_level = WarningLevel.CRITICAL
            finding_type = FindingType.GUARDRAIL_CRITICAL
        elif pct >= guardrail.warning_pct and guardrail.last_warning_level == WarningLevel.NONE:
            new_level = WarningLevel.WARNING
            finding_type = FindingType.GUARDRAIL_WARNING

        if finding_type is not None:
            guardrail.last_warning_level = new_level
            db.add(guardrail)
            findings.append(_make_finding(
                db, agent, event, finding_type,
                expected=(
                    f"Usage of '{guardrail.metric_name}' should stay below "
                    f"{guardrail.max_value} per run."
                ),
                actual=f"Usage: {current_count}/{guardrail.max_value} ({pct:.0f}%)",
                explanation=(
                    f"Guardrail '{guardrail.metric_name}' reached {pct:.0f}% "
                    f"of its limit ({current_count}/{guardrail.max_value})."
                ),
            ))

    return findings
