import pytest
from datetime import datetime, timezone, timedelta
from verticals.msignals.src.agents.base import AgentOutput
from verticals.msignals.src.rules.compound import (
    detect_sepsis,
    detect_aki,
    detect_respiratory_failure,
    detect_drug_conflict,
    detect_fluid_overload,
)

def create_mock_output(
    agent_id: str,
    domain: str,
    confidence: float,
    data: dict,
    escalation_flags: list = None,
    fetched_at: datetime = None
) -> AgentOutput:
    return AgentOutput(
        agent_id=agent_id,
        domain=domain,
        source="mock",
        fetched_at=fetched_at or datetime.now(timezone.utc),
        freshness_status="fresh",
        confidence=confidence,
        raw_confidence=confidence,
        data=data,
        raw_text="mock text",
        escalation_flags=escalation_flags or [],
        stale_seconds=0
    )

# --- Sepsis Tests ---

def test_sepsis_three_agent_convergence():
    # 3 active domains: VAS (vitals meet sepsis), LRA (labs abnormal), PHA (antibiotics active)
    vas = create_mock_output("vas", "vital_signs", 0.90, {"hr": 105, "sbp": 95, "temp_c": 37.0, "rr": 12}) # hr > 100, sbp < 100
    lra = create_mock_output("lra", "laboratory", 0.85, {"wbc": 14.0, "lactate": 2.5}) # wbc > 12, lactate > 2
    pha = create_mock_output("pha", "pharmacy", 0.99, {"active_medications": [{"name": "Vancomycin IV"}]}) # active antibiotic
    
    outputs = {"vas": vas, "lra": lra, "pha": pha}
    res = detect_sepsis(outputs)
    
    assert res.detected is True
    assert res.action_tier == 3  # Notify attending
    assert "vas" in res.agents_contributing
    assert "lra" in res.agents_contributing
    assert "pha" in res.agents_contributing
    assert res.conflict_detected is False

def test_sepsis_vas_lra_conflict():
    # Critical case: VAS hemodynamically STABLE (no flags) AND LRA lactate is RISING (lactate_rising)
    vas = create_mock_output("vas", "vital_signs", 0.88, {"hr": 72, "sbp": 120, "temp_c": 36.8, "rr": 14}, escalation_flags=[])
    lra = create_mock_output("lra", "laboratory", 0.91, {"lactate": 2.4}, escalation_flags=["lactate_rising"])
    
    outputs = {"vas": vas, "lra": lra}
    res = detect_sepsis(outputs)
    
    assert res.detected is True
    assert res.conflict_detected is True
    assert "vas" in res.conflict_agents
    assert "lra" in res.conflict_agents
    # VAS/LRA conflict only (no infection context / HIA active) -> Tier 2 Advisory
    assert res.action_tier == 2 
    # confidence = lra.confidence * 0.85 = 0.91 * 0.85 = 0.7735 -> 0.773
    assert res.confidence == 0.773

def test_sepsis_below_threshold():
    # Below sepsis threshold
    vas = create_mock_output("vas", "vital_signs", 0.90, {"hr": 80, "sbp": 120})
    lra = create_mock_output("lra", "laboratory", 0.85, {"wbc": 7.0, "lactate": 1.0})
    
    outputs = {"vas": vas, "lra": lra}
    res = detect_sepsis(outputs)
    assert res.detected is False
    assert res.action_tier == 1

def test_sepsis_stale_lra_penalty():
    # Sepsis meets threshold, but LRA was stale (confidence penalized)
    vas = create_mock_output("vas", "vital_signs", 0.90, {"hr": 105, "sbp": 95})
    lra = create_mock_output("lra", "laboratory", 0.65, {"wbc": 14.0, "lactate": 2.5}) # raw_confidence was 0.85, decayed to 0.65 due to stale
    hia = create_mock_output("hia", "patient_history", 0.80, {"prior_sepsis": True})
    
    outputs = {"vas": vas, "lra": lra, "hia": hia}
    res = detect_sepsis(outputs)
    assert res.detected is True
    assert res.action_tier == 3
    # confidence = avg of vas (0.90), lra (0.65), hia (0.80) -> 0.783
    assert res.confidence == 0.783

# --- AKI Tests ---

def test_aki_three_agent():
    vas = create_mock_output("vas", "vital_signs", 0.90, {}, escalation_flags=["map_lt_65"])
    lra = create_mock_output("lra", "laboratory", 0.85, {}, escalation_flags=["creatinine_rise"])
    pha = create_mock_output("pha", "pharmacy", 0.99, {}, escalation_flags=["nephrotoxin_active"])
    
    outputs = {"vas": vas, "lra": lra, "pha": pha}
    res = detect_aki(outputs)
    assert res.detected is True
    assert res.action_tier == 3
    assert "lra" in res.agents_contributing
    assert "vas" in res.agents_contributing
    assert "pha" in res.agents_contributing

