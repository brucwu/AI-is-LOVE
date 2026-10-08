import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import secrets
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse
from backend.chat.service import ChatComposer, ChatBusy, RequestMismatch, send_message, public_turn
from backend.chat.page import CHAT_PAGE
from pydantic import BaseModel, Field

from backend.character.models import CharacterProfile, LifeState, Memory, RelationshipStage, RelationshipState
from backend.character.runtime import CharacterRuntime
from backend.deliberation.llm import LLMDeliberator
from backend.models.openai import OpenAIStructuredModel
from backend.life.director import LLMLifeDirector, serialize_experience, serialize_thread
from backend.life.mira import mira_life_identity, mira_initial_threads
from backend.autonomy.loop import LifeLoop
from backend.persistence.service import initialize_database
from backend.persistence.store import RuntimeStore, ConflictError, encode

app = FastAPI(title="AI is LOVE", version="0.7.0")
logger = logging.getLogger("ai_is_love.behavior")
PROCESS_ID = str(uuid4())


@app.on_event("startup")
def initialize_persistent_runtime():
    url = os.getenv("DATABASE_URL")
    app.state.persistence = initialize_database(url) if url else None
    if url:
        logger.warning("PERSISTENCE_VALIDATION %s", json.dumps(
            {**app.state.persistence, "process_id": PROCESS_ID,
             "commit_sha": os.getenv("RENDER_GIT_COMMIT")}, ensure_ascii=False))


@app.on_event("startup")
def start_life_loop():
    app.state.life_loop = None
    if os.getenv("AUTONOMY_ENABLED", "").lower() not in {"1", "true", "yes"}:
        return
    if not os.getenv("DATABASE_URL") or not os.getenv("RUNTIME_API_TOKEN"):
        raise RuntimeError("Autonomy requires configured persistence and protected runtime access")
    limit = int(os.getenv("AUTONOMY_DAILY_LIMIT", "8"))
    if not 1 <= limit <= 24:
        raise ValueError("Invalid autonomy budget")
    from openai import OpenAI
    model = OpenAIStructuredModel(client=OpenAI(timeout=60, max_retries=0))
    store = RuntimeStore(os.environ["DATABASE_URL"])
    try:
        runtime, revision = store.load("mira")
        state = runtime.autonomy
        logger.warning("AUTONOMY_RESTORED %s", json.dumps({
            "revision": revision, "attempts_today": state.attempts_today,
            "next_wakeup_at": state.next_wakeup_at.isoformat() if state.next_wakeup_at else None,
            "next_life_at": state.next_life_at.isoformat() if state.next_life_at else None,
            "last_decision": state.last_decision,
            "process_id": PROCESS_ID, "commit_sha": os.getenv("RENDER_GIT_COMMIT")
        }))
    finally:
        store.close()
    app.state.life_loop = LifeLoop(os.environ["DATABASE_URL"], LLMLifeDirector(model),
                                  LLMDeliberator(model), limit)
    app.state.life_loop.start()


@app.on_event("shutdown")
def stop_life_loop():
    loop = getattr(app.state, "life_loop", None)
    if loop:
        loop.close()


def authorize_runtime(authorization: str | None = Header(default=None)):
    token = os.getenv("RUNTIME_API_TOKEN")
    if not token or not os.getenv("DATABASE_URL"):
        raise HTTPException(503, "Persistent runtime access is not configured")
    if not secrets.compare_digest(authorization or "", "Bearer " + token):
        raise HTTPException(401, "Unauthorized")


@app.get("/runtime/mira", dependencies=[Depends(authorize_runtime)])
def persistent_mira():
    store = RuntimeStore(os.environ["DATABASE_URL"])
    try:
        runtime, revision = store.load("mira")
        if runtime is None:
            raise HTTPException(404, "Character not found")
        return {"revision": revision, "runtime": encode(runtime)}
    finally:
        store.close()


