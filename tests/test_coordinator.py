import pytest
import asyncio
from datetime import datetime, timezone
from verticals.msignals.src.coordinator import ICUCoordinator, ICUAlignedState

@pytest.mark.asyncio
async def test_coordinator_alignment_structure():
    coord = ICUCoordinator()
    
    # Default alignment run with mock fallbacks
    state = await coord.align("patient-123")
    
    assert isinstance(state, ICUAlignedState)
    assert state.patient_id == "patient-123"
    assert state.version == 1
    assert len(state.agent_outputs) == 5
    assert "vas" in state.agent_outputs
    assert "lra" in state.agent_outputs
    assert "pha" in state.agent_outputs
    assert "nla" in state.agent_outputs
    assert "hia" in state.agent_outputs
    assert isinstance(state.aligned_at, datetime)
    assert len(state.state_hash) == 64  # standard sha256 output length

@pytest.mark.asyncio
async def test_coordinator_version_increment():
    coord = ICUCoordinator()
    
    state1 = await coord.align("patient-999")
    state2 = await coord.align("patient-999")
    
    assert state1.version == 1
    assert state2.version == 2

@pytest.mark.asyncio
async def test_coordinator_deterministic_hash():
    coord = ICUCoordinator()
    eval_time = datetime.now(timezone.utc)
    
    state1 = await coord.align("patient-101", evaluation_time=eval_time)
    # Same inputs should produce exactly the same hash
    state2 = await coord.align("patient-101", evaluation_time=eval_time)
    # Note: version changes, but state_hash is based only on agents and conflicts
    assert state1.state_hash == state2.state_hash
    
    # Adding a note changes NLA inputs and should change the hash
    state3 = await coord.align("patient-101", notes=["accessory muscles visible"], evaluation_time=eval_time)
    assert state1.state_hash != state3.state_hash

@pytest.mark.asyncio
async def test_coordinator_conflict_detection():
    coord = ICUCoordinator()
    
    # Under mock values:
    # - VAS has no active flags (HR 102, RR 22, Temp 38.4, BP 94/62 - all below VAS thresholds)
    # - LRA has "lactate_rising" (lactate 2.4 vs 1.8 6h ago -> rise of 0.6 > 0.5)
    # This triggers the pre-threshold Sepsis VAS/LRA conflict trigger.
    state = await coord.align("patient-456")
    
    assert len(state.conflicts) == 1
    sepsis_conflict = state.conflicts[0]
    assert sepsis_conflict.pattern == "sepsis"
    assert sepsis_conflict.conflict_detected is True
    assert set(sepsis_conflict.conflict_agents) == {"vas", "lra"}
    assert sepsis_conflict.action_tier == 3  # VAS/LRA conflict + active HIA/PHA defaults -> Tier 3 Notify
    assert state.highest_action_tier >= 3
