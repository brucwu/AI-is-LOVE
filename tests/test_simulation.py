from datetime import datetime
from backend.character.models import CharacterProfile, Decision
from backend.character.runtime import CharacterRuntime
from backend.deliberation.fake import DeterministicDeliberator
from backend.simulation.virtual_clock import VirtualClock
from backend.simulation.simulator import Simulator


def make_simulator():
    runtime = CharacterRuntime(CharacterProfile("c1", "Mira", "warm, independent", "natural"))
    return Simulator(runtime, DeterministicDeliberator(0.7), VirtualClock(datetime(2026, 1, 1, 9)))


def test_wait_is_a_valid_outcome():
    sim = make_simulator()
    result = sim.step()
    assert result.decision is Decision.WAIT
    assert sim.events[-1].intent is None


def test_time_creates_opportunity_not_guaranteed_action():
    sim = make_simulator()
    sim.run_hours(8)
    assert any(e.decision == "WAIT" for e in sim.events)
    assert not all(e.decision == "ACT" for e in sim.events)


def test_character_can_eventually_act_from_internal_state():
    sim = make_simulator()
    sim.run_hours(12)
    assert any(e.decision == "ACT" for e in sim.events)
