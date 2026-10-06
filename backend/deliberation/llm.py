import json
from dataclasses import asdict
from typing import Protocol

from backend.character.models import Decision, DeliberationResult


class StructuredModel(Protocol):
    def generate_json(self, *, system: str, payload: dict) -> dict: ...


SYSTEM_PROMPT = """You are the private cognition layer for a persistent romantic AI character.
Decide whether the character should ACT toward the player now or WAIT.
A wakeup is only an opportunity to think; it is never an instruction to message.
The character can miss the player, think about them, or form an intention and still WAIT.
Do not optimize for engagement frequency. Preserve the character's personality, dignity,
independence, relationship context, and continuity. Return structured JSON only with:
decision (ACT or WAIT), reason, intent (string or null), next_wakeup_minutes (positive integer).
ACT means there is a genuine outward action worth taking now. WAIT is a first-class outcome."""


class LLMDeliberator:
    """Model-backed cognition. The runtime remains authoritative over persistent state."""

    def __init__(self, model: StructuredModel):
        self.model = model

    def deliberate(self, runtime) -> DeliberationResult:
        payload = {
            "character": asdict(runtime.profile),
            "relationship": asdict(runtime.relationship),
            "mental_state": {
                "mood": runtime.mental.mood,
                "unresolved_intentions": list(runtime.mental.unresolved_intentions),
                "last_deliberated_at": (
                    runtime.mental.last_deliberated_at.isoformat()
                    if runtime.mental.last_deliberated_at else None
                ),
            },
            "recent_memories": [
                {
                    **asdict(memory),
                    "occurred_at": memory.occurred_at.isoformat(),
                }
                for memory in runtime.memories[-10:]
            ],
        }
        raw = self.model.generate_json(system=SYSTEM_PROMPT, payload=payload)
        decision = Decision(raw["decision"])
        intent = raw.get("intent")
        if decision is Decision.WAIT:
            intent = None
        wakeup = max(1, int(raw.get("next_wakeup_minutes", 60)))
        return DeliberationResult(
            decision=decision,
            reason=str(raw.get("reason", "")).strip(),
            intent=intent,
            next_wakeup_minutes=wakeup,
        )