@app.post("/runtime/mira/life", dependencies=[Depends(authorize_runtime)])
def advance_persistent_life():
    store = RuntimeStore(os.environ["DATABASE_URL"])
    try:
        runtime, revision = store.load("mira")
        if runtime is None:
            raise HTTPException(404, "Character not found")
        event = runtime.experience(LLMLifeDirector(OpenAIStructuredModel()).advance(
            runtime, datetime.now(timezone.utc)))
        try:
            revision = store.save(runtime, revision)
        except ConflictError:
            raise HTTPException(409, "Character changed; reload before retrying")
        return {"revision": revision, "event": serialize_experience(event)}
    finally:
        store.close()


class DeliberationRequest(BaseModel):
    character_name: str = "Mira"
    personality: str = "溫暖、有自己的生活，會留意別人的感受"
    expression_style: str = "自然親近，有喜歡就會表達，也尊重對方的空間"
    mood: str = "平靜"
    trust: float = Field(default=0.5, ge=0.0, le=1.0)
    intimacy: float = Field(default=0.2, ge=0.0, le=1.0)
    longing: float = Field(default=0.0, ge=0.0, le=1.0)
    hurt: float = Field(default=0.0, ge=0.0, le=1.0)
    security: float = Field(default=0.5, ge=0.0, le=1.0)
    relationship_stage: RelationshipStage = RelationshipStage.ATTRACTION
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
            stage=request.relationship_stage,
            stage_reason="這次測試明確指定的關係階段。",
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
                mood="掛心",
                trust=0.65,
                intimacy=0.4,
                longing=0.55,
                memories=["玩家告訴 Mira，今天過得很辛苦，也很累。"],
            ),
        ),
        (
            "long_absence",
            DeliberationRequest(
                mood="有點想念",
                trust=0.7,
                intimacy=0.5,
                longing=0.95,
                memories=["玩家已經很久沒和 Mira 聯絡了。"],
            ),
        ),
        (
            "after_intimate_moment",
            DeliberationRequest(
                mood="心裡暖暖的",
                trust=0.85,
                intimacy=0.8,
                longing=0.45,
                security=0.8,
                memories=["Mira 和玩家最近聊到脆弱的心事，也表達了彼此的喜歡。"],
            ),
        ),
    ]
    results = []
    for name, request in scenarios:
        results.append({"scenario": name, **run_deliberation(request)})
    payload = {"character": "Mira", "results": results}
    logger.warning("BEHAVIOR_EXPERIMENT_RESULT %s", json.dumps(payload, ensure_ascii=False))
    return payload


def run_stage_experiment() -> dict:
    stages = [
        (RelationshipStage.ATTRACTION, 0.45, 0.35, 0.35),
        (RelationshipStage.MUTUAL_INTEREST, 0.58, 0.45, 0.48),
        (RelationshipStage.EARLY_ROMANCE, 0.7, 0.6, 0.62),
        (RelationshipStage.COMMITTED, 0.82, 0.76, 0.8),
        (RelationshipStage.PASSIONATE, 0.9, 0.88, 0.9),
    ]
    results = []
    for stage, trust, intimacy, security in stages:
        request = DeliberationRequest(
            mood="喜歡玩家，也很想念對方",
            trust=trust,
            intimacy=intimacy,
            longing=0.8,
            security=security,
            relationship_stage=stage,
            memories=[
                "Mira 想起玩家時心裡很柔軟，想和對方靠近一點。",
                "沒有急事或非聯絡不可的任務。",
            ],
        )
        results.append({"stage": stage.value, **run_deliberation(request)})
    payload = {"character": "Mira", "experiment": "relationship_stage_comparison", "results": results}
    logger.warning("STAGE_EXPERIMENT_RESULT %s", json.dumps(payload, ensure_ascii=False))
    return payload


@app.on_event("startup")
def optional_startup_behavior_experiment() -> None:
    if os.getenv("RUN_BEHAVIOR_EXPERIMENT_ON_STARTUP", "").lower() not in {"1", "true", "yes"}:
        return
    try:
        run_behavior_experiment()
        run_stage_experiment()
    except Exception:
        logger.exception("BEHAVIOR_EXPERIMENT_FAILED")


@app.get("/", response_class=HTMLResponse)
def root():
    return CHAT_PAGE


