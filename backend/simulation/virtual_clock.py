from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class VirtualClock:
    now: datetime

    def advance_minutes(self, minutes: int) -> datetime:
        self.now += timedelta(minutes=minutes)
        return self.now
