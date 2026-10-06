from collections import Counter
from dataclasses import asdict
from datetime import datetime

from backend.character.models import CharacterProfile
from backend.character.runtime import CharacterRuntime
from backend.deliberation.fake import DeterministicDeliberator
from backend.simulation.simulator import Simulator
from backend.simulation.virtual_clock import VirtualClock


def run_baseline(days: int = 3, start: datetime | None = None) -> dict:
    """Run the deterministic Milestone 1 baseline and return a reviewable summary."""
    if days < 1:
        raise ValueError("days must be >= 1")

    start = start or datetime(2026, 1, 1, 9, 0)
    runtime = CharacterRuntime(
        CharacterProfile("mira", "Mira", "warm, independent", "natural")
    )
    sim = Simulator(
        runtime,
        DeterministicDeliberator(act_threshold=0.7),
        VirtualClock(start),
    )
    events = sim.run_hours(days * 24)
    counts = Counter(event.decision for event in events)

    return {
        "character": runtime.profile.name,
        "days": days,
        "start": start.isoformat(),
        "end": events[-1].at.isoformat() if events else start.isoformat(),
        "counts": dict(counts),
        "final_relationship": asdict(runtime.relationship),
        "events": [
            {
                "at": event.at.isoformat(),
                "decision": event.decision,
                "reason": event.reason,
                "intent": event.intent,
            }
            for event in events
        ],
    }


def format_report(summary: dict) -> str:
    counts = summary["counts"]
    acts = counts.get("ACT", 0)
    waits = counts.get("WAIT", 0)
    lines = [
        "# Milestone 1 Baseline Simulation",
        "",
        f"Character: {summary['character']}",
        f"Duration: {summary['days']} virtual day(s)",
        f"Window: {summary['start']} -> {summary['end']}",
        f"Decisions: {acts} ACT / {waits} WAIT",
        "",
        "## Events",
        "",
    ]
    for event in summary["events"]:
        intent = f" | intent: {event['intent']}" if event["intent"] else ""
        lines.append(
            f"- {event['at']} | {event['decision']} | {event['reason']}{intent}"
        )
    return "\n".join(lines) + "\n"
