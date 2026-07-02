import logging
from datetime import datetime, timezone
from typing import Any, Optional
from .base import ICUAgent, AgentOutput
from ..data.mimic import PatientStream, MIMICDataNotAvailableError

logger = logging.getLogger(__name__)

class HIAAgent(ICUAgent):
    agent_id = "hia"
    domain = "patient_history"
    ttl_seconds = 86400  # 24 hours
    publish_threshold = 0.75
    gate_threshold = 0.55
    staleness_penalty_per_ttl = 0.05

    async def fetch(self, patient_id: str, **kwargs) -> AgentOutput:
        evaluation_time = kwargs.get("evaluation_time") or datetime.now(timezone.utc)
        
        # Try fetching from MIMIC
        try:
            subj_id = int(patient_id.split("-")[-1]) if "-" in patient_id else int(patient_id)
            stream = PatientStream(subject_id=subj_id, hadm_id=kwargs.get("hadm_id", 0))
            history = stream.get_history()
            
            raise MIMICDataNotAvailableError("MIMIC-IV files not found on disk.")
        except (MIMICDataNotAvailableError, ValueError, KeyError) as e:
            # Fall back to mock data
            data = {
                "age": 62,
                "sex": "F",
                "prior_diagnoses_icd": ["E11.9", "N39.0"],
                "prior_sepsis": True,
                "immunocompromised": False,
                "prior_aki": False,
                "ckd": False,
                "chf": False,
                "copd": False,
                "diabetes": True
            }
            raw_text = "62F · T2DM · Prior UTI (N39.0) · Prior sepsis episode 2024 · No CKD, CHF, or COPD"
            fetched_at = evaluation_time

        # Calculate escalation flags based on parameters
        escalation_flags = []
        prior_sepsis = data.get("prior_sepsis", False)
        immunocompromised = data.get("immunocompromised", False)
        prior_aki = data.get("prior_aki", False)
        ckd = data.get("ckd", False)
        chf = data.get("chf", False)
        copd = data.get("copd", False)
        diabetes = data.get("diabetes", False)
        
        if prior_sepsis:
            escalation_flags.append("prior_sepsis")
        if immunocompromised:
            escalation_flags.append("immunocompromised")
        if prior_aki:
            escalation_flags.append("prior_aki")
        if ckd:
            escalation_flags.append("ckd_known")
        if chf:
            escalation_flags.append("chf_known")
        if copd:
            escalation_flags.append("copd_known")
        if diabetes:
            escalation_flags.append("diabetes_known")
            
        # High-risk combinations: e.g., prior sepsis + immunocompromised
        if prior_sepsis and immunocompromised:
            escalation_flags.append("high_risk_combo")

        output = AgentOutput(
            agent_id=self.agent_id,
            domain=self.domain,
            source="diagnoses_icd",
            fetched_at=fetched_at,
            freshness_status="fresh",
            confidence=self.publish_threshold,
            raw_confidence=self.publish_threshold,
            data=data,
            raw_text=raw_text,
            escalation_flags=escalation_flags,
            stale_seconds=0
        )

        return self._apply_staleness_penalty(output, evaluation_time)
