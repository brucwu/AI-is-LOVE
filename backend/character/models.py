from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Decision(str, Enum):
    ACT = "ACT"
    WAIT = "WAIT"


class RelationshipStage(str, Enum):
    ATTRACTION = "attraction"
    MUTUAL_INTEREST = "mutual_interest"
    EARLY_ROMANCE = "early_romance"
    COMMITTED = "committed"
    PASSIONATE = "passionate"


@dataclass
class CharacterProfile:
    id: str
    name: str
    personality: str
    expression_style: str
    affection: float = 0.85
    desire_for_connection: float = 0.8


@dataclass
class LifePerson:
    name: str
    relationship: str
    description: str


@dataclass
class LifeIdentity:
    profession: str
    profession_context: str
    skills: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    important_people: list[LifePerson] = field(default_factory=list)
    long_term_goals: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)


@dataclass
class LifeThread:
    id: str
    category: str
    title: str
    summary: str
    status: str = "active"
    importance: float = 0.5
    last_progress_at: datetime | None = None
    next_step: str | None = None
    next_check_at: datetime | None = None


@dataclass
class RelationshipEvidence:
    kind: str
    description: str
    occurred_at: datetime
    valence: float = 0.0
    significance: float = 0.5


@dataclass
class RelationshipState:
    trust: float = 0.5
    intimacy: float = 0.2
    longing: float = 0.0
    hurt: float = 0.0
    security: float = 0.5
    stage: RelationshipStage = RelationshipStage.ATTRACTION
    stage_reason: str = "已經心動，但還沒有彼此承諾。"


@dataclass
class MentalState:
    mood: str = "平靜"
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


@dataclass
class LivedExperience:
    occurred_at: datetime
    summary: str
    activity: str
    emotional_reaction: str
    salience: float = 0.5
    location: str | None = None
    creates_memory: bool = False
    future_thread: str | None = None
    thread_id: str | None = None
    thread_progress: str | None = None
    thread_next_step: str | None = None
    thread_next_step_in_hours: int | None = None
    category: str = "personal"
    participants: list[str] = field(default_factory=list)


@dataclass
class LifeState:
    current_activity: str = "過著平常的一天"
    identity: LifeIdentity | None = None
    threads: list[LifeThread] = field(default_factory=list)
    ongoing_threads: list[str] = field(default_factory=list)
    future_plans: list[str] = field(default_factory=list)
    recent_experiences: list[LivedExperience] = field(default_factory=list)


@dataclass
class AutonomyState:
    next_wakeup_at: datetime | None = None
    next_life_at: datetime | None = None
    budget_day: str = ""
    attempts_today: int = 0
    last_decision: str | None = None
    last_reason: str | None = None
    proposed_intent: str | None = None
