from backend.character.models import Decision, DeliberationResult


class DeterministicDeliberator:
    """Test double: acts only when longing crosses the configured threshold."""

    def __init__(self, act_threshold: float = 0.7):
        self.act_threshold = act_threshold

    def deliberate(self, runtime):
        longing = runtime.relationship.longing
        if longing >= self.act_threshold:
            return DeliberationResult(
                decision=Decision.ACT,
                reason=f"longing {longing:.2f} reached threshold",
                intent="reach out to the player",
                next_wakeup_minutes=180,
            )
        return DeliberationResult(
            decision=Decision.WAIT,
            reason=f"longing {longing:.2f} below threshold",
            next_wakeup_minutes=60,
        )
