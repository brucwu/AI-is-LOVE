from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from backend.character.models import (
    AutonomyState,
    CharacterProfile,
    LifeState,
    LifeThread,
    LivedExperience,
    Memory,
    MentalState,
    RelationshipEvidence,
    RelationshipStage,
    RelationshipState,
)


@dataclass
class CharacterRuntime:
    profile: CharacterProfile
    relationship: RelationshipState = field(default_factory=RelationshipState)
    mental: MentalState = field(default_factory=MentalState)
    memories: list[Memory] = field(default_factory=list)
    relationship_evidence: list[RelationshipEvidence] = field(default_factory=list)
    life: LifeState = field(default_factory=LifeState)
    autonomy: AutonomyState = field(default_factory=AutonomyState)

    def advance_internal_time(self, now: datetime, elapsed_hours: float) -> None:
        self.relationship.longing = min(1.0, self.relationship.longing + 0.08 * elapsed_hours)
        self.mental.last_deliberated_at = now

    def remember(self, memory: Memory) -> None:
        self.memories.append(memory)

    def experience(self, event: LivedExperience) -> LivedExperience:
        """Apply an experience; only known active threads accept bounded progress.

        Return the accepted event so callers do not report rejected model claims.
        Identity, thread IDs/status/importance and other threads remain Runtime-owned.
        """
        thread = next((t for t in self.life.threads
                       if t.id == event.thread_id and t.status == "active"), None)
        progress = event.thread_progress.strip() if isinstance(event.thread_progress, str) else ""
        if thread is not None and progress and len(progress) <= 2000:
            thread.summary = progress
            thread.last_progress_at = event.occurred_at
            next_step = event.thread_next_step
            hours = event.thread_next_step_in_hours
            if next_step is None and hours is None:
                thread.next_step = None
                thread.next_check_at = None
            elif (isinstance(next_step, str) and next_step.strip() and len(next_step) <= 500
                  and type(hours) is int and 6 <= hours <= 168):
                thread.next_step = next_step.strip()
                thread.next_check_at = event.occurred_at + timedelta(hours=hours)
            else:
                next_step = None
                hours = None
            event = replace(event, thread_progress=progress,
                            thread_next_step=next_step, thread_next_step_in_hours=hours)
        else:
            event = replace(event, thread_id=None, thread_progress=None,
                            thread_next_step=None, thread_next_step_in_hours=None)

        self.life.current_activity = event.activity
        self.mental.mood = event.emotional_reaction
        self.life.recent_experiences.append(event)
        self.life.recent_experiences = self.life.recent_experiences[-30:]

        # Preserve v0 fixtures; structured v1 state does not accept arbitrary free-text threads.
        if self.life.identity is None and event.future_thread and event.future_thread not in self.life.ongoing_threads:
            self.life.ongoing_threads.append(event.future_thread)

        if event.creates_memory:
            self.remember(Memory(
                content=event.summary,
                occurred_at=event.occurred_at,
                importance=event.salience,
                emotional_weight=min(1.0, max(-1.0, event.salience)),
            ))
        return event

    def add_life_thread(self, thread: LifeThread) -> None:
        if not any(existing.id == thread.id for existing in self.life.threads):
            self.life.threads.append(thread)

    def record_relationship_evidence(self, evidence: RelationshipEvidence) -> None:
        self.relationship_evidence.append(evidence)
        self._reassess_relationship_stage()

    def _reassess_relationship_stage(self) -> None:
        positive = sum(max(0.0, e.valence) * e.significance for e in self.relationship_evidence[-30:])
        reciprocal = sum(
            e.significance for e in self.relationship_evidence[-30:]
            if e.kind in {"player_affection", "mutual_vulnerability", "commitment", "repair"} and e.valence > 0
        )
        commitment = sum(
            e.significance for e in self.relationship_evidence[-30:]
            if e.kind == "commitment" and e.valence > 0
        )

        r = self.relationship
        if commitment >= 1.0 and r.trust >= 0.75 and r.intimacy >= 0.7 and r.security >= 0.7:
            r.stage = RelationshipStage.PASSIONATE
            r.stage_reason = "彼此有明確承諾，也有深厚的信任、親密和安全感。"
        elif commitment >= 0.5 and r.trust >= 0.65 and r.security >= 0.6:
            r.stage = RelationshipStage.COMMITTED
            r.stage_reason = "彼此的承諾有持續的信任與安全感支持。"
        elif reciprocal >= 1.2 and positive >= 1.5 and r.trust >= 0.55 and r.intimacy >= 0.45:
            r.stage = RelationshipStage.EARLY_ROMANCE
            r.stage_reason = "彼此多次表達喜歡、坦露脆弱，戀情正在萌芽。"
        elif reciprocal >= 0.5 and positive >= 0.7:
            r.stage = RelationshipStage.MUTUAL_INTEREST
            r.stage_reason = "有具體跡象顯示，這份喜歡正在得到回應。"
        else:
            r.stage = RelationshipStage.ATTRACTION
            r.stage_reason = "已經喜歡對方，但還不太確定對方的心意。"
