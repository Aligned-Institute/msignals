import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from .agents.base import AgentOutput, ICUAgent
from .agents.vas import VASAgent
from .agents.lra import LRAAgent
from .agents.pha import PHAAgent
from .agents.nla import NLAAgent
from .agents.hia import HIAAgent

from .governor.contracts_icu import get_contract, requires_gate, passes_publish_threshold
from .rules.compound import (
    CompoundResult,
    detect_sepsis,
    detect_aki,
    detect_respiratory_failure,
    detect_drug_conflict,
    detect_fluid_overload,
)

logger = logging.getLogger(__name__)

@dataclass
class ICUAlignedState:
    patient_id: str
    version: int
    agent_outputs: Dict[str, AgentOutput]
    compound_results: List[CompoundResult]
    conflicts: List[CompoundResult]       # subset where conflict_detected=True
    aggregate_confidence: float           # weighted mean of contributing agent confidences
    aligned_at: datetime
    state_hash: str                       # sha256 of the serialized aligned state
    highest_action_tier: int              # max tier across all compound results


class ICUCoordinator:
    """
    The ICU Clinical Coordinator for mSignals.
    Collects outputs from VAS, LRA, PHA, NLA, HIA agents, aligns them temporally,
    detects compound clinical deterioration states and active conflicts, and produces
    the unified patient state.
    """

    def __init__(self, tenant_id: str = "default-tenant"):
        self.tenant_id = tenant_id
        self._versions: Dict[str, int] = {}
        self.agents: Dict[str, ICUAgent] = {
            "vas": VASAgent(tenant_id),
            "lra": LRAAgent(tenant_id),
            "pha": PHAAgent(tenant_id),
            "nla": NLAAgent(tenant_id),
            "hia": HIAAgent(tenant_id),
        }

    async def align(
        self,
        patient_id: str,
        notes: Optional[List[str]] = None,
        evaluation_time: Optional[datetime] = None,
        **kwargs
    ) -> ICUAlignedState:
        eval_time = evaluation_time or datetime.now(timezone.utc)
        
        # 1. Fetch from all agents concurrently
        # We pass notes to NLA and other context to fetch
        tasks = [
            self.agents["vas"].fetch(patient_id, evaluation_time=eval_time, **kwargs),
            self.agents["lra"].fetch(patient_id, evaluation_time=eval_time, **kwargs),
            self.agents["pha"].fetch(patient_id, evaluation_time=eval_time, **kwargs),
            self.agents["nla"].fetch(patient_id, notes=notes, evaluation_time=eval_time, **kwargs),
            self.agents["hia"].fetch(patient_id, evaluation_time=eval_time, **kwargs),
        ]
        
        raw_outputs = await asyncio.gather(*tasks)
        agent_outputs: Dict[str, AgentOutput] = {
            out.agent_id: out for out in raw_outputs
        }

        # 2. Temporal Alignment: re-verify and apply staleness penalty at evaluation_time
        for agent_id, output in agent_outputs.items():
            agent_inst = self.agents[agent_id]
            agent_outputs[agent_id] = agent_inst._apply_staleness_penalty(output, eval_time)

        # 3. Evaluate Compound Detection Rules
        compound_results = [
            detect_sepsis(agent_outputs),
            detect_aki(agent_outputs),
            detect_respiratory_failure(agent_outputs),
            detect_drug_conflict(agent_outputs),
            detect_fluid_overload(agent_outputs),
        ]

        # 4. Extract Conflicts (detected compound results with conflict flag active)
        conflicts = [res for res in compound_results if res.conflict_detected]

        # 5. Calculate Aggregate Confidence
        # Use average of all agents, with a -0.04 penalty if any conflict is present
        base_confs = [out.confidence for out in agent_outputs.values()]
        avg_conf = sum(base_confs) / len(base_confs) if base_confs else 0.0
        
        if conflicts:
            avg_conf -= 0.04
            
        aggregate_confidence = round(max(0.0, min(1.0, avg_conf)), 3)

        # 6. Highest Action Tier
        highest_action_tier = max(res.action_tier for res in compound_results) if compound_results else 1

        # 7. Increment Version for Patient
        version = self._versions.get(patient_id, 0) + 1
        self._versions[patient_id] = version

        # 8. Deterministic Hash of State
        state_hash = self._generate_state_hash(patient_id, agent_outputs, compound_results)

        return ICUAlignedState(
            patient_id=patient_id,
            version=version,
            agent_outputs=agent_outputs,
            compound_results=compound_results,
            conflicts=conflicts,
            aggregate_confidence=aggregate_confidence,
            aligned_at=eval_time,
            state_hash=state_hash,
            highest_action_tier=highest_action_tier
        )

    def _generate_state_hash(
        self,
        patient_id: str,
        agent_outputs: Dict[str, AgentOutput],
        compound_results: List[CompoundResult]
    ) -> str:
        serialized_agents = {
            aid: {
                "freshness_status": out.freshness_status,
                "confidence": out.confidence,
                "escalation_flags": out.escalation_flags,
                "data": out.data
            }
            for aid, out in sorted(agent_outputs.items())
        }
        serialized_results = [
            {
                "pattern": res.pattern,
                "detected": res.detected,
                "confidence": res.confidence,
                "action_tier": res.action_tier
            }
            for res in sorted(compound_results, key=lambda x: x.pattern)
        ]
        payload = json.dumps({
            "patient_id": patient_id,
            "agents": serialized_agents,
            "results": serialized_results
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
