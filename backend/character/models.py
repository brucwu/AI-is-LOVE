from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Decision(str, Enum):
    ACT = "ACT"
    WAIT = "WAIT"


@dataclass
class CharacterProfile:
    id: str
    name: str
    personality: str
    expression_style: str


@dataclass
class RelationshipState:
    trust: float = 0.5
    intimacy: float = 0.2
    longing: float = 0.0
    hurt: float = 0.0
    security: float = 0.5


@dataclass
class MentalState:
    mood: str = "neutral"
    unresolved_intentions: list[str] = field(default_factory=list)
    last_deliberated_at: datetime | None = None


@dataclass
class Memory:
    content: str
    occurred_at: datetime
    importance: float = 0.5
    emotional_weight: float = 0.0


@dataclass
class DeliberationResult:
    decision: Decision
    reason: str
    intent: str | None = None
    next_wakeup_minutes: int = 60
