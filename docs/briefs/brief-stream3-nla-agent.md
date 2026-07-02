# Agent Brief — Stream 3: NLA Agent — BioClinicalBERT NLP Pipeline
## Notes / NLP Agent — Full Implementation (Replaces Stream 1 Stub)

**Status:** Ready to build — awaiting go signal
**Prepared:** 2026-07-01
**Dependency:** Stream 1 must be complete before Stream 3 runs — this brief replaces the NLA stub

---

## What You Are Building

The full implementation of the NLA (Notes / NLP Agent) for the mSignals ICU monitoring system. Stream 1 built a stub for this agent. This stream replaces that stub with a real NLP pipeline using BioClinicalBERT — a BERT model pretrained on clinical notes — to classify ICU nursing and physician notes for deterioration signals.

You will:
1. Implement `verticals/msignals/src/agents/nla.py` — replacing the stub with BioClinicalBERT inference
2. Build a text preprocessing pipeline for ICU clinical notes
3. Implement two classification heads: (a) sentiment classifier, (b) deterioration keyword detector
4. Build a fallback keyword regex pipeline (used when GPU/model not available)
5. Write evaluation tests against 20 labeled synthetic notes

---

## Context You Need

### Why NLA Matters in the System

The NLA agent covers the one data domain that no other agent touches: what clinicians write down. A patient can have normal vital signs and normal labs while a nurse documents "increased work of breathing, using accessory muscles, distressed" — that documentation is the early respiratory failure warning. No existing ICU monitoring system ingests clinical notes in real time.

NLA is also the most uncertain agent (lowest confidence threshold: 0.70; gate threshold: 0.50). Clinical notes are:
- Asynchronous (written hours after the observed event)
- Subjective (language varies by clinician)
- Inconsistently structured (mix of templates and free text)

This means NLA is the most likely agent to be suppressed by the Governor Contract's gate threshold — and that's correct behavior. NLA adds signal at the margin. It should not drive decisions alone.

### Integration Point — Stream 1 Interface

Stream 1 defined the following interface (in `verticals/msignals/src/agents/nla.py`):

```python
@dataclass
class NLAOutput:
    note_count: int
    last_note_text: str
    sentiment: str                       # 'neutral' | 'negative' | 'positive'
    deterioration_keywords_found: list[str]
    confidence: float
    nlp_model: str                       # 'bioclinicalbert' | 'regex_fallback' | 'mock'

class NLAAgent(ICUAgent):
    def fetch(self, patient_id: str, notes: list[str] | None = None) -> AgentOutput:
        # Stream 1 stub: returns mock values
        # Stream 3: replace this implementation with real NLP
```

You must replace the stub body of `fetch()`. The signature, `AgentOutput` schema, escalation flag names, TTL, and threshold values are fixed by Stream 1 — do not change them.

### Read Before Building

```
# Stream 1 NLA stub to replace:
verticals/msignals/src/agents/nla.py

# Base class and AgentOutput schema:
verticals/msignals/src/agents/base.py

# Full clinical spec for NLA escalation conditions (section 3 agent contracts):
verticals/msignals/docs/msignals-whitepaper.md

# Build plan NLA spec (Phase 0.2):
verticals/msignals/docs/msignals-build-plan.md
```

---

## Decisions Already Made

- **Model:** `emilyalsentzer/Bio_ClinicalBERT` from HuggingFace. Open weights, no API key required, runs on CPU or CUDA. Do not use any commercial NLP API (Azure, AWS, OpenAI).
- **Device:** CPU by default. Detect CUDA and use it if available (`torch.cuda.is_available()`). Do not hardcode device.
- **Fallback:** If the model cannot be loaded (no transformers installed, no network on first run, OOM), fall back to the regex keyword pipeline. Set `nlp_model: 'regex_fallback'` in output. This is a degraded mode, not a failure.
- **Model download:** Use HuggingFace `transformers` auto-download. Do not commit model weights. The model downloads on first run to the HuggingFace cache (`~/.cache/huggingface/`).
- **MIMIC noteevents:** NLA reads from MIMIC `noteevents.csv` (free-text `text` column) via the `PatientStream` class from Stream 1. If MIMIC data is not available, `fetch()` receives `notes=None` or an empty list — fall back to mock output with `nlp_model: 'mock'`.

