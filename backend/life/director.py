from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.character.models import LivedExperience


LIFE_SCHEMA = {
    "type": "object",
    "properties": {
        "activity": {"type": "string"},
        "category": {"type": "string", "enum": ["career", "social", "interest", "personal", "rest"]},
        "summary": {"type": "string"},
        "emotional_reaction": {"type": "string"},
        "salience": {"type": "number", "minimum": 0, "maximum": 1},
        "location": {"type": ["string", "null"]},
        "participants": {"type": "array", "items": {"type": "string"}},
        "creates_memory": {"type": "boolean"},
        "thread_id": {"type": ["string", "null"]},
        "thread_progress": {"type": ["string", "null"]},
    },
    "required": ["activity", "category", "summary", "emotional_reaction", "salience",
                 "location", "participants", "creates_memory", "thread_id", "thread_progress"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are Life Director v1 for a persistent fictional character. She exists and lives even when the player is absent. Generate one representative experience in the elapsed slice, not a six-hour continuous task or a message to the player.

Use the supplied Life Identity: profession, responsibilities, important people, interests and long-term goals. Usually advance ONE existing active Life Thread when appropriate. Select its exact id; thread_progress is a concise cumulative state of that thread AFTER this experience, retaining unresolved concerns, specific people, commitments and future timing. Preserve established facts; do not reset a case, forget an agreement or repeat a completed task. The Runtime alone applies validated progression; you cannot create threads or rewrite identity/status/importance. An ordinary unthreaded event (especially rest) is fine: return null for both thread fields.

Use recent experiences, memories, mental state and local temporal context causally. Plans made earlier should lead to preparation, actual meetings/events and later consequences when their time arrives. Do not repeatedly defer or endlessly refine a plan. Existing animals remain the same fictional cases across follow-ups; rehabilitation/release must take plausible time and involve appropriate clinical assessment, not miraculous recovery. Coworkers and friends have distinct roles and their own constraints. Do not turn every interaction into a therapeutic pep talk.

Mostly ordinary believable life, some meaningful/share-worthy experiences, very few exceptional events. Work should be present on plausible shifts, with follow-ups and colleagues, but not consume all hours or all days. Protect off-duty life, social contact, outdoor interests and rest. At night sleep/rest is normal, not recurring midnight chores or routine center visits. There is no established work roster yet: infer modest shifts consistently from recent history, allow days off, and do not claim a real schedule. Consider recent category counts and streaks: avoid consecutive slices dominated by the same category unless a specific obligation or ongoing event justifies it. This is context for judgment, not a category rotation quota. A broad personal-life thread is not an excuse for repetitive apartment organizing, receipts, kitchen chores or tea. Interests can involve going out and doing things, not only planning them.

No constant melodrama, emergencies, extraordinary coincidences or forced emotional breakthroughs. Only create a memory for something a person might remember later, not each meal/task. Report category for the actual main activity (sleep is rest even if it supports life balance), actual participants (empty when alone), and a generic location. No World Grounding exists: do not invent current named restaurants/venues, news, weather, opening hours or other externally verifiable current facts. Veterinary cases and events must be fictional, non-identifiable and professionally reasonable. World grounding is empty; do not imply you looked anything up."""


def serialize_experience(event):
    return {**asdict(event), "occurred_at": event.occurred_at.isoformat()}


def serialize_thread(thread):
    return {**asdict(thread), "last_progress_at": thread.last_progress_at.isoformat() if thread.last_progress_at else None}


class LLMLifeDirector:
    def __init__(self, model):
        self.model = model

    def advance(self, runtime, now: datetime) -> LivedExperience:
        if now.tzinfo is None:
            raise ValueError("Life Director requires timezone-aware time")
        local = now.astimezone(ZoneInfo("America/Los_Angeles"))
        recent = runtime.life.recent_experiences[-8:]
        counts = {category: sum(e.category == category for e in recent)
                  for category in LIFE_SCHEMA["properties"]["category"]["enum"]}
        streak = 0
        for event in reversed(recent):
            if event.category != recent[-1].category:
                break
            streak += 1
        payload = {
            "version": "life-director-v1",
            "character": asdict(runtime.profile),
            "life_identity": asdict(runtime.life.identity) if runtime.life.identity else None,
            "active_life_threads": [serialize_thread(t) for t in runtime.life.threads if t.status == "active"],
            "temporal_context": {
                "now": now.isoformat(), "local_now": local.isoformat(),
                "timezone": "America/Los_Angeles", "weekday": local.strftime("%A"),
                "local_hour": local.hour,
                "elapsed_hours": (now - recent[-1].occurred_at).total_seconds() / 3600 if recent else 6,
            },
            "mental_state": {"mood": runtime.mental.mood, "unresolved_intentions": runtime.mental.unresolved_intentions},
            "life_state": {
                "current_activity": runtime.life.current_activity,
                "future_plans": runtime.life.future_plans[-10:],
                "recent_experiences": [serialize_experience(e) for e in recent],
                "recent_category_counts": counts,
                "last_category_streak": streak,
            },
            "recent_memories": [{**asdict(m), "occurred_at": m.occurred_at.isoformat()} for m in runtime.memories[-8:]],
            "player_present": False, "world_grounding": [],
        }
        raw = self.model.generate_json(system=SYSTEM_PROMPT, payload=payload, schema=LIFE_SCHEMA, schema_name="lived_experience_v1")
        return LivedExperience(
            occurred_at=now, activity=raw["activity"].strip(), category=raw["category"],
            summary=raw["summary"].strip(), emotional_reaction=raw["emotional_reaction"].strip(),
            salience=float(raw["salience"]), location=raw["location"], participants=raw["participants"],
            creates_memory=raw["creates_memory"], thread_id=raw["thread_id"], thread_progress=raw["thread_progress"],
        )
