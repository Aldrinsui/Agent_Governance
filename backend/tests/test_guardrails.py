import uuid


def test_guardrail_thresholds_fire_once_each(client):
    r = client.post("/agents", json={"name": "Guardrail Test"})
    agent = r.json()
    client.post(f"/agents/{agent['id']}/profiles", json={
        "name": "profile", "allowed_tools": ["faq_search"],
        "allowed_data_sources": ["faq_database"], "allowed_actions": ["read"],
        "guardrails": [{"metric_name": "calls_per_day", "max_value": 10,
                         "warning_pct": 80, "critical_pct": 90}],
    })
    run_id = str(uuid.uuid4())

    warning_events, critical_events, limit_events = [], [], []
    for i in range(1, 11):
        r = client.post("/events", json={
            "agent_id": agent["id"], "run_id": run_id,
            "tool_used": "faq_search", "data_source_used": "faq_database", "action": "read",
        })
        body = r.json()
        for f in body["findings"]:
            if f["finding_type"] == "GUARDRAIL_WARNING":
                warning_events.append(i)
            elif f["finding_type"] == "GUARDRAIL_CRITICAL":
                critical_events.append(i)
                # CRITICAL is policy-mapped to REQUIRE_APPROVAL, which pauses
                # the agent -- a human must approve before it can continue,
                # which is the whole point of a "critical" warning zone.
                assert body["agent_state"] == "PAUSED"
                client.post(f"/findings/{f['id']}/approve", json={"actor": "ops@flyyy.ai"})
            elif f["finding_type"] == "GUARDRAIL_LIMIT":
                limit_events.append(i)

    # 8/10 = 80% -> WARNING fires exactly once, at call 8 (NOTIFY only, no state change)
    assert warning_events == [8]
    # 9/10 = 90% -> CRITICAL fires exactly once, at call 9 (pauses, then approved)
    assert critical_events == [9]
    # 10/10 = 100% -> LIMIT fires exactly once, at call 10, and blocks the agent
    assert limit_events == [10]

    final_agent = client.get(f"/agents/{agent['id']}").json()
    assert final_agent["state"] == "BLOCKED"
