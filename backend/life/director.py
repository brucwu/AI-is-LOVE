from dataclasses import asdict
from datetime import datetime
from backend.character.models import LivedExperience

LIFE_SCHEMA = {"type":"object","properties":{"activity":{"type":"string"},"summary":{"type":"string"},"emotional_reaction":{"type":"string"},"salience":{"type":"number","minimum":0,"maximum":1},"location":{"type":["string","null"]},"creates_memory":{"type":"boolean"},"future_thread":{"type":["string","null"]}},"required":["activity","summary","emotional_reaction","salience","location","creates_memory","future_thread"],"additionalProperties":False}

SYSTEM_PROMPT = """You are the Life Director for a persistent fictional romantic character named Mira. Advance her off-screen life by one plausible slice of time. Her life exists for its own sake, not merely to create content for the player.
Prefer grounded everyday continuity with occasional meaningful, funny, frustrating, surprising, or emotionally resonant moments. Avoid both boring diary bookkeeping and nonstop drama. Continue existing plans and threads when natural. Do not invent real-world current facts, named venues, news, or claims that require external grounding; this v0 simulation has no World Grounding input.
Generate one representative lived experience for this time slice. It can be mundane. Only mark creates_memory true when the experience is salient enough that a person might actually remember it later. A future_thread should be a concise unresolved plan, concern, curiosity, or intention worth carrying forward; otherwise null."""

class LLMLifeDirector:
    def __init__(self, model): self.model = model

    def advance(self, runtime, now: datetime) -> LivedExperience:
        payload = {
            "now": now.isoformat(), "character": asdict(runtime.profile),
            "mental_state": {"mood": runtime.mental.mood, "unresolved_intentions": runtime.mental.unresolved_intentions},
            "life_state": {"current_activity": runtime.life.current_activity, "ongoing_threads": runtime.life.ongoing_threads[-10:], "future_plans": runtime.life.future_plans[-10:], "recent_experiences":[{**asdict(e),"occurred_at":e.occurred_at.isoformat()} for e in runtime.life.recent_experiences[-8:]]},
            "recent_memories":[{**asdict(m),"occurred_at":m.occurred_at.isoformat()} for m in runtime.memories[-8:]],
            "player_present": False, "world_grounding": []}
        raw=self.model.generate_json(system=SYSTEM_PROMPT,payload=payload,schema=LIFE_SCHEMA,schema_name="lived_experience")
        return LivedExperience(occurred_at=now,activity=str(raw["activity"]).strip(),summary=str(raw["summary"]).strip(),emotional_reaction=str(raw["emotional_reaction"]).strip(),salience=float(raw["salience"]),location=raw.get("location"),creates_memory=bool(raw["creates_memory"]),future_thread=raw.get("future_thread"))