---

## Implementation

### 1. Model Loading (`src/agents/nla.py`)

```python
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import re
from functools import lru_cache

MODEL_ID = 'emilyalsentzer/Bio_ClinicalBERT'
MAX_TOKEN_LENGTH = 512

@lru_cache(maxsize=1)
def _load_model():
    """Load once, reuse across calls. Returns None if model unavailable."""
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        # For PoC: use the base model for embedding + simple classification head
        # (not fine-tuned — zero-shot classification via cosine similarity to label embeddings)
        from transformers import AutoModel
        model = AutoModel.from_pretrained(MODEL_ID)
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = model.to(device)
        model.eval()
        return tokenizer, model, device
    except Exception:
        return None
```

### 2. Zero-Shot Deterioration Classification (No Fine-Tuning Required)

For the PoC, use embedding similarity rather than a fine-tuned classification head. This requires no labeled training data and no GPU training.

Approach:
1. Encode the input note with BioClinicalBERT to get a [CLS] embedding
2. Encode each label description to get label embeddings
3. Classify by cosine similarity to the label with highest similarity

Label descriptions for sentiment:
```python
SENTIMENT_LABELS = {
    'negative': 'Patient is deteriorating, in distress, or has worsening symptoms',
    'neutral':  'Patient is stable, comfortable, or without significant change',
    'positive': 'Patient is improving, recovering, or responding to treatment',
}
```

Label descriptions for deterioration (binary — present/absent):
```python
DETERIORATION_LABEL = 'Patient showing signs of clinical deterioration, respiratory distress, altered mental status, or hemodynamic instability'
NO_DETERIORATION_LABEL = 'Patient is clinically stable without signs of acute deterioration'
```

```python
def _embed(text: str, tokenizer, model, device: str) -> torch.Tensor:
    inputs = tokenizer(text, return_tensors='pt', truncation=True,
                       max_length=MAX_TOKEN_LENGTH, padding=True).to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state[:, 0, :]  # [CLS] token

def _cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    return torch.nn.functional.cosine_similarity(a, b).item()

def classify_note(text: str) -> tuple[str, float, bool]:
    """
    Returns: (sentiment, confidence, deterioration_detected)
    Falls back to regex if model unavailable.
    """
    loaded = _load_model()
    if loaded is None:
        return _regex_fallback(text)
    
    tokenizer, model, device = loaded
    note_emb = _embed(text, tokenizer, model, device)
    
    # Sentiment
    label_sims = {label: _cosine_sim(note_emb, _embed(desc, tokenizer, model, device))
                  for label, desc in SENTIMENT_LABELS.items()}
    sentiment = max(label_sims, key=label_sims.get)
    
    # Deterioration
    det_sim = _cosine_sim(note_emb, _embed(DETERIORATION_LABEL, tokenizer, model, device))
    no_det_sim = _cosine_sim(note_emb, _embed(NO_DETERIORATION_LABEL, tokenizer, model, device))
    deterioration_detected = det_sim > no_det_sim
    
    # Confidence: based on margin between top-2 label similarities
    sorted_sims = sorted(label_sims.values(), reverse=True)
    margin = sorted_sims[0] - sorted_sims[1]
    confidence = min(0.70 + margin * 2.0, 0.95)  # scale margin to 0.70–0.95 range
    
    return sentiment, confidence, deterioration_detected
```

### 3. Keyword Detection (Both NLP and Regex Paths)

Run keyword detection on every note regardless of whether NLP is available. Keywords are the escalation signal that the coordinator uses for compound rules.

```python
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

def extract_keywords(text: str) -> list[str]:
    """Case-insensitive substring match. Returns matched keywords."""
    text_lower = text.lower()
    return [kw for kw in DETERIORATION_KEYWORDS if kw in text_lower]
```

### 4. Regex Fallback (when model unavailable)

```python
def _regex_fallback(text: str) -> tuple[str, float, bool]:
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
```

### 5. Main `fetch()` Implementation

