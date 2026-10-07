from dataclasses import dataclass, field
from datetime import datetime

from backend.character.models import (
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

    def advance_internal_time(self, now: datetime, elapsed_hours: float) -> None:
        self.relationship.longing = min(1.0, self.relationship.longing + 0.08 * elapsed_hours)
        self.mental.last_deliberated_at = now

    def remember(self, memory: Memory) -> None:
        self.memories.append(memory)

    def experience(self, event: LivedExperience) -> None:
        self.life.current_activity = event.activity
        self.life.recent_experiences.append(event)
        self.life.recent_experiences = self.life.recent_experiences[-30:]

        if event.thread_id:
            thread = next((t for t in self.life.threads if t.id == event.thread_id), None)
            if thread:
                if event.thread_progress:
                    thread.summary = event.thread_progress
                thread.last_progress_at = event.occurred_at

        # Legacy bridge while older simulations/fixtures still use free-text threads.
        if event.future_thread and event.future_thread not in self.life.ongoing_threads:
            self.life.ongoing_threads.append(event.future_thread)

        if event.creates_memory:
            self.remember(Memory(
                content=event.summary,
                occurred_at=event.occurred_at,
                importance=event.salience,
                emotional_weight=min(1.0, max(-1.0, event.salience)),
            ))

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
            r.stage_reason = "Strong mutual commitment plus high trust, intimacy, and security."
        elif commitment >= 0.5 and r.trust >= 0.65 and r.security >= 0.6:
            r.stage = RelationshipStage.COMMITTED
            r.stage_reason = "Explicit commitment is supported by sustained trust and security."
        elif reciprocal >= 1.2 and positive >= 1.5 and r.trust >= 0.55 and r.intimacy >= 0.45:
            r.stage = RelationshipStage.EARLY_ROMANCE
            r.stage_reason = "Repeated reciprocal affection/vulnerability supports an emerging romance."
        elif reciprocal >= 0.5 and positive >= 0.7:
            r.stage = RelationshipStage.MUTUAL_INTEREST
            r.stage_reason = "There is meaningful evidence that romantic interest is becoming reciprocal."
        else:
            r.stage = RelationshipStage.ATTRACTION
            r.stage_reason = "Attraction exists, but reciprocal romantic evidence is still limited."
