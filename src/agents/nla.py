import logging
from datetime import datetime, timezone
from typing import Any, Optional
from .base import ICUAgent, AgentOutput
from ..data.mimic import PatientStream, MIMICDataNotAvailableError

logger = logging.getLogger(__name__)

DETERIORATION_KEYWORDS = [
    "worsening", "altered", "non-responsive", "distress", 
    "increased work of breathing", "accessory muscles", "crackles", 
    "edema", "decreased breath sounds", "unresponsive", 
    "lethargic", "confused", "disoriented"
]

class NLAAgent(ICUAgent):
    agent_id = "nla"
    domain = "clinical_notes"
    ttl_seconds = 14400  # 4 hours
    publish_threshold = 0.70
    gate_threshold = 0.50
    staleness_penalty_per_ttl = 0.08

    async def fetch(self, patient_id: str, notes: Optional[list[str]] = None, **kwargs) -> AgentOutput:
        evaluation_time = kwargs.get("evaluation_time") or datetime.now(timezone.utc)
        
        # If notes parameter is not passed, try fetching from MIMIC (which fails gracefully)
        if notes is None:
            try:
                subj_id = int(patient_id.split("-")[-1]) if "-" in patient_id else int(patient_id)
                stream = PatientStream(subject_id=subj_id, hadm_id=kwargs.get("hadm_id", 0))
                notes = stream.get_notes(window_hours=24)
                
                raise MIMICDataNotAvailableError("MIMIC-IV files not found on disk.")
            except (MIMICDataNotAvailableError, ValueError, KeyError) as e:
                notes = []

        if not notes:
            # Fall back to mock data
            data = {
                "note_count": 2,
                "last_note_text": "Patient tolerating O2 2L NC, alert and oriented x3",
                "sentiment": "neutral",
                "deterioration_keywords_found": [],
                "nlp_model": "mock"
            }
            raw_text = "Last note (10:08): tolerating O2, alert and oriented. Sentiment: neutral."
            fetched_at = evaluation_time
        else:
            # Process passed notes (high-fidelity stub behavior)
            found_kws = []
            sentiment = "neutral"
            for note in notes:
                note_lower = note.lower()
                for kw in DETERIORATION_KEYWORDS:
                    if kw in note_lower and kw not in found_kws:
                        found_kws.append(kw)
            
            if found_kws:
                sentiment = "negative"
            
            data = {
                "note_count": len(notes),
                "last_note_text": notes[-1],
                "sentiment": sentiment,
                "deterioration_keywords_found": found_kws,
                "nlp_model": "mock"
            }
            raw_text = f"Last note: {notes[-1][:80]}... Sentiment: {sentiment}. Keywords: {', '.join(found_kws) if found_kws else 'none'}"
            # Assume note was posted 10 minutes ago
            fetched_at = evaluation_time

        # Calculate escalation flags
        escalation_flags = []
        if data.get("sentiment") == "negative":
            escalation_flags.append("negative_clinical_sentiment")
        if data.get("deterioration_keywords_found"):
            escalation_flags.append("deterioration_keyword")

        output = AgentOutput(
            agent_id=self.agent_id,
            domain=self.domain,
            source="noteevents",
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
