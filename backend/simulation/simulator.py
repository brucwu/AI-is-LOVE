from dataclasses import dataclass, field
from backend.character.models import Decision


@dataclass
class SimulationEvent:
    at: object
    decision: str
    reason: str
    intent: str | None


@dataclass
class Simulator:
    runtime: object
    deliberator: object
    clock: object
    events: list[SimulationEvent] = field(default_factory=list)

    def step(self, minutes: int = 60):
        now = self.clock.advance_minutes(minutes)
        self.runtime.advance_internal_time(now, minutes / 60.0)
        result = self.deliberator.deliberate(self.runtime)
        self.events.append(SimulationEvent(now, result.decision.value, result.reason, result.intent))
        if result.decision is Decision.ACT:
            # Acting relieves some longing, but does not reset the relationship.
            self.runtime.relationship.longing = max(0.0, self.runtime.relationship.longing - 0.45)
        return result

    def run_hours(self, hours: int):
        for _ in range(hours):
            self.step(60)
        return self.events
