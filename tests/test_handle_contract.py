from fastapi.testclient import TestClient
import aims.api as api


def test_handle_contract():
    client = TestClient(api.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "started_at" in data

def test_handle_contract_and_telemetry(monkeypatch):

    # 1) Force handle_message() to return a predictable result
    def fake_handle_message(message: str):
        return {
            "route": "human_billing",
            "issue": "billing",
            "reply": "Test reply",
        }

    # 2) Capture telemetry payloads without printing to the console
    captured = []

    def fake_log_event(payload):
        captured.append(payload)

    monkeypatch.setattr(api, "handle_message", fake_handle_message)
    monkeypatch.setattr(api, "log_event", fake_log_event)

    client = TestClient(api.app)
    resp = client.post(
        "/v1/handle",
        json={"message": "I was charged twice and need a refund"})
    assert resp.status_code == 200
    data = resp.json()

    # --- GOLDEN RESPONSE CONTRACT (this is what we are "locking") ---
    # Required top-level keys
    assert set(("route", "issue", "confidence", "reply", "escalate", "meta")).issubset(data.keys())

    # Types / shapes
    assert isinstance(data["route"], str)
    assert isinstance(data["issue"], str)
    assert isinstance(data["confidence"], (int, float))
    assert isinstance(data["reply"], str)
    assert isinstance(data["escalate"], bool)
    assert isinstance(data["meta"], dict)

    # Meta contract
    assert "ts" in data["meta"]
    assert isinstance(data["meta"]["ts"], str)

    # If you added elapsed_ms to meta, lock it too (recommended).
    # If you have NOT added it yet, comment these 2 lines out.
    assert "elapsed_ms" in data["meta"]
    assert isinstance(data["meta"]["elapsed_ms"], (int, float))

    # Behavior contract for billing
    assert data["issue"] == "billing"
    assert data["escalate"] is True
    assert data["route"] == "human_billing"

    # --- TELEMETRY CONTRACT (stable fields) ---
    assert len(captured) >= 1
    event = captured[-1]
    assert event.get("type") == "handle_complete"
    assert "route" in event
    assert "issue" in event
    assert "confidence" in event
    assert "escalate" in event
