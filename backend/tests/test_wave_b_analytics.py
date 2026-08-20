from app.analytics import emitter


def _event(events, name, index=0):
    matches = [e for e in events if e[0] == name]
    return matches[index]


def test_capture_index_regime_and_owned_pct_compound(client, monkeypatch):
    events: list[tuple[str, str, dict]] = []

    def collect(event: str, user_id: str, **props: object) -> None:
        events.append((event, user_id, props))

    monkeypatch.setattr(emitter, "emit", collect)

    assert client.post("/budget", json={"base_amount": 100}).status_code == 200

    first = client.post("/captures", json={}).json()
    first_look = client.get(f"/looks/{first['look_id']}").json()
    assert first_look["score_look"] == 0

    first_capture_event = _event(events, emitter.CAPTURE_STARTED)
    assert first_capture_event[2]["capture_index"] == 1
    assert first_capture_event[2]["regime"] == "j0"
    assert first_capture_event[2]["wardrobe_count"] == 0

    first_match = _event(events, emitter.MATCH_COMPUTED)
    assert first_match[2]["capture_index"] == 1
    assert first_match[2]["owned_pct"] == 0
    assert first_match[2]["regime"] == "j0"

    piece_id = client.get(f"/looks/{first['look_id']}/gaps").json()["missing"][0]
    option = client.get(f"/gaps/{piece_id}/options").json()["options"][1]
    action = client.post(
        "/decisions/actions",
        json={"option_id": option["id"], "action": "buy"},
    )
    assert action.status_code == 201
    purchase = client.post(
        "/purchases/confirm",
        json={"option_id": option["id"], "idempotency_key": "analytics-purchase-1"},
    )
    assert purchase.status_code == 200

    action_event = _event(events, emitter.DECISION_ACTION_TAKEN)
    assert action_event[2]["capture_index"] == 1
    assert action_event[2]["regime"] == "j0"

    purchase_event = _event(events, emitter.PURCHASE_CONFIRMED)
    assert purchase_event[2]["wardrobe_count_before"] == 0
    assert purchase_event[2]["wardrobe_count_after"] == 1
    assert purchase_event[2]["regime_before"] == "j0"

    second = client.post("/captures", json={}).json()
    second_look = client.get(f"/looks/{second['look_id']}").json()
    assert second_look["score_look"] == 25

    second_capture_event = _event(events, emitter.CAPTURE_STARTED, 1)
    assert second_capture_event[2]["capture_index"] == 2
    assert second_capture_event[2]["regime"] == "mature"
    assert second_capture_event[2]["wardrobe_count"] == 1

    second_match = _event(events, emitter.MATCH_COMPUTED, 1)
    assert second_match[2]["capture_index"] == 2
    assert second_match[2]["owned_pct"] == 25
    assert second_match[2]["regime"] == "mature"

    return_session = _event(events, emitter.RETURN_SESSION)
    assert return_session[2]["capture_index"] == 2
    assert return_session[2]["regime"] == "mature"


def test_decision_viewed_has_regime_context(client, monkeypatch):
    events: list[tuple[str, str, dict]] = []

    def collect(event: str, user_id: str, **props: object) -> None:
        events.append((event, user_id, props))

    monkeypatch.setattr(emitter, "emit", collect)
    client.post("/budget", json={"base_amount": 100})
    capture = client.post("/captures", json={}).json()
    client.get(f"/looks/{capture['look_id']}")
    piece_id = client.get(f"/looks/{capture['look_id']}/gaps").json()["missing"][0]
    option = client.get(f"/gaps/{piece_id}/options").json()["options"][1]

    response = client.post("/decisions/evaluate", json={"option_id": option["id"]})
    assert response.status_code == 200

    viewed = _event(events, emitter.DECISION_VIEWED)
    assert viewed[2]["capture_index"] == 1
    assert viewed[2]["regime"] == "j0"
    assert viewed[2]["available_after"] == 50.01
