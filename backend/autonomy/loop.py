"""Durable wake-up opportunities, not scheduled player messages.

CAS reserves an opportunity BEFORE model calls. A crash consumes budget and leaves
an expiring reservation. Concurrent saves never overwrite player/manual updates.
Free Render sleep pauses this loop; missed opportunities are not replayed in bulk.
"""
import logging
import random
import threading
from datetime import datetime, timedelta, timezone

from backend.persistence.store import RuntimeStore, ConflictError

logger = logging.getLogger("ai_is_love.autonomy")


def tick(url, now, director, deliberator, *, daily_limit=8, jitter=None):
    if now.tzinfo is None:
        raise ValueError("Timezone-aware clock required")
    now = now.astimezone(timezone.utc)
    if not 1 <= daily_limit <= 24:
        raise ValueError("Invalid daily opportunity budget")
    jitter = jitter or random.randint
    store = RuntimeStore(url)
    try:
        runtime, revision = store.load("mira")
        if runtime is None:
            return {"status": "missing"}
        state = runtime.autonomy
        if state.next_wakeup_at and now < state.next_wakeup_at:
            return {"status": "waiting"}
        day = now.date().isoformat()
        if state.budget_day != day:
            state.budget_day, state.attempts_today = day, 0
        if state.attempts_today >= daily_limit:
            state.next_wakeup_at = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1, minutes=jitter(5, 30))
            try:
                store.save(runtime, revision)
            except ConflictError:
                pass
            return {"status": "budget_wait"}
        state.attempts_today += 1
        state.next_wakeup_at = now + timedelta(minutes=20)  # Crash/error lease.
        try:
            revision = store.save(runtime, revision)
        except ConflictError:
            return {"status": "contended"}
        recent = runtime.life.recent_experiences
        life_due = state.next_life_at or (recent[-1].occurred_at + timedelta(hours=6) if recent else now)
        event = None
        if now >= life_due:
            event = runtime.experience(director.advance(runtime, now))
            state.next_life_at = now + timedelta(hours=6)
        previous = runtime.mental.last_deliberated_at
        elapsed = max(0, (now - previous).total_seconds() / 3600) if previous else 0
        runtime.advance_internal_time(now, elapsed)
        result = deliberator.deliberate(runtime)
        state.last_decision, state.last_reason = result.decision.value, result.reason
        # A proposed ACT is internal state, not a sent message or a delivery queue.
        state.proposed_intent = result.intent if result.decision.value == "ACT" else None
        minutes = max(30, min(360, result.next_wakeup_minutes + jitter(-15, 15)))
        state.next_wakeup_at = now + timedelta(minutes=minutes)
        try:
            revision = store.save(runtime, revision)
        except ConflictError:
            return {"status": "conflict", "delivery": "none"}
        payload = {"status": "advanced", "revision": revision,
                   "decision": state.last_decision, "delivery": "none",
                   "life_advanced": event is not None,
                   "thread_id": event.thread_id if event else None,
                   "attempts_today": state.attempts_today,
                   "next_wakeup_at": state.next_wakeup_at.isoformat()}
        logger.warning("AUTONOMY_TICK %s", payload)
        return payload
    finally:
        store.close()


class LifeLoop:
    def __init__(self, url, director, deliberator, daily_limit=8):
        self.url, self.director, self.deliberator = url, director, deliberator
        self.daily_limit = daily_limit
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name="mira-life", daemon=True)

    def run(self):
        while not self.stop_event.is_set():
            try:
                tick(self.url, datetime.now(timezone.utc), self.director,
                     self.deliberator, daily_limit=self.daily_limit)
            except Exception as error:
                # Do not log connection strings or provider request headers.
                logger.error("AUTONOMY_TICK_FAILED type=%s", type(error).__name__)
            self.stop_event.wait(30)

    def start(self):
        self.thread.start()

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=2)
