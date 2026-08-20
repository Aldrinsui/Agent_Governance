def test_normal_run_produces_no_findings(client):
    r = client.post("/agents", json={"name": "Detector Test - Normal"})
    agent = r.json()
    client.post(f"/agents/{agent['id']}/profiles", json={
        "name": "profile", "allowed_tools": ["faq_search"],
        "allowed_data_sources": ["faq_database"], "allowed_actions": ["read"],
        "guardrails": [],
    })
    r = client.post("/events", json={
        "agent_id": agent["id"], "run_id": "11111111-1111-1111-1111-111111111111",
        "tool_used": "faq_search", "data_source_used": "faq_database", "action": "read",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["findings"] == []
    assert body["agent_state"] == "ACTIVE"


def test_unauthorized_tool_blocks_agent(client):
    r = client.post("/agents", json={"name": "Detector Test - Unauthorized Tool"})
    agent = r.json()
    client.post(f"/agents/{agent['id']}/profiles", json={
        "name": "profile", "allowed_tools": ["faq_search"],
        "allowed_data_sources": ["faq_database"], "allowed_actions": ["read"],
        "guardrails": [],
    })
    r = client.post("/events", json={
        "agent_id": agent["id"], "run_id": "22222222-2222-2222-2222-222222222222",
        "tool_used": "file_delete",
    })
    body = r.json()
    # only tool_used is set (and unauthorized) here, so exactly one finding
    # should fire -- confirms detectors don't cross-contaminate on unset fields
    assert len(body["findings"]) == 1
    finding = body["findings"][0]
    assert finding["finding_type"] == "UNAUTHORIZED_TOOL"
    assert finding["severity"] == "HIGH"
    assert finding["response_action"] == "BLOCK"
    assert body["agent_state"] == "BLOCKED"
    assert "file_delete" in finding["explanation"]


def test_unauthorized_action_pauses_agent_for_approval(client):
    r = client.post("/agents", json={"name": "Detector Test - Unauthorized Action"})
    agent = r.json()
    client.post(f"/agents/{agent['id']}/profiles", json={
        "name": "profile", "allowed_tools": ["faq_search"],
        "allowed_data_sources": ["faq_database"], "allowed_actions": ["read"],
        "guardrails": [],
    })
    r = client.post("/events", json={
        "agent_id": agent["id"], "run_id": "33333333-3333-3333-3333-333333333333",
        "action": "update_profile",
    })
    body = r.json()
    finding = body["findings"][0]
    assert finding["finding_type"] == "UNAUTHORIZED_ACTION"
    assert finding["response_action"] == "REQUIRE_APPROVAL"
    assert body["agent_state"] == "PAUSED"

    # blocked from further events until resolved
    r2 = client.post("/events", json={
        "agent_id": agent["id"], "run_id": "33333333-3333-3333-3333-333333333333",
        "tool_used": "faq_search", "action": "read",
    })
    assert r2.status_code == 409

    # approve -> resumes to ACTIVE
    r3 = client.post(f"/findings/{finding['id']}/approve", json={"actor": "manager@flyyy.ai"})
    assert r3.status_code == 200
    assert r3.json()["state"] == "ACTIVE"


def test_reject_blocks_agent(client):
    r = client.post("/agents", json={"name": "Detector Test - Reject Path"})
    agent = r.json()
    client.post(f"/agents/{agent['id']}/profiles", json={
        "name": "profile", "allowed_tools": ["faq_search"],
        "allowed_data_sources": ["faq_database"], "allowed_actions": ["read"],
        "guardrails": [],
    })
    r = client.post("/events", json={
        "agent_id": agent["id"], "run_id": "44444444-4444-4444-4444-444444444444",
        "action": "update_profile",
    })
    finding = r.json()["findings"][0]
    r3 = client.post(f"/findings/{finding['id']}/reject", json={"actor": "manager@flyyy.ai", "reason": "not approved"})
    assert r3.status_code == 200
    assert r3.json()["state"] == "BLOCKED"