def authorize_chat(authorization: str | None = Header(default=None)):
    token = os.getenv("CHAT_ACCESS_TOKEN")
    if not token or not os.getenv("DATABASE_URL"):
        raise HTTPException(503, "Chat access is not configured")
    if not secrets.compare_digest(authorization or "", "Bearer " + token):
        raise HTTPException(401, "Unauthorized")


class ChatRequest(BaseModel):
    request_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,80}$")
    text: str = Field(min_length=1, max_length=2000)


@app.get("/chat", dependencies=[Depends(authorize_chat)])
def chat_history():
    store = RuntimeStore(os.environ["DATABASE_URL"])
    try:
        runtime, revision = store.load("mira")
        if runtime is None:
            raise HTTPException(404, "Character not found")
        return {"character": runtime.profile.name, "turns": [public_turn(t) for t in runtime.conversation]}
    finally:
        store.close()


def chat_composer():
    from openai import OpenAI
    return ChatComposer(OpenAIStructuredModel(client=OpenAI(timeout=60, max_retries=0)))


@app.post("/chat", dependencies=[Depends(authorize_chat)])
def chat_send(request: ChatRequest):
    try:
        return send_message(os.environ["DATABASE_URL"], request.request_id, request.text, chat_composer())
    except ChatBusy:
        raise HTTPException(409, "Reply in progress; retry the same message")
    except RequestMismatch:
        raise HTTPException(409, "Request ID already used")
    except ValueError:
        raise HTTPException(422, "Invalid message or reply")
    except Exception:
        logger.error("CHAT_REPLY_FAILED")
        raise HTTPException(502, "Reply unavailable; retry the same message")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "process_id": PROCESS_ID,
            "persistence": "ready" if getattr(app.state, "persistence", None) else "disabled"}


@app.post("/deliberate")
def deliberate(request: DeliberationRequest) -> dict:
    return run_deliberation(request)


@app.get("/experiments/behavior")
@app.post("/experiments/behavior")
def behavior_experiment() -> dict:
    return run_behavior_experiment()


@app.get("/experiments/stages")
@app.post("/experiments/stages")
def stage_experiment() -> dict:
    return run_stage_experiment()


def run_life_simulation(days: int = 7, slice_hours: int = 6) -> dict:
    if days < 1 or slice_hours < 1 or days * 24 % slice_hours:
        raise ValueError("Simulation requires positive days and evenly dividing slices")
    runtime = CharacterRuntime(
        profile=CharacterProfile(id="development-character", name="Mira",
                                 personality="溫暖、有自己的生活，會留意別人的感受",
                                 expression_style="自然親近，有喜歡就會表達，也尊重對方的空間"),
        life=LifeState(identity=mira_life_identity(), threads=mira_initial_threads()),
    )
    director = LLMLifeDirector(OpenAIStructuredModel())
    # Comparable local dayparts; not dependent on the UTC hour the endpoint was called.
    now = datetime.now(ZoneInfo("America/Los_Angeles")).replace(hour=6, minute=0, second=0, microsecond=0)
    events = []
    for step in range(days * 24 // slice_hours):
        event_time = now + timedelta(hours=step * slice_hours)
        event = runtime.experience(director.advance(runtime, event_time))
        events.append(serialize_experience(event))
    payload = {
        "character": "Mira", "experiment": "seven_days_without_player",
        "version": "life-director-v1", "language": "zh-TW", "commit_sha": os.getenv("RENDER_GIT_COMMIT"),
        "days": days, "slice_hours": slice_hours, "player_interventions": 0,
        "life_identity": asdict(runtime.life.identity), "events": events,
        "memories_created": len(runtime.memories),
        "threads": [serialize_thread(t) for t in runtime.life.threads],
        "threads_progressed": sorted({e.thread_id for e in runtime.life.recent_experiences if e.thread_id}),
        "ongoing_threads": runtime.life.ongoing_threads,
    }
    logger.warning("LIFE_SIMULATION_RESULT %s", json.dumps(payload, ensure_ascii=False))
    return payload


@app.get("/experiments/life")
@app.post("/experiments/life")
def life_experiment() -> dict:
    return run_life_simulation()

