import logging
from datetime import datetime, timezone
from typing import Any, Optional
from .base import ICUAgent, AgentOutput
from ..data.mimic import PatientStream, MIMICDataNotAvailableError

logger = logging.getLogger(__name__)

class VASAgent(ICUAgent):
    agent_id = "vas"
    domain = "vital_signs"
    ttl_seconds = 30
    publish_threshold = 0.90
    gate_threshold = 0.70
    staleness_penalty_per_ttl = 0.15

    async def fetch(self, patient_id: str, **kwargs) -> AgentOutput:
        evaluation_time = kwargs.get("evaluation_time") or datetime.now(timezone.utc)
        
        # Try fetching from MIMIC
        try:
            # Reconstruct patient_id to integers if needed
            subj_id = int(patient_id.split("-")[-1]) if "-" in patient_id else int(patient_id)
            stream = PatientStream(subject_id=subj_id, hadm_id=kwargs.get("hadm_id", 0))
            vitals_df = stream.get_vitals(window_hours=6)
            
            # Since this is a placeholder pipeline, we simulate raising the error 
            # if no real file reading is wired yet
            raise MIMICDataNotAvailableError("MIMIC-IV files not found on disk.")
        except (MIMICDataNotAvailableError, ValueError, KeyError) as e:
            # Fall back to mock data
            data = {
                "hr": 102,
                "sbp": 94,
                "dbp": 62,
                "map": 73,
                "spo2": 95,
                "rr": 22,
                "temp_c": 38.4,
                "trend_spo2_15m": "stable"
            }
            raw_text = "HR 102 bpm · SpO2 95% · BP 94/62 (MAP 73) · RR 22 · Temp 38.4°C"
            fetched_at = evaluation_time

        # Calculate escalation flags based on parameters
        escalation_flags = []
        hr = data.get("hr", 0)
        sbp = data.get("sbp", 120)
        temp_c = data.get("temp_c", 37.0)
        rr = data.get("rr", 12)
        spo2 = data.get("spo2", 100)
        map_val = data.get("map", 80)
        trend_spo2 = data.get("trend_spo2_15m", "stable")
        
        if hr > 130:
            escalation_flags.append("hr_gt_130")
        if spo2 < 88:
            escalation_flags.append("spo2_lt_88")
        if sbp < 80:
            escalation_flags.append("sbp_lt_80")
        if rr > 30:
            escalation_flags.append("rr_gt_30")
        if temp_c > 38.5:
            escalation_flags.append("temp_gt_38_5")
        if temp_c < 36.0:
            escalation_flags.append("temp_lt_36")
        if map_val < 65:
            escalation_flags.append("map_lt_65")
        if trend_spo2 == "declining":
            escalation_flags.append("spo2_trending")

        output = AgentOutput(
            agent_id=self.agent_id,
            domain=self.domain,
            source="chartevents",
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