def test_aki_two_agent_no_vas():
    lra = create_mock_output("lra", "laboratory", 0.85, {}, escalation_flags=["creatinine_rise"])
    pha = create_mock_output("pha", "pharmacy", 0.99, {}, escalation_flags=["nephrotoxin_active"])
    
    outputs = {"lra": lra, "pha": pha}
    res = detect_aki(outputs)
    assert res.detected is True
    assert res.action_tier == 2 # 2-agent AKI is tier 2
    assert "lra" in res.agents_contributing
    assert "pha" in res.agents_contributing
    assert "vas" not in res.agents_contributing

def test_aki_no_trigger():
    lra = create_mock_output("lra", "laboratory", 0.85, {})
    pha = create_mock_output("pha", "pharmacy", 0.99, {}, escalation_flags=["nephrotoxin_active"])
    
    outputs = {"lra": lra, "pha": pha}
    res = detect_aki(outputs)
    assert res.detected is False
    assert res.action_tier == 1

# --- Respiratory Failure Tests ---

def test_respiratory_autonomous():
    # Autonomous alert: spo2_lt_88 AND rr_gt_30
    vas = create_mock_output("vas", "vital_signs", 0.90, {}, escalation_flags=["spo2_lt_88", "rr_gt_30"])
    
    outputs = {"vas": vas}
    res = detect_respiratory_failure(outputs)
    assert res.detected is True
    assert res.action_tier == 4
    assert "Rapid response" in res.recommended_action

def test_respiratory_notify():
    # Notify alert: spo2_trending + rr > 25 (e.g. 27) + NLA keyword
    vas = create_mock_output("vas", "vital_signs", 0.90, {"rr": 27}, escalation_flags=["spo2_trending"])
    nla = create_mock_output("nla", "clinical_notes", 0.70, {"deterioration_keywords_found": ["accessory muscles"]})
    
    outputs = {"vas": vas, "nla": nla}
    res = detect_respiratory_failure(outputs)
    assert res.detected is True
    assert res.action_tier == 3
    assert "Notify bedside nurse" in res.recommended_action

def test_respiratory_nla_only():
    nla = create_mock_output("nla", "clinical_notes", 0.70, {"deterioration_keywords_found": ["accessory muscles"]})
    outputs = {"nla": nla}
    res = detect_respiratory_failure(outputs)
    assert res.detected is False

# --- Drug Conflict Tests ---

def test_drug_conflict_anticoagulant_inr():
    # PHA active anticoagulant + interaction; LRA elevated INR
    pha = create_mock_output("pha", "pharmacy", 0.99, {}, escalation_flags=["anticoagulant_active", "drug_interaction_detected"])
    lra = create_mock_output("lra", "laboratory", 0.85, {}, escalation_flags=["inr_gt_3_5"])
    
    outputs = {"pha": pha, "lra": lra}
    res = detect_drug_conflict(outputs)
    assert res.detected is True
    assert res.conflict_detected is True
    assert res.action_tier == 3
    assert "Pharmacist review required" in res.recommended_action

def test_drug_conflict_no_anticoagulant():
    pha = create_mock_output("pha", "pharmacy", 0.99, {}, escalation_flags=["drug_interaction_detected"])
    lra = create_mock_output("lra", "laboratory", 0.85, {}, escalation_flags=["inr_gt_3_5"])
    
    outputs = {"pha": pha, "lra": lra}
    res = detect_drug_conflict(outputs)
    assert res.detected is False

# --- Fluid Overload Tests ---

def test_fluid_three_agent():
    pha = create_mock_output("pha", "pharmacy", 0.99, {"total_iv_24h_liters": 7.2})
    vas = create_mock_output("vas", "vital_signs", 0.90, {"rr": 28}, escalation_flags=["spo2_trending"])
    nla = create_mock_output("nla", "clinical_notes", 0.70, {"deterioration_keywords_found": ["crackles"]})
    
    outputs = {"pha": pha, "vas": vas, "nla": nla}
    res = detect_fluid_overload(outputs)
    assert res.detected is True
    assert res.action_tier == 3 # 3-agent fluid overload is tier 3

def test_fluid_two_agent():
    pha = create_mock_output("pha", "pharmacy", 0.99, {"total_iv_24h_liters": 7.2})
    vas = create_mock_output("vas", "vital_signs", 0.90, {"rr": 28}, escalation_flags=["spo2_trending"])
    
    outputs = {"pha": pha, "vas": vas}
    res = detect_fluid_overload(outputs)
    assert res.detected is True
    assert res.action_tier == 2 # 2-agent fluid overload is tier 2