```python
def fetch(self, patient_id: str, notes: list[str] | None = None) -> AgentOutput:
    fetched_at = datetime.now(UTC)
    
    # If no notes provided (MIMIC unavailable), return mock
    if not notes:
        return self._mock_output(fetched_at)
    
    all_keywords: list[str] = []
    sentiments: list[str] = []
    confidences: list[float] = []
    nlp_model_used = 'mock'
    
    for note in notes[-5:]:  # Process at most last 5 notes (recency bias)
        keywords = extract_keywords(note)
        all_keywords.extend(kw for kw in keywords if kw not in all_keywords)
        
        try:
            sentiment, conf, deterioration = classify_note(note)
            nlp_model_used = 'bioclinicalbert'
        except Exception:
            sentiment, conf, deterioration = _regex_fallback(note)
            nlp_model_used = 'regex_fallback'
        
        sentiments.append(sentiment)
        confidences.append(conf)
    
    # Aggregate: take worst-case sentiment, mean confidence
    final_sentiment = 'negative' if 'negative' in sentiments else \
                      'positive' if all(s == 'positive' for s in sentiments) else 'neutral'
    final_confidence = sum(confidences) / len(confidences) if confidences else 0.50
    
    escalation_flags = []
    if final_sentiment == 'negative':
        escalation_flags.append('negative_clinical_sentiment')
    if all_keywords:
        escalation_flags.append('deterioration_keyword')
    
    return AgentOutput(
        agent_id='nla',
        domain='clinical_notes',
        source='noteevents',
        fetched_at=fetched_at,
        freshness_status='fresh',   # caller is responsible for TTL check
        confidence=self._apply_staleness(final_confidence, fetched_at),
        raw_confidence=final_confidence,
        stale_seconds=0,
        escalation_flags=escalation_flags,
        raw_text=f"Last {len(notes)} note(s). Sentiment: {final_sentiment}. "
                 f"Keywords: {', '.join(all_keywords) if all_keywords else 'none'}.",
        data={
            'note_count': len(notes),
            'last_note_text': notes[-1][:500] if notes else '',
            'sentiment': final_sentiment,
            'deterioration_keywords_found': all_keywords,
            'nlp_model': nlp_model_used,
        }
    )
```

---

## Test Requirements (`tests/test_nla.py`)

Write 20 labeled test cases. Run in two modes: model-available (BioClinicalBERT) and model-unavailable (regex fallback forced via mock). Both modes must produce the correct escalation flag for each case.

### Test Cases

```python
LABELED_NOTES = [
    # Format: (note_text, expected_sentiment, expected_keywords_present, expected_det_flag)
    
    # Clear deterioration — should always detect
    ("Patient increasingly agitated, pulling at lines. Increased work of breathing noted. Accessory muscles visible.", 
     'negative', ['increased work of breathing', 'accessory muscles'], True),
    
    ("Unresponsive to verbal stimuli. BP 74/40. Diaphoretic. Mottled lower extremities.",
     'negative', ['unresponsive', 'diaphoretic', 'mottled'], True),
    
    ("SpO2 declining despite O2 increase. Crackles bilaterally. Respiratory distress.",
     'negative', ['crackles', 'respiratory distress'], True),
    
    ("Patient confused and disoriented x2. States 'I can't breathe.' RR 28.",
     'negative', ['confused', 'disoriented', 'dyspnea'], True),
    
    ("Significant edema bilateral lower extremities, pitting 2+. Decreased urine output 15ml/hr.",
     'negative', ['edema', 'decreased urine output'], True),
    
    ("Patient worsening from this morning. More lethargic, not responding to questions normally.",
     'negative', ['worsening', 'lethargic'], True),
    
    ("Labored breathing with nasal flaring. Patient stating she is in pain, rates 8/10.",
     'negative', ['labored breathing', 'in pain'], True),
    
    ("Cool extremities noted. Tachycardic at 128 bpm. Patient looks unwell.",
     'negative', ['cool extremities', 'tachycardic'], True),
    
    # Borderline — single keyword, low severity
    ("Patient reports mild shortness of breath with exertion. Resting comfortably.",
     'neutral', ['shortness of breath'], False),   # context negates: 'resting comfortably'
    
    ("Trace edema bilateral feet, unchanged from prior shift.",
     'neutral', ['edema'], False),    # static — 'unchanged'
    
    # Clear stable — should never trigger
    ("Patient resting comfortably. Alert and oriented x3. Tolerating clear liquids.",
     'neutral', [], False),
    
    ("Good shift overall. Patient ambulated in hallway x2. Vital signs stable.",
     'neutral', [], False),
    
    ("Patient reports improved pain control. SpO2 98% on room air. No complaints.",
     'positive', [], False),
    
    ("Overnight uneventful. Patient slept well. No acute events to report.",
     'neutral', [], False),
    
    ("Respiratory status improved from yesterday. Off supplemental O2. Patient pleased.",
     'positive', [], False),
    
    ("Patient cooperating with care, following commands. Eating lunch without difficulty.",
     'neutral', [], False),
    
    ("Foley output adequate at 60ml/hr. No edema. Ambulated with PT this afternoon.",
     'neutral', [], False),
    
    ("Temperature normalized. Patient afebrile x12h. Blood cultures finalized — no growth.",
     'positive', [], False),
    
    # Template/minimal notes — low signal, should not escalate
    ("Nursing assessment completed. See flowsheet for vitals.",
     'neutral', [], False),
    
    ("Patient transferred from OSH. Records reviewed. Plan discussed with team.",
     'neutral', [], False),
]
```

