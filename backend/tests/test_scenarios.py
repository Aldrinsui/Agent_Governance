"""
Exercises the four evaluation scenarios end-to-end through /demo/run-scenario,
matching exactly what a reviewer running the app locally would see.
"""


def test_scenario_a_normal_behavior_no_findings(client):
    r = client.post("/demo/run-scenario/A")
    assert r.status_code == 200
    body = r.json()
    assert body["final_state"] == "ACTIVE"
    for step in body["trace"]:
        assert step.get("findings", []) == []


def test_scenario_b_unauthorized_tool_blocks(client):
    r = client.post("/demo/run-scenario/B")
    assert r.status_code == 200
    body = r.json()
    assert body["final_state"] == "BLOCKED"
    all_findings = [f for step in body["trace"] for f in step.get("findings", [])]
    assert any("file_delete" in f for f in all_findings)


def test_scenario_c_guardrail_escalation(client):
    r = client.post("/demo/run-scenario/C")
    assert r.status_code == 200
    body = r.json()
    assert body["final_state"] == "BLOCKED"  # hits LIMIT at call 10
    all_findings_flat = [
        (step.get("findings", []), step.get("severities", []))
        for step in body["trace"] if step.get("findings")
    ]
    # Expect exactly 3 guardrail findings total across the whole run (warning, critical, limit)
    total_findings = sum(len(f) for f, _ in all_findings_flat)
    assert total_findings == 3


def test_scenario_d_human_approval_pauses_and_awaits_decision(client):
    r = client.post("/demo/run-scenario/D")
    assert r.status_code == 200
    body = r.json()
    assert body["state_after_deviation"] == "PAUSED"
    assert body["pending_finding_id"] is not None

    # Complete the loop: approve
    r2 = client.post(f"/findings/{body['pending_finding_id']}/approve",
                      json={"actor": "reviewer@flyyy.ai", "reason": "confirmed legitimate"})
    assert r2.status_code == 200
    assert r2.json()["state"] == "ACTIVE"

    # Audit trail should show the full sequence
    r3 = client.get(f"/agents/{body['agent_id']}/audit")
    audit_events = [e["event_type"] for e in r3.json()]
    assert "FINDING_CREATED" in audit_events
    assert "APPROVAL_REQUESTED" in audit_events
    assert "APPROVED" in audit_events
    assert "STATE_CHANGED" in audit_events
