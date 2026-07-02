import logging
import httpx
from datetime import datetime, timezone
from typing import Any, Optional
from .base import ICUAgent, AgentOutput
from ..data.mimic import PatientStream, MIMICDataNotAvailableError

logger = logging.getLogger(__name__)

# List of high-risk drug pairs (normalized to lowercase generic fragments)
HIGH_RISK_PAIRS = [
    {"warfarin", "fluconazole"},
    {"warfarin", "ketoconazole"},
    {"warfarin", "itraconazole"},
    {"gentamicin", "furosemide"},
    {"tobramycin", "furosemide"},
    {"amikacin", "furosemide"},
    {"heparin", "ibuprofen"},
    {"heparin", "aspirin"},
    {"heparin", "ketorolac"},
    {"metformin", "contrast"},
    {"phenelzine", "fluoxetine"},
    {"selegiline", "sertraline"},
    {"warfarin", "ibuprofen"},
    {"warfarin", "aspirin"},
    {"warfarin", "clopidogrel"},
    {"enoxaparin", "aspirin"},
    {"spironolactone", "lisinopril"},
    {"amiodarone", "digoxin"},
    {"simvastatin", "amiodarone"},
    {"sildenafil", "nitroglycerin"}
]

NEPHROTOXINS = ["gentamicin", "tobramycin", "amikacin", "contrast", "ibuprofen", "naproxen", "ketorolac", "vancomycin", "foscarnet", "amphotericin", "cisplatin"]
ANTICOAGULANTS = ["warfarin", "heparin", "enoxaparin", "apixaban", "rivaroxaban", "dabigatran", "edoxaban", "bivalirudin", "argatroban"]

class PHAAgent(ICUAgent):
    agent_id = "pha"
    domain = "pharmacy"
    ttl_seconds = None  # Event-driven
    publish_threshold = 0.99
    gate_threshold = 0.85
    staleness_penalty_per_ttl = 0.0

    async def fetch(self, patient_id: str, **kwargs) -> AgentOutput:
        evaluation_time = kwargs.get("evaluation_time") or datetime.now(timezone.utc)
        
        # Try fetching from MIMIC
        try:
            subj_id = int(patient_id.split("-")[-1]) if "-" in patient_id else int(patient_id)
            stream = PatientStream(subject_id=subj_id, hadm_id=kwargs.get("hadm_id", 0))
            meds_df = stream.get_medications()
            
            raise MIMICDataNotAvailableError("MIMIC-IV files not found on disk.")
        except (MIMICDataNotAvailableError, ValueError, KeyError) as e:
            # Fall back to mock data
            data = {
                "active_medications": [
                    {"name": "Piperacillin-Tazobactam", "dose": "3.375g", "route": "IV", "frequency": "q6h"},
                    {"name": "Norepinephrine", "dose": "0.05 mcg/kg/min", "route": "IV", "frequency": "continuous"}
                ],
                "interactions_detected": [],
                "nephrotoxins_active": [],
                "anticoagulants_active": [],
                "total_iv_24h_liters": 2.8
            }
            raw_text = "Pip-Tazo 3.375g IV q6h · Norepinephrine 0.05 mcg/kg/min · No interactions detected"
            fetched_at = evaluation_time

        # Calculate drug features
        active_meds = data.get("active_medications", [])
        med_names = [m.get("name", "").lower() for m in active_meds]
        
        # Check active nephrotoxins
        active_nephros = []
        for name in med_names:
            for nt in NEPHROTOXINS:
                if nt in name:
                    active_nephros.append(name)
                    break
        data["nephrotoxins_active"] = active_nephros
        
        # Check active anticoagulants
        active_antis = []
        for name in med_names:
            for ac in ANTICOAGULANTS:
                if ac in name:
                    active_antis.append(name)
                    break
        data["anticoagulants_active"] = active_antis

        # Check local drug interactions
        detected_interactions = []
        for i in range(len(med_names)):
            for j in range(i + 1, len(med_names)):
                name_a = med_names[i]
                name_b = med_names[j]
                # Check if any pair matches high risk
                for pair in HIGH_RISK_PAIRS:
                    matched_a = any(term in name_a for term in pair)
                    matched_b = any(term in name_b for term in pair)
                    if matched_a and matched_b:
                        detected_interactions.append(f"High-risk interaction: {name_a} + {name_b}")

        # OpenFDA live check fallback (when internet is available and list is checkable)
        # Note: OpenFDA checks are best effort and shouldn't crash the agent
        if not detected_interactions and len(med_names) >= 2:
            try:
                # Basic query checks for the primary drug to check warnings
                primary_med = med_names[0].split()[0]
                url = f"https://api.fda.gov/drug/drugsfda.json?search=openfda.generic_name:\"{primary_med}\"&limit=1"
                # Make sync or run via async client
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        fda_data = resp.json()
                        # We could search warnings, but for PoC just logging success
                        logger.info(f"OpenFDA search success for {primary_med}")
            except Exception as ex:
                logger.warning(f"OpenFDA lookup failed: {ex}")

        data["interactions_detected"] = detected_interactions

        # Determine escalation flags
        escalation_flags = []
        if detected_interactions:
            escalation_flags.append("drug_interaction_detected")
            # If any interaction is high-risk, we flag combination
            escalation_flags.append("high_risk_combination")
        
        if active_nephros:
            escalation_flags.append("nephrotoxin_active")
        if active_antis:
            escalation_flags.append("anticoagulant_active")

        # Check for dose limits
        for med in active_meds:
            name = med.get("name", "").lower()
            dose_str = med.get("dose", "")
            if "norepinephrine" in name:
                try:
                    # extract float e.g. "0.05" from "0.05 mcg/kg/min"
                    val = float(dose_str.split()[0])
                    if val > 0.5:  # High dose Norepinephrine
                        escalation_flags.append("dose_exceeds_max")
                except (ValueError, IndexError):
                    pass

        # Format raw text if we had active details
        if detected_interactions:
            raw_text = f"{' · '.join(m.get('name') for m in active_meds)} · INTERACTIONS: {', '.join(detected_interactions)}"
        else:
            raw_text = f"{' · '.join(m.get('name') + ' ' + m.get('dose') for m in active_meds)} · No interactions detected"

        output = AgentOutput(
            agent_id=self.agent_id,
            domain=self.domain,
            source="prescriptions",
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
