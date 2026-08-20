"""
Deterministic policy mapping: finding_type -> (severity, response_action).

This is intentionally a plain dict, not a rules-engine or ML model. The
assignment explicitly asks for explainable, deterministic severity/response
decisions -- a lookup table is the simplest artifact that is still fully
correct and trivially auditable ("why did this happen?" -> "look at this
one table").

If this needed to vary per-agent or per-org in the future, this table would
move into the DB (e.g. a `policy_rules` table keyed by profile_id), but that
is not required by the current scope.
"""

from app.models import FindingType, Severity, ResponseAction

POLICY_TABLE: dict[FindingType, tuple[Severity, ResponseAction]] = {
    FindingType.UNAUTHORIZED_TOOL: (Severity.HIGH, ResponseAction.BLOCK),
    FindingType.UNAUTHORIZED_DATA: (Severity.HIGH, ResponseAction.BLOCK),
    FindingType.UNAUTHORIZED_ACTION: (Severity.MEDIUM, ResponseAction.REQUIRE_APPROVAL),
    FindingType.GUARDRAIL_WARNING: (Severity.LOW, ResponseAction.NOTIFY),
    FindingType.GUARDRAIL_CRITICAL: (Severity.MEDIUM, ResponseAction.REQUIRE_APPROVAL),
    FindingType.GUARDRAIL_LIMIT: (Severity.HIGH, ResponseAction.BLOCK),
}


def resolve_policy(finding_type: FindingType) -> tuple[Severity, ResponseAction]:
    return POLICY_TABLE[finding_type]
