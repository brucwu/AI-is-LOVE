import json
import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, Field

from backend.character.models import CharacterProfile, Memory, RelationshipState
from backend.character.runtime import CharacterRuntime
from backend.deliberation.llm import LLMDeliberator
from backend.models.openai import OpenAIStructuredModel

app = FastAPI(title="AI is LOVE", version="0.4.0")
logger = logging.getLogger("ai_is_love.behavior")


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


def run_behavior_experiment() -> dict:
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
    payload = {"character": "Mira", "results": results}
    logger.warning("BEHAVIOR_EXPERIMENT_RESULT %s", json.dumps(payload, ensure_ascii=False))
    return payload


@app.on_event("startup")
def optional_startup_behavior_experiment() -> None:
    if os.getenv("RUN_BEHAVIOR_EXPERIMENT_ON_STARTUP", "").lower() not in {"1", "true", "yes"}:
        return
    try:
        run_behavior_experiment()
    except Exception:
        logger.exception("BEHAVIOR_EXPERIMENT_FAILED")


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
    return run_behavior_experiment()
