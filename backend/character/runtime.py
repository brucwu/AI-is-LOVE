from dataclasses import dataclass, field
from datetime import datetime

from backend.character.models import (
    CharacterProfile,
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

    def advance_internal_time(self, now: datetime, elapsed_hours: float) -> None:
        # Absence can increase longing without forcing action.
        self.relationship.longing = min(1.0, self.relationship.longing + 0.08 * elapsed_hours)
        self.mental.last_deliberated_at = now

    def remember(self, memory: Memory) -> None:
        self.memories.append(memory)

    def record_relationship_evidence(self, evidence: RelationshipEvidence) -> None:
        self.relationship_evidence.append(evidence)
        self._reassess_relationship_stage()

    def _reassess_relationship_stage(self) -> None:
        positive = sum(
            max(0.0, e.valence) * e.significance for e in self.relationship_evidence[-30:]
        )
        reciprocal = sum(
            e.significance
            for e in self.relationship_evidence[-30:]
            if e.kind in {"player_affection", "mutual_vulnerability", "commitment", "repair"}
            and e.valence > 0
        )
        commitment = sum(
            e.significance
            for e in self.relationship_evidence[-30:]
            if e.kind == "commitment" and e.valence > 0
        )

        r = self.relationship
        # MVP transition policy: evidence is necessary, so numeric state alone cannot level up.
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
