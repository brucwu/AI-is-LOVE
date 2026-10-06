from typing import Protocol
from backend.character.models import DeliberationResult


class Deliberator(Protocol):
    def deliberate(self, runtime: "CharacterRuntime") -> DeliberationResult: ...
