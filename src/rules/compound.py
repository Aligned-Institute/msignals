from dataclasses import dataclass, field
from typing import List, Dict, Optional
from ..agents.base import AgentOutput

@dataclass
class CompoundResult:
    pattern: str                  # 'sepsis' | 'aki' | 'respiratory_failure' | 'drug_conflict' | 'fluid_overload'
    detected: bool
    confidence: float
    agents_contributing: List[str]
    conflict_detected: bool       # True if agent signals diverge
    conflict_agents: List[str]    # Which agents are in conflict
    conflict_description: str
    resolution_directive: str
    action_tier: int              # 1=suppress 2=advisory 3=notify 4=autonomous
    recommended_action: str

def detect_sepsis(outputs: Dict[str, AgentOutput]) -> CompoundResult:
    vas = outputs.get("vas")
    lra = outputs.get("lra")
    pha = outputs.get("pha")
    hia = outputs.get("hia")

    # 1. VAS Active: HR > 100 AND (SBP < 100 OR Temp > 38.5 OR Temp < 36.0 OR RR > 22)
    vas_active = False
    if vas:
        hr = vas.data.get("hr", 0)
        sbp = vas.data.get("sbp", 120)
        temp_c = vas.data.get("temp_c", 37.0)
        rr = vas.data.get("rr", 12)
        vas_active = (hr > 100) and (sbp < 100 or temp_c > 38.5 or temp_c < 36.0 or rr > 22)

    # 2. LRA Active: WBC > 12 or < 4 AND Lactate > 2.0
    lra_active = False
    if lra:
        wbc = lra.data.get("wbc", 7.5)
        lactate = lra.data.get("lactate", 1.0)
        lra_active = (wbc > 12 or wbc < 4) and (lactate > 2.0)

    # 3. HIA Active (prior sepsis) or PHA Active (antibiotics active)
    hia_active = bool(hia and hia.data.get("prior_sepsis", False))
    
    abx = ["piperacillin", "tazobactam", "vancomycin", "meropenem", "cef", "penicillin", "gentamicin", "tobramycin", "linezolid", "cipro", "levo", "azithro", "tazo", "pip-tazo"]
    pha_abx_active = False
    if pha:
        active_meds = pha.data.get("active_medications", [])
        pha_abx_active = any(any(a in m.get("name", "").lower() for a in abx) for m in active_meds)

    infection_context_active = hia_active or pha_abx_active

    # Standard check: 3 domain markers active
    detected = sum([vas_active, lra_active, infection_context_active]) >= 3
    conflict_detected = False
    conflict_agents = []
    conflict_desc = ""
    resolution_directive = ""
    agents_contributing = []

    if vas_active: agents_contributing.append("vas")
    if lra_active: agents_contributing.append("lra")
    if hia_active: agents_contributing.append("hia")
    if pha_abx_active: agents_contributing.append("pha")

    # Critical conflict case: VAS hemodynamically STABLE (no flags) AND LRA lactate is RISING (lactate_rising flag)
    if vas and lra:
        vas_stable = len(vas.escalation_flags) == 0
        lra_rising = "lactate_rising" in lra.escalation_flags
        
        if vas_stable and lra_rising:
            detected = True
            conflict_detected = True
            conflict_agents = ["vas", "lra"]
            conflict_desc = "VAS reports hemodynamic compensation (BP stable, no flags). LRA reports ongoing metabolic stress — lactate climbing post-wean rather than clearing."
            resolution_directive = "LRA weighted primary — lactate trend post-wean outweighs momentary pressure recovery as sepsis staging signal. Vasopressor wean may be premature. Aggregate confidence penalized -0.04 for inter-agent divergence."
            if "vas" not in agents_contributing: agents_contributing.append("vas")
            if "lra" not in agents_contributing: agents_contributing.append("lra")

    # Calculate confidence
    if conflict_detected:
        confidence = round(lra.confidence * 0.85, 3)
    else:
        active_confs = [outputs[a].confidence for a in agents_contributing if a in outputs]
        confidence = round(sum(active_confs) / len(active_confs), 3) if active_confs else 0.0

    # Determine Action Tier
    if detected:
        if conflict_detected:
            if infection_context_active:
                action_tier = 3  # 2 agents + conflict (VAS/LRA conflict + infection context)
            else:
                action_tier = 2  # VAS/LRA conflict only
        else:
            action_tier = 3      # 3 agents contributing
    else:
        action_tier = 1

    return CompoundResult(
        pattern="sepsis",
        detected=detected,
        confidence=confidence,
        agents_contributing=agents_contributing,
        conflict_detected=conflict_detected,
        conflict_agents=conflict_agents,
        conflict_description=conflict_desc,
        resolution_directive=resolution_directive,
        action_tier=action_tier,
        recommended_action="Blood cultures x2 · Lactate repeat in 2h · Review antibiotic coverage · Hold vasopressor wean pending repeat labs"
    )

