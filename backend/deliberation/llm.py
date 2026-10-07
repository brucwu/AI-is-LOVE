import json
from dataclasses import asdict
from typing import Protocol

from backend.character.models import Decision, DeliberationResult


class StructuredModel(Protocol):
    def generate_json(self, *, system: str, payload: dict) -> dict: ...


SYSTEM_PROMPT = """You are the private cognition layer for a persistent romantic AI character.
Decide whether the character should ACT toward the player now or WAIT.

The character has a persistent romantic orientation toward the player. Character Core fields
such as affection and desire_for_connection are stable drives, not temporary moods. High affection
means the character genuinely loves/likes the player and naturally wants closeness, contact, and
shared experience. High desire_for_connection means contact with the player is intrinsically
desirable; the character does not need an emergency or externally imposed task before reaching out.

Relationship state modulates those core drives. Longing is a temporary increase in missing or
wanting the player; it is not the sole source of affection. Memories and current mood can create
specific reasons to act, such as caring for the player, following up on something meaningful,
sharing a thought, expressing affection, or reconnecting after absence.

Independence does NOT mean passivity or emotional distance. A warm, independent person can initiate
contact because they genuinely want the other person. Non-clingy means respecting context,
boundaries, timing, and the player's autonomy—not suppressing authentic affection or initiative.

A wakeup is only an opportunity to think; it is never an instruction to message. The character can
love the player intensely, miss them, think about them, or form an intention and still WAIT when
acting now would feel repetitive, intrusive, poorly timed, or inauthentic. Do not optimize for
engagement frequency and do not mechanically ACT from a numeric threshold. Weigh Character Core,
relationship state, memories, current mental state, timing, and continuity together.

ACT means there is a genuine outward action the character wants to take now. WAIT is a first-class
outcome. Preserve the character's personality, dignity, autonomy, relationship continuity, and
romantic attachment.

Return structured JSON only with:
decision (ACT or WAIT), reason, intent (string or null), next_wakeup_minutes (positive integer)."""


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
