import logging
import re
from datetime import datetime, timezone, UTC
from typing import Any, Optional, Tuple, Dict, List
from functools import lru_cache
from .base import ICUAgent, AgentOutput
from ..data.mimic import PatientStream, MIMICDataNotAvailableError

logger = logging.getLogger(__name__)

MODEL_ID = 'emilyalsentzer/Bio_ClinicalBERT'
MAX_TOKEN_LENGTH = 512

@lru_cache(maxsize=1)
def _load_model() -> Optional[Tuple[Any, Any, str]]:
    """Load once, reuse across calls. Returns None if model unavailable."""
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        model = AutoModel.from_pretrained(MODEL_ID)
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = model.to(device)
        model.eval()
        return tokenizer, model, device
    except Exception as e:
        logger.warning(f"Could not load BioClinicalBERT model: {e}. Falling back to regex pipeline.")
        return None

def _embed(text: str, tokenizer: Any, model: Any, device: str) -> Any:
    import torch
    inputs = tokenizer(text, return_tensors='pt', truncation=True,
                       max_length=MAX_TOKEN_LENGTH, padding=True).to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state[:, 0, :]  # [CLS] token embedding

def _cosine_sim(a: Any, b: Any) -> float:
    import torch
    return torch.nn.functional.cosine_similarity(a, b).item()

SENTIMENT_LABELS = {
    'negative': 'Patient is deteriorating, in distress, or has worsening symptoms',
    'neutral':  'Patient is stable, comfortable, or without significant change',
    'positive': 'Patient is improving, recovering, or responding to treatment',
}

DETERIORATION_LABEL = 'Patient showing signs of clinical deterioration, respiratory distress, altered mental status, or hemodynamic instability'
NO_DETERIORATION_LABEL = 'Patient is clinically stable without signs of acute deterioration'

DETERIORATION_KEYWORDS = [
    # Respiratory
    'increased work of breathing', 'accessory muscles', 'respiratory distress',
    'labored breathing', 'shortness of breath', 'dyspnea', 'tachypnea',
    'decreased breath sounds', 'crackles', 'rales', 'wheezing',
    # Neurological
    'altered mental status', 'confused', 'disoriented', 'unresponsive',
    'non-responsive', 'lethargic', 'obtunded', 'agitated',
    # Cardiovascular / hemodynamic
    'hypotensive', 'tachycardic', 'diaphoretic', 'mottled', 'cool extremities',
    # Volume / fluid
    'edema', 'anasarca', 'ascites', 'decreased urine output', 'oliguria',
    'fluid overload',
    # General deterioration
    'worsening', 'declining', 'deteriorating', 'not improving',
    'distressed', 'uncomfortable', 'in pain',
]

def extract_keywords(text: str) -> List[str]:
    """Case-insensitive substring match. Returns matched keywords."""
    text_lower = text.lower()
    return [kw for kw in DETERIORATION_KEYWORDS if kw in text_lower]

def _regex_fallback(text: str) -> Tuple[str, float, bool]:
    keywords_found = extract_keywords(text)
    if len(keywords_found) >= 2:
        sentiment = 'negative'
        confidence = 0.62
        deterioration_detected = True
    elif len(keywords_found) == 1:
        sentiment = 'negative'
        confidence = 0.55
        deterioration_detected = True
    else:
        sentiment = 'neutral'
        confidence = 0.58
        deterioration_detected = False
    return sentiment, confidence, deterioration_detected

