
def _option(client, base_amount: float, index: int = 1) -> dict:
    assert client.post("/budget", json={"base_amount": base_amount}).status_code == 200
    cap = client.post("/captures", json={}).json()
    client.get(f"/looks/{cap['look_id']}")
    piece_id = client.get(f"/looks/{cap['look_id']}/gaps").json()["missing"][0]
    return client.get(f"/gaps/{piece_id}/options").json()["options"][index]


def test_tight_verdict_uses_configured_threshold(client):
    option = _option(client, 55.0)

    response = client.post("/decisions/evaluate", json={"option_id": option["id"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "tight"
    assert payload["available_after"] == 5.01
    assert {issue["type"] for issue in payload["issues"]} == {"buy", "wait", "recreate"}


def test_over_verdict_exposes_phase_and_substitution_at_parity(client):
    option = _option(client, 40.0)

    response = client.post("/decisions/evaluate", json={"option_id": option["id"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "over"
    assert payload["available_after"] == -9.99
    issue_types = [issue["type"] for issue in payload["issues"]]
    assert issue_types[:2] == ["phase", "substitute"]
    assert set(issue_types) == {"phase", "substitute", "wait", "recreate"}
    phase = next(issue for issue in payload["issues"] if issue["type"] == "phase")
    substitute = next(issue for issue in payload["issues"] if issue["type"] == "substitute")
    assert phase["plan"]["strategy"] == "stub"
    assert substitute["bundle"] == {"strategy": "stub", "price": 92.0}