def detect_aki(outputs: Dict[str, AgentOutput]) -> CompoundResult:
    vas = outputs.get("vas")
    lra = outputs.get("lra")
    pha = outputs.get("pha")

    creatinine_rise = bool(lra and "creatinine_rise" in lra.escalation_flags)
    map_lt_65 = bool(vas and "map_lt_65" in vas.escalation_flags)
    nephrotoxin_active = bool(pha and "nephrotoxin_active" in pha.escalation_flags)

    # Trigger combinations
    three_agent_convergence = creatinine_rise and map_lt_65 and nephrotoxin_active
    two_agent_sufficient = creatinine_rise and nephrotoxin_active
    detected = three_agent_convergence or two_agent_sufficient

    agents_contributing = []
    if creatinine_rise: agents_contributing.append("lra")
    if map_lt_65: agents_contributing.append("vas")
    if nephrotoxin_active: agents_contributing.append("pha")

    # Action tier determination
    if detected:
        if three_agent_convergence:
            action_tier = 3
        else:
            action_tier = 2
    else:
        action_tier = 1

    # Average confidence of active/contributing agents
    active_confs = [outputs[a].confidence for a in agents_contributing if a in outputs]
    confidence = round(sum(active_confs) / len(active_confs), 3) if active_confs else 0.0

    return CompoundResult(
        pattern="aki",
        detected=detected,
        confidence=confidence,
        agents_contributing=agents_contributing,
        conflict_detected=False,
        conflict_agents=[],
        conflict_description="",
        resolution_directive="",
        action_tier=action_tier,
        recommended_action="Hold nephrotoxic agents · Nephrology consult · Fluid challenge consider"
    )

def detect_respiratory_failure(outputs: Dict[str, AgentOutput]) -> CompoundResult:
    vas = outputs.get("vas")
    nla = outputs.get("nla")
    hia = outputs.get("hia")

    spo2_lt_88 = bool(vas and "spo2_lt_88" in vas.escalation_flags)
    rr_gt_30 = bool(vas and "rr_gt_30" in vas.escalation_flags)
    spo2_trending = bool(vas and "spo2_trending" in vas.escalation_flags)
    
    # Check RR > 25 (if vas output data is present)
    rr_val = vas.data.get("rr", 0) if vas else 0
    rr_gt_25 = rr_val > 25

    # Check NLA keyword from respiratory set
    resp_keywords = ["increased work of breathing", "accessory muscles", "respiratory distress", "labored breathing", "shortness of breath", "dyspnea", "tachypnea"]
    nla_kws = nla.data.get("deterioration_keywords_found", []) if nla else []
    nla_resp_match = any(kw in resp_keywords for kw in nla_kws)

    # Trigger definitions
    autonomous_trigger = spo2_lt_88 and rr_gt_30
    notify_trigger = (spo2_trending or rr_gt_25) and nla_resp_match

    detected = autonomous_trigger or notify_trigger

    agents_contributing = []
    if spo2_lt_88 or rr_gt_30 or spo2_trending or rr_gt_25:
        if vas and "vas" not in agents_contributing: agents_contributing.append("vas")
    if nla_resp_match:
        if nla and "nla" not in agents_contributing: agents_contributing.append("nla")
    # HIA is contributing context if active
    if detected and hia and "copd_known" in hia.escalation_flags:
        agents_contributing.append("hia")

    if detected:
        if autonomous_trigger:
            action_tier = 4
            recommended_action = "Rapid response paged · Supplemental O2 order pre-populated"
        else:
            action_tier = 3
            recommended_action = "Notify bedside nurse · Document respiratory assessment"
    else:
        action_tier = 1
        recommended_action = ""

    active_confs = [outputs[a].confidence for a in agents_contributing if a in outputs]
    confidence = round(sum(active_confs) / len(active_confs), 3) if active_confs else 0.0

    return CompoundResult(
        pattern="respiratory_failure",
        detected=detected,
        confidence=confidence,
        agents_contributing=agents_contributing,
        conflict_detected=False,
        conflict_agents=[],
        conflict_description="",
        resolution_directive="",
        action_tier=action_tier,
        recommended_action=recommended_action
    )