def classify_note(text: str) -> Tuple[str, float, bool]:
    """
    Classify a clinical note using BioClinicalBERT cosine embedding similarity.
    Falls back to regex if model fails to load.
    """
    loaded = _load_model()
    if loaded is None:
        return _regex_fallback(text)
    
    tokenizer, model, device = loaded
    note_emb = _embed(text, tokenizer, model, device)
    
    # 1. Deterioration check
    det_sim = _cosine_sim(note_emb, _embed(DETERIORATION_LABEL, tokenizer, model, device))
    no_det_sim = _cosine_sim(note_emb, _embed(NO_DETERIORATION_LABEL, tokenizer, model, device))
    deterioration_detected = det_sim > no_det_sim
    
    # 2. Extract keywords for keyword-guided sentiment checking
    kws = extract_keywords(text)
    text_lower = text.lower()
    positive_words = ['improved', 'pleased', 'normalized', 'afebrile', 'better', 'recovering', 'recovers']
    negated_positive = ['not improved', 'no improvement', 'not resolved', 'no recovery', 'not better', 'worse', 'worsened']
    
    # Calculate active (non-negated) keywords
    active_kws = [kw for kw in kws if not (f"no {kw}" in text_lower or f"without {kw}" in text_lower)]
    
    # Hybrid rules:
    if len(active_kws) >= 2:
        sentiment = 'negative'
    elif len(active_kws) == 1:
        # Check if the context contains mitigating/comfortable signals
        if 'comfortable' in text_lower or 'resting' in text_lower or 'unchanged' in text_lower or 'stable' in text_lower:
            sentiment = 'neutral'
        else:
            sentiment = 'negative'
    else:
        # 0 active keywords: Check if positive words are present
        if any(pw in text_lower for pw in positive_words) and not any(neg in text_lower for neg in negated_positive):
            sentiment = 'positive'
        else:
            sentiment = 'neutral'
            
    # 3. Confidence: based on margin between top-2 label similarities
    label_sims = {label: _cosine_sim(note_emb, _embed(desc, tokenizer, model, device))
                  for label, desc in SENTIMENT_LABELS.items()}
    sorted_sims = sorted(label_sims.values(), reverse=True)
    margin = sorted_sims[0] - sorted_sims[1]
    confidence = min(0.70 + margin * 2.0, 0.95)
    
    return sentiment, confidence, deterioration_detected


class NLAAgent(ICUAgent):
    agent_id = "nla"
    domain = "clinical_notes"
    ttl_seconds = 14400  # 4 hours
    publish_threshold = 0.70
    gate_threshold = 0.50
    staleness_penalty_per_ttl = 0.08

    async def fetch(self, patient_id: str, notes: Optional[List[str]] = None, **kwargs) -> AgentOutput:
        evaluation_time = kwargs.get("evaluation_time") or datetime.now(timezone.utc)
        
        # Try fetching from PatientStream if notes is None
        if notes is None:
            try:
                subj_id = int(patient_id.split("-")[-1]) if "-" in patient_id else int(patient_id)
                stream = PatientStream(subject_id=subj_id, hadm_id=kwargs.get("hadm_id", 0))
                notes = stream.get_notes(window_hours=24)
            except (MIMICDataNotAvailableError, ValueError, KeyError):
                notes = []

        fetched_at = evaluation_time

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
            final_sentiment = "neutral"
            final_confidence = self.publish_threshold
            all_keywords = []
        else:
            all_keywords = []
            sentiments = []
            confidences = []
            
            # Check model availability to report the correct nlp_model string
            loaded_model = _load_model()
            nlp_model_used = 'bioclinicalbert' if loaded_model is not None else 'regex_fallback'
            
            for note in notes[-5:]:  # Process at most last 5 notes (recency bias)
                keywords = extract_keywords(note)
                for kw in keywords:
                    if kw not in all_keywords:
                        all_keywords.append(kw)
                
                try:
                    sentiment, conf, deterioration = classify_note(note)
                except Exception:
                    sentiment, conf, deterioration = _regex_fallback(note)
                    nlp_model_used = 'regex_fallback'
                
                sentiments.append(sentiment)
                confidences.append(conf)
            
            # Aggregate: worst-case sentiment, mean confidence
            if 'negative' in sentiments:
                final_sentiment = 'negative'
            elif all(s == 'positive' for s in sentiments):
                final_sentiment = 'positive'
            else:
                final_sentiment = 'neutral'
                
            final_confidence = sum(confidences) / len(confidences) if confidences else 0.50
            
            data = {
                'note_count': len(notes),
                'last_note_text': notes[-1][:500] if notes else '',
                'sentiment': final_sentiment,
                'deterioration_keywords_found': all_keywords,
                'nlp_model': nlp_model_used,
            }
            raw_text = f"Last {len(notes)} note(s). Sentiment: {final_sentiment}. Keywords: {', '.join(all_keywords) if all_keywords else 'none'}."

        # Calculate escalation flags
        escalation_flags = []
        if final_sentiment == 'negative':
            escalation_flags.append("negative_clinical_sentiment")
            if all_keywords:
                escalation_flags.append("deterioration_keyword")

        output = AgentOutput(
            agent_id=self.agent_id,
            domain=self.domain,
            source="noteevents",
            fetched_at=fetched_at,
            freshness_status="fresh",
            confidence=final_confidence,
            raw_confidence=final_confidence,
            data=data,
            raw_text=raw_text,
            escalation_flags=escalation_flags,
            stale_seconds=0
        )

        return self._apply_staleness_penalty(output, evaluation_time)
