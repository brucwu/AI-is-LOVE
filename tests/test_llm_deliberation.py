from backend.character.models import CharacterProfile, Decision
from backend.character.runtime import CharacterRuntime
from backend.deliberation.llm import LLMDeliberator


class StubModel:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate_json(self, *, system, payload):
        self.calls.append((system, payload))
        return self.result


def make_runtime():
    return CharacterRuntime(
        CharacterProfile("c1", "Mira", "warm, independent", "natural")
    )


def test_llm_can_choose_wait_even_when_character_has_feelings():
    runtime = make_runtime()
    runtime.relationship.longing = 0.9
    model = StubModel({
        "decision": "WAIT",
        "reason": "I miss them, but I do not need to interrupt them right now.",
        "intent": "message the player",
        "next_wakeup_minutes": 45,
    })
    result = LLMDeliberator(model).deliberate(runtime)
    assert result.decision is Decision.WAIT
    assert result.intent is None
    assert result.next_wakeup_minutes == 45


def test_llm_can_choose_act_with_genuine_intent():
    model = StubModel({
        "decision": "ACT",
        "reason": "A remembered event makes reaching out feel natural now.",
        "intent": "ask how the event went",
        "next_wakeup_minutes": 180,
    })
    result = LLMDeliberator(model).deliberate(make_runtime())
    assert result.decision is Decision.ACT
    assert result.intent == "ask how the event went"
    assert model.calls


def test_chinese_intent_and_reason_survive_structured_deliberation():
    model = StubModel({"decision": "ACT", "reason": "想到他今天很累，想問他到家了沒。",
                       "intent": "問他到家了沒，讓他知道我惦記著他。", "next_wakeup_minutes": 90})
    result = LLMDeliberator(model).deliberate(make_runtime())
    assert result.reason == model.result["reason"]
    assert result.intent == model.result["intent"]
    assert result.decision is Decision.ACT
