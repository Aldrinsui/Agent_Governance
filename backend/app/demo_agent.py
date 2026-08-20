"""
Lightweight scripted "agent" used purely to generate realistic governance
events for the demo scenarios.

Design note: the assignment explicitly says an agent framework (LangGraph/
LangChain/etc.) should only be used "if it adds clear value." Here the
agent's own decision-making is not the thing being evaluated -- the
governance layer is. A framework would add dependency weight and
indirection without making the detection/response logic any more
demonstrable, so this is a deliberately simple scripted sequence of
tool/data/action calls that plays the role of an agent's behavior.

A "Customer Support Agent" persona is used, matching the example in the
assignment PDF (FAQ Search, Email Sender tools; FAQ Database; read/
send_email actions), with a deliberate escalation to file-delete to
demonstrate unauthorized-tool detection, and a payment-support twist
(unauthorized data-source access) to match the End-to-End Example in the
brief.
"""

import uuid
from dataclasses import dataclass


@dataclass
class ScriptedCall:
    tool_used: str | None = None
    data_source_used: str | None = None
    action: str | None = None
    metadata: dict | None = None

    def as_event_payload(self, agent_id, run_id):
        return {
            "agent_id": str(agent_id),
            "run_id": str(run_id),
            "tool_used": self.tool_used,
            "data_source_used": self.data_source_used,
            "action": self.action,
            "event_metadata": self.metadata or {},
        }


SUPPORT_AGENT_PROFILE = {
    "name": "Customer Support Agent v1",
    "allowed_tools": ["faq_search", "email_sender"],
    "allowed_data_sources": ["faq_database"],
    "allowed_actions": ["read", "send_email"],
    "guardrails": [
        {"metric_name": "calls_per_day", "max_value": 10, "warning_pct": 80, "critical_pct": 90},
    ],
}


def normal_run() -> list[ScriptedCall]:
    """Scenario A: entirely within the approved profile."""
    return [
        ScriptedCall(tool_used="faq_search", data_source_used="faq_database", action="read"),
        ScriptedCall(tool_used="email_sender", action="send_email"),
    ]


def unauthorized_tool_run() -> list[ScriptedCall]:
    """Scenario B: agent calls a tool never approved for it."""
    return [
        ScriptedCall(tool_used="faq_search", data_source_used="faq_database", action="read"),
        ScriptedCall(tool_used="file_delete", action="delete",
                     metadata={"note": "unexpected destructive tool call"}),
    ]


def guardrail_escalation_run(call_count: int = 10) -> list[ScriptedCall]:
    """Scenario C: agent stays within its profile but exceeds its call guardrail."""
    return [
        ScriptedCall(tool_used="faq_search", data_source_used="faq_database", action="read")
        for _ in range(call_count)
    ]


def unauthorized_data_access_run() -> list[ScriptedCall]:
    """
    Scenario D setup: mirrors the End-to-End Example in the brief -- a
    payment-support agent that accesses an unauthorized database, triggering
    REQUIRE_APPROVAL (medium severity, since it's an unauthorized *action*
    variant handled via data-source path) -> agent PAUSED, awaiting a human
    decision via the approval endpoint.
    """
    return [
        ScriptedCall(tool_used="faq_search", data_source_used="faq_database", action="read"),
        ScriptedCall(action="update_profile",
                     metadata={"note": "action outside approved scope, needs human sign-off"}),
    ]


def new_run_id() -> uuid.UUID:
    return uuid.uuid4()
