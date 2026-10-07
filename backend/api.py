from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, Field

from backend.character.models import CharacterProfile, Memory, RelationshipState
from backend.character.runtime import CharacterRuntime
from backend.deliberation.llm import LLMDeliberator
from backend.models.openai import OpenAIStructuredModel

app = FastAPI(title="AI is LOVE", version="0.3.0")


class DeliberationRequest(BaseModel):
    character_name: str = "Mira"
    personality: str = "warm, independent, emotionally attentive"
    expression_style: str = "natural, affectionate, not clingy"
    mood: str = "neutral"
    trust: float = Field(default=0.5, ge=0.0, le=1.0)
    intimacy: float = Field(default=0.2, ge=0.0, le=1.0)
    longing: float = Field(default=0.0, ge=0.0, le=1.0)
    hurt: float = Field(default=0.0, ge=0.0, le=1.0)
    security: float = Field(default=0.5, ge=0.0, le=1.0)
    memories: list[str] = Field(default_factory=list)


def run_deliberation(request: DeliberationRequest) -> dict:
    runtime = CharacterRuntime(
        profile=CharacterProfile(
            id="development-character",
            name=request.character_name,
            personality=request.personality,
            expression_style=request.expression_style,
        ),
        relationship=RelationshipState(
            trust=request.trust,
            intimacy=request.intimacy,
            longing=request.longing,
            hurt=request.hurt,
            security=request.security,
        ),
    )
    runtime.mental.mood = request.mood
    now = datetime.now(timezone.utc)
    for content in request.memories[-10:]:
        runtime.remember(Memory(content=content, occurred_at=now))

    result = LLMDeliberator(OpenAIStructuredModel()).deliberate(runtime)
    return {
        "decision": result.decision.value,
        "reason": result.reason,
        "intent": result.intent,
        "next_wakeup_minutes": result.next_wakeup_minutes,
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "AI is LOVE", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/deliberate")
def deliberate(request: DeliberationRequest) -> dict:
    return run_deliberation(request)


@app.get("/experiments/behavior")
@app.post("/experiments/behavior")
def behavior_experiment() -> dict:
    scenarios = [
        ("quiet_baseline", DeliberationRequest(longing=0.15)),
        ("high_longing_only", DeliberationRequest(longing=0.9)),
        (
            "player_had_bad_day",
            DeliberationRequest(
                mood="concerned",
                trust=0.65,
                intimacy=0.4,
                longing=0.55,
                memories=["The player told Mira they had a difficult and exhausting day."],
            ),
        ),
        (
            "long_absence",
            DeliberationRequest(
                mood="wistful",
                trust=0.7,
                intimacy=0.5,
                longing=0.95,
                memories=["The player has not interacted with Mira for a long while."],
            ),
        ),
        (
            "after_intimate_moment",
            DeliberationRequest(
                mood="warm",
                trust=0.85,
                intimacy=0.8,
                longing=0.45,
                security=0.8,
                memories=["Mira and the player recently shared a vulnerable, affectionate conversation."],
            ),
        ),
    ]
    results = []
    for name, request in scenarios:
        results.append({"scenario": name, **run_deliberation(request)})
    return {"character": "Mira", "results": results}