### Test Structure

```python
def test_nla_with_regex_fallback():
    """Force regex mode by patching _load_model to return None."""
    # For each labeled note:
    # - Run fetch() with notes=[note_text]
    # - Assert escalation_flags match expected_det_flag
    # - Assert sentiment matches (within regex accuracy limits — allow 2 mismatches)
    # - Assert nlp_model == 'regex_fallback'

def test_nla_keyword_extraction():
    """Test keyword extractor directly — no model dependency."""
    # Assert exact keyword match for clear deterioration notes
    # Assert empty list for stable notes

def test_nla_empty_notes():
    """fetch() with notes=[] or notes=None returns mock output, not an error."""
    
def test_nla_long_note_truncation():
    """Note longer than 512 tokens is truncated without crashing."""
    
def test_nla_confidence_bounds():
    """Confidence is always in [0.0, 1.0] after staleness penalty."""

def test_nla_multiple_notes_worst_case():
    """3 notes: 2 stable + 1 deterioration → final_sentiment='negative', escalation set."""
```

---

## Dependencies to Add

Add to `verticals/msignals/requirements.txt` (create if it doesn't exist):

```
torch>=2.2.0
transformers>=4.40.0
tokenizers>=0.19.0
```

These are optional dependencies for the NLA agent. The system should work without them (regex fallback). Do not add to the main MAS requirements — they are NLA-specific.

---

## Performance Notes

- BioClinicalBERT inference on CPU: ~200–500ms per note (512 tokens max)
- In the PoC, this is acceptable — NLA is event-driven (not continuous like VAS)
- The `@lru_cache` on `_load_model()` ensures the model loads once per process lifetime
- Label embeddings for the zero-shot classification are computed on every call — cache them the same way if performance becomes an issue

---

## Success Criteria

- [ ] `from verticals.msignals.src.agents.nla import NLAAgent` works with and without `torch`/`transformers` installed
- [ ] With transformers installed: `nlp_model` in output is `'bioclinicalbert'`
- [ ] Without transformers installed: `nlp_model` is `'regex_fallback'`, no import error, no crash
- [ ] All 8 clear deterioration test cases produce `'deterioration_keyword'` in `escalation_flags`
- [ ] All 10 stable/neutral test cases produce empty `escalation_flags`
- [ ] `fetch(patient_id='x', notes=None)` returns a valid `AgentOutput` with `nlp_model: 'mock'`
- [ ] `fetch(patient_id='x', notes=['note text longer than 512 tokens...'])` does not raise
- [ ] All tests pass: `python -m pytest verticals/msignals/tests/test_nla.py -v`

## What NOT to Build

- Do NOT fine-tune BioClinicalBERT — zero-shot embedding similarity only for the PoC
- Do NOT build a training pipeline or dataset loader
- Do NOT integrate with the MIMIC noteevents loader — that's `PatientStream` (Stream 1). Accept `notes: list[str]` as a parameter.
- Do NOT modify any other agents — NLA stub replacement only
- Do NOT change the `AgentOutput` schema or the `ICUAgent` base class — Stream 1 owns those
- Do NOT add any FastAPI endpoints — backend API is out of scope for this stream
