from dataclasses import dataclass, field
from datetime import datetime
from backend.character.models import CharacterProfile, RelationshipState, MentalState, Memory


@dataclass
class CharacterRuntime:
    profile: CharacterProfile
    relationship: RelationshipState = field(default_factory=RelationshipState)
    mental: MentalState = field(default_factory=MentalState)
    memories: list[Memory] = field(default_factory=list)

    def advance_internal_time(self, now: datetime, elapsed_hours: float) -> None:
        # MVP placeholder dynamics: absence can increase longing without forcing action.
        self.relationship.longing = min(1.0, self.relationship.longing + 0.08 * elapsed_hours)
        self.mental.last_deliberated_at = now

    def remember(self, memory: Memory) -> None:
        self.memories.append(memory)
