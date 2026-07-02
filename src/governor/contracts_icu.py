from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class AgentContract:
    agent_id: str
    dispatch: str
    confidence_threshold: float
    gate_threshold: float
    freshness_ttl_seconds: Optional[int]
    staleness_penalty: float
    escalation_conditions: List[str]

ICU_CONTRACTS: Dict[str, AgentContract] = {
    "vas": AgentContract(
        agent_id="vas",
        dispatch="continuous",
        confidence_threshold=0.90,
        gate_threshold=0.70,
        freshness_ttl_seconds=30,
        staleness_penalty=0.15,
        escalation_conditions=[
            "hr_gt_130", "spo2_lt_88", "sbp_lt_80", "rr_gt_30",
            "temp_gt_38_5", "temp_lt_36", "map_lt_65", "spo2_trending"
        ]
    ),
    "lra": AgentContract(
        agent_id="lra",
        dispatch="event",
        confidence_threshold=0.85,
        gate_threshold=0.65,
        freshness_ttl_seconds=21600,  # 6h
        staleness_penalty=0.10,
        escalation_conditions=[
            "lactate_gt_2", "lactate_rising", "wbc_high", "wbc_low",
            "creatinine_rise", "inr_gt_3_5", "platelet_low"
        ]
    ),
    "pha": AgentContract(
        agent_id="pha",
        dispatch="event",
        confidence_threshold=0.99,
        gate_threshold=0.85,
        freshness_ttl_seconds=None,
        staleness_penalty=0.0,
        escalation_conditions=[
            "drug_interaction_detected", "dose_exceeds_max",
            "nephrotoxin_active", "anticoagulant_active"
        ]
    ),
    "nla": AgentContract(
        agent_id="nla",
        dispatch="event",
        confidence_threshold=0.70,
        gate_threshold=0.50,
        freshness_ttl_seconds=14400,  # 4h
        staleness_penalty=0.08,
        escalation_conditions=[
            "negative_clinical_sentiment", "deterioration_keyword"
        ]
    ),
    "hia": AgentContract(
        agent_id="hia",
        dispatch="daily",
        confidence_threshold=0.75,
        gate_threshold=0.55,
        freshness_ttl_seconds=86400,  # 24h
        staleness_penalty=0.05,
        escalation_conditions=[
            "prior_sepsis", "immunocompromised", "high_risk_combo"
        ]
    )
}

def get_contract(agent_id: str) -> AgentContract:
    if agent_id not in ICU_CONTRACTS:
        raise ValueError(f"No governor contract for agent: {agent_id}")
    return ICU_CONTRACTS[agent_id]

def requires_gate(agent_id: str, confidence: float) -> bool:
    return confidence < get_contract(agent_id).gate_threshold

def passes_publish_threshold(agent_id: str, confidence: float) -> bool:
    return confidence >= get_contract(agent_id).confidence_threshold
