from fastapi.testclient import TestClient

import backend.api as api
from backend.character.models import Decision, DeliberationResult


class StubDeliberator:
    def __init__(self, model):
        pass

    def deliberate(self, runtime):
        assert runtime.profile.name == "Mira"
        assert runtime.relationship.longing == 0.9
        assert runtime.memories[-1].content == "The player had a difficult day."
        return DeliberationResult(
            decision=Decision.WAIT,
            reason="She cares, but there is no need to interrupt right now.",
            intent=None,
            next_wakeup_minutes=45,
        )


def test_health():
    client = TestClient(api.app)
    assert client.get("/health").json() == {"status": "ok"}


def test_deliberate_endpoint(monkeypatch):
    monkeypatch.setattr(api, "LLMDeliberator", StubDeliberator)
    monkeypatch.setattr(api, "OpenAIStructuredModel", lambda: object())
    client = TestClient(api.app)
    response = client.post(
        "/deliberate",
        json={
            "longing": 0.9,
            "memories": ["The player had a difficult day."],
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "decision": "WAIT",
        "reason": "She cares, but there is no need to interrupt right now.",
        "intent": None,
        "next_wakeup_minutes": 45,
    }