def detect_drug_conflict(outputs: Dict[str, AgentOutput]) -> CompoundResult:
    pha = outputs.get("pha")
    lra = outputs.get("lra")

    anticoagulant_active = bool(pha and "anticoagulant_active" in pha.escalation_flags)
    drug_interaction = bool(pha and ("drug_interaction_detected" in pha.escalation_flags or "high_risk_combination" in pha.escalation_flags))
    
    inr_gt_3_5 = bool(lra and "inr_gt_3_5" in lra.escalation_flags)
    platelet_low = bool(lra and "platelet_low" in lra.escalation_flags)

    # Always conflict because LRA safety thresholds or anticoagulants collide with pharmacy orders
    conflict_condition = anticoagulant_active and drug_interaction and (inr_gt_3_5 or platelet_low)
    # The brief says: "PHA: anticoagulant_active AND drug_interaction_detected; LRA: inr_gt_3_5 OR platelet_low"
    detected = anticoagulant_active and (inr_gt_3_5 or platelet_low)

    agents_contributing = []
    if anticoagulant_active: agents_contributing.append("pha")
    if inr_gt_3_5 or platelet_low: agents_contributing.append("lra")

    if detected:
        action_tier = 3
        conflict_detected = True
        conflict_agents = ["pha", "lra"]
        conflict_description = "PHA reports active anticoagulant and drug interaction. LRA reports critical coagulopathy / bleeding risk (elevated INR or thrombocytopenia)."
        resolution_directive = "Pharmacist gate required. Hold all anticoagulant doses until pharmacist reviews interactions and checks lab trends."
        recommended_action = "Pharmacist review required · Hold anticoagulant dose · Recheck INR/platelets"
    else:
        action_tier = 1
        conflict_detected = False
        conflict_agents = []
        conflict_description = ""
        resolution_directive = ""
        recommended_action = ""

    active_confs = [outputs[a].confidence for a in agents_contributing if a in outputs]
    confidence = round(sum(active_confs) / len(active_confs), 3) if active_confs else 0.0

    return CompoundResult(
        pattern="drug_conflict",
        detected=detected,
        confidence=confidence,
        agents_contributing=agents_contributing,
        conflict_detected=conflict_detected,
        conflict_agents=conflict_agents,
        conflict_description=conflict_description,
        resolution_directive=resolution_directive,
        action_tier=action_tier,
        recommended_action=recommended_action
    )

def detect_fluid_overload(outputs: Dict[str, AgentOutput]) -> CompoundResult:
    pha = outputs.get("pha")
    vas = outputs.get("vas")
    nla = outputs.get("nla")
    lra = outputs.get("lra")

    # check PHA: total IV fluid > 6L in 24h
    total_iv = 0.0
    if pha:
        total_iv = pha.data.get("total_iv_24h_liters") or pha.data.get("total_iv_24h") or 0.0
    pha_overload = total_iv > 6.0

    # check VAS: spo2_trending (declining) AND rr > 25
    spo2_declining = bool(vas and "spo2_trending" in vas.escalation_flags)
    rr_val = vas.data.get("rr", 0) if vas else 0
    rr_gt_25 = rr_val > 25
    vas_respiratory = spo2_declining and rr_gt_25

    # check NLA: keywords crackles, edema, decreased breath sounds
    fluid_keywords = ["crackles", "edema", "decreased breath sounds"]
    nla_kws = nla.data.get("deterioration_keywords_found", []) if nla else []
    nla_fluid_match = any(kw in fluid_keywords for kw in nla_kws)

    # Optional LRA: bnp_high
    bnp_high = bool(lra and "bnp_high" in lra.escalation_flags)

    # Triggers
    three_agent_trigger = pha_overload and vas_respiratory and nla_fluid_match
    two_agent_trigger = pha_overload and vas_respiratory
    detected = three_agent_trigger or two_agent_trigger

    agents_contributing = []
    if pha_overload: agents_contributing.append("pha")
    if vas_respiratory: agents_contributing.append("vas")
    if nla_fluid_match: agents_contributing.append("nla")
    if bnp_high: agents_contributing.append("lra")

    if detected:
        if three_agent_trigger:
            action_tier = 3
        else:
            action_tier = 2
        recommended_action = "Fluid balance review · Diuresis consider · CXR order"
    else:
        action_tier = 1
        recommended_action = ""

    active_confs = [outputs[a].confidence for a in agents_contributing if a in outputs]
    confidence = round(sum(active_confs) / len(active_confs), 3) if active_confs else 0.0

    return CompoundResult(
        pattern="fluid_overload",
        detected=detected,
        confidence=confidence,
        agents_contributing=agents_contributing,
        conflict_detected=False,
        conflict_agents=[],
        conflict_description="",
        resolution_directive="",
        action_tier=action_tier,
        recommended_action=recommended_action
    )
