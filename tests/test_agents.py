import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from verticals.msignals.src.agents.vas import VASAgent
from verticals.msignals.src.agents.lra import LRAAgent
from verticals.msignals.src.agents.pha import PHAAgent
from verticals.msignals.src.agents.nla import NLAAgent
from verticals.msignals.src.agents.hia import HIAAgent
from verticals.msignals.src.agents.base import AgentOutput

@pytest.mark.asyncio
async def test_vas_agent_mock():
    agent = VASAgent()
    output = await agent.fetch("patient-123")
    assert isinstance(output, AgentOutput)
    assert output.agent_id == "vas"
    assert output.freshness_status == "fresh"
    assert output.confidence == 0.90
    assert "hr" in output.data
    assert "temp_c" in output.data

@pytest.mark.asyncio
async def test_vas_staleness_penalty():
    agent = VASAgent()
    eval_time = datetime.now(timezone.utc)
    
    # 1. Inside TTL (25 seconds ago) -> No penalty
    fetched_at_1 = eval_time - timedelta(seconds=25)
    output1 = AgentOutput(
        agent_id="vas", domain="vital_signs", source="chartevents",
        fetched_at=fetched_at_1, freshness_status="fresh",
        confidence=0.90, raw_confidence=0.90, data={}, raw_text=""
    )
    penalized1 = agent._apply_staleness_penalty(output1, eval_time)
    assert penalized1.freshness_status == "fresh"
    assert penalized1.confidence == 0.90

    # 2. 70 seconds ago -> stale_seconds=40. breaches=40//30 = 1. penalty = 0.15
    fetched_at_2 = eval_time - timedelta(seconds=70)
    output2 = AgentOutput(
        agent_id="vas", domain="vital_signs", source="chartevents",
        fetched_at=fetched_at_2, freshness_status="fresh",
        confidence=0.90, raw_confidence=0.90, data={}, raw_text=""
    )
    penalized2 = agent._apply_staleness_penalty(output2, eval_time)
    assert penalized2.freshness_status == "stale"
    assert penalized2.confidence == 0.75  # 0.90 - 0.15 * 1

    # 3. 100 seconds ago -> stale_seconds=70. breaches=70//30 = 2. penalty = 0.30
    fetched_at_3 = eval_time - timedelta(seconds=100)
    output3 = AgentOutput(
        agent_id="vas", domain="vital_signs", source="chartevents",
        fetched_at=fetched_at_3, freshness_status="fresh",
        confidence=0.90, raw_confidence=0.90, data={}, raw_text=""
    )
    penalized3 = agent._apply_staleness_penalty(output3, eval_time)
    assert penalized3.confidence == 0.60  # 0.90 - 0.15 * 2

@pytest.mark.asyncio
async def test_lra_escalation_flags():
    agent = LRAAgent()
    # Mock output with specific lab values to trigger flags
    eval_time = datetime.now(timezone.utc)
    # Fetch default mock
    output = await agent.fetch("patient-123", evaluation_time=eval_time)
    assert "lactate_gt_2" in output.escalation_flags
    assert "lactate_rising" in output.escalation_flags
    assert "wbc_high" in output.escalation_flags
    assert "creatinine_rise" not in output.escalation_flags

@pytest.mark.asyncio
async def test_pha_nephrotoxins_and_anticoagulants():
    agent = PHAAgent()
    eval_time = datetime.now(timezone.utc)
    output = await agent.fetch("patient-123", evaluation_time=eval_time)
    assert isinstance(output, AgentOutput)
    # The default mock does not have nephrotoxins/anticoagulants active, let's verify
    assert "nephrotoxin_active" not in output.escalation_flags
    assert "anticoagulant_active" not in output.escalation_flags

@pytest.mark.asyncio
async def test_nla_keyword_scanning():
    agent = NLAAgent()
    eval_time = datetime.now(timezone.utc)
    # Test stub NLA with custom notes containing deterioration keywords
    notes = ["Patient has severe respiratory distress with accessory muscles visible."]
    output = await agent.fetch("patient-123", notes=notes, evaluation_time=eval_time)
    assert "distress" in output.data["deterioration_keywords_found"]
    assert "accessory muscles" in output.data["deterioration_keywords_found"]
    assert "deterioration_keyword" in output.escalation_flags
    assert "negative_clinical_sentiment" in output.escalation_flags

@pytest.mark.asyncio
async def test_hia_context_flags():
    agent = HIAAgent()
    output = await agent.fetch("patient-123")
    assert "prior_sepsis" in output.escalation_flags
    assert "diabetes_known" in output.escalation_flags
