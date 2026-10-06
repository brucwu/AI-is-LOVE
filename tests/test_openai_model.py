import json

from backend.models.openai import OpenAIStructuredModel


class FakeResponse:
    output_text = json.dumps({
        "decision": "WAIT",
        "reason": "I can care without interrupting.",
        "intent": None,
        "next_wakeup_minutes": 60,
    })


class FakeResponses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeResponse()


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_openai_gateway_uses_structured_output_and_does_not_store_response():
    client = FakeClient()
    model = OpenAIStructuredModel(client=client)
    result = model.generate_json(system="system", payload={"hello": "world"})

    assert result["decision"] == "WAIT"
    assert client.responses.kwargs["model"] == "gpt-5.4-mini"
    assert client.responses.kwargs["store"] is False
    assert client.responses.kwargs["text"]["format"]["strict"] is True
    assert client.responses.kwargs["reasoning"]["effort"] == "low"
