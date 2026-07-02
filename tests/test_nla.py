import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from verticals.msignals.src.agents.nla import NLAAgent, extract_keywords, _load_model
from verticals.msignals.src.agents.base import AgentOutput

# Labeled notes formatted as:
# (note_text, expected_sent_nlp, expected_sent_regex, expected_keywords, expected_flag_nlp, expected_flag_regex)
LABELED_NOTES = [
    # Clear deterioration — should always detect
    ("Patient increasingly agitated, pulling at lines. Increased work of breathing noted. Accessory muscles visible.", 
     'negative', 'negative', ['increased work of breathing', 'accessory muscles', 'agitated'], True, True),
    
    ("Unresponsive to verbal stimuli. BP 74/40. Diaphoretic. Mottled lower extremities.",
     'negative', 'negative', ['unresponsive', 'diaphoretic', 'mottled'], True, True),
    
    ("SpO2 declining despite O2 increase. Crackles bilaterally. Respiratory distress.",
     'negative', 'negative', ['crackles', 'respiratory distress', 'declining'], True, True),
    
    ("Patient confused and disoriented x2. States 'I can't breathe.' RR 28.",
     'negative', 'negative', ['confused', 'disoriented'], True, True),
    
    ("Significant edema bilateral lower extremities, pitting 2+. Decreased urine output 15ml/hr.",
     'negative', 'negative', ['edema', 'decreased urine output'], True, True),
    
    ("Patient worsening from this morning. More lethargic, not responding to questions normally.",
     'negative', 'negative', ['worsening', 'lethargic'], True, True),
    
    ("Labored breathing with nasal flaring. Patient stating she is in pain, rates 8/10.",
     'negative', 'negative', ['labored breathing', 'in pain'], True, True),
    
    ("Cool extremities noted. Tachycardic at 128 bpm. Patient looks unwell.",
     'negative', 'negative', ['cool extremities', 'tachycardic'], True, True),
    
    # Borderline — single keyword, low severity (fails context check in regex, passes in NLP)
    ("Patient reports mild shortness of breath with exertion. Resting comfortably.",
     'neutral', 'negative', ['shortness of breath'], False, True),
    
    ("Trace edema bilateral feet, unchanged from prior shift.",
     'neutral', 'negative', ['edema'], False, True),
    
    # Clear stable — should never trigger
    ("Patient resting comfortably. Alert and oriented x3. Tolerating clear liquids.",
     'neutral', 'neutral', [], False, False),
    
    ("Good shift overall. Patient ambulated in hallway x2. Vital signs stable.",
     'neutral', 'neutral', [], False, False),
    
    ("Patient reports improved pain control. SpO2 98% on room air. No complaints.",
     'positive', 'neutral', [], False, False),
    
    ("Overnight uneventful. Patient slept well. No acute events to report.",
     'neutral', 'neutral', [], False, False),
    
    ("Respiratory status improved from yesterday. Off supplemental O2. Patient pleased.",
     'positive', 'neutral', [], False, False),
    
    ("Patient cooperating with care, following commands. Eating lunch without difficulty.",
     'neutral', 'neutral', [], False, False),
    
    # Case 17: Negation check (regex matches 'edema' inside 'No edema', NLP correctly discounts it)
    ("Foley output adequate at 60ml/hr. No edema. Ambulated with PT this afternoon.",
     'neutral', 'negative', ['edema'], False, True),
    
    ("Temperature normalized. Patient afebrile x12h. Blood cultures finalized — no growth.",
     'positive', 'neutral', [], False, False),
    
    # Template/minimal notes — low signal, should not escalate
    ("Nursing assessment completed. See flowsheet for vitals.",
     'neutral', 'neutral', [], False, False),
    
    ("Patient transferred from OSH. Records reviewed. Plan discussed with team.",
     'neutral', 'neutral', [], False, False),
]

@pytest.mark.asyncio
async def test_nla_with_regex_fallback():
    """Force regex mode by patching _load_model to return None."""
    agent = NLAAgent()
    
    with patch('verticals.msignals.src.agents.nla._load_model', return_value=None):
        for note_text, expected_sent_nlp, expected_sent_regex, expected_kws, expected_flag_nlp, expected_flag_regex in LABELED_NOTES:
            output = await agent.fetch("patient-123", notes=[note_text])
            assert isinstance(output, AgentOutput)
            assert output.data['nlp_model'] == 'regex_fallback'
            assert output.data['sentiment'] == expected_sent_regex
            assert sorted(output.data['deterioration_keywords_found']) == sorted(expected_kws)
            
            if expected_flag_regex:
                assert 'deterioration_keyword' in output.escalation_flags
            else:
                assert 'deterioration_keyword' not in output.escalation_flags

@pytest.mark.asyncio
async def test_nla_with_model_inference():
    """Verify inference works on model path if torch/transformers are loaded."""
    if _load_model() is None:
        pytest.skip("BioClinicalBERT packages or model weights not available.")
        
    agent = NLAAgent()
    for note_text, expected_sent_nlp, expected_sent_regex, expected_kws, expected_flag_nlp, expected_flag_regex in LABELED_NOTES:
        output = await agent.fetch("patient-123", notes=[note_text])
        assert output.data['nlp_model'] == 'bioclinicalbert'
        assert output.data['sentiment'] == expected_sent_nlp
        
        if expected_flag_nlp:
            assert 'deterioration_keyword' in output.escalation_flags
        else:
            assert 'deterioration_keyword' not in output.escalation_flags

def test_nla_keyword_extraction():
    """Verify substring clinical keyword matching directly."""
    for note_text, _, _, expected_kws, _, _ in LABELED_NOTES:
        kws = extract_keywords(note_text)
        assert sorted(kws) == sorted(expected_kws)

@pytest.mark.asyncio
async def test_nla_empty_notes():
    """Verify fallback to mock outputs when notes are empty."""
    agent = NLAAgent()
    output = await agent.fetch("patient-123", notes=[])
    assert output.data['nlp_model'] == 'mock'
    assert output.data['sentiment'] == 'neutral'
    assert len(output.data['deterioration_keywords_found']) == 0

@pytest.mark.asyncio
async def test_nla_long_note_truncation():
    """Verify long inputs are safely handled."""
    agent = NLAAgent()
    long_text = "increased work of breathing " * 200  # exceeds 512 tokens
    output = await agent.fetch("patient-123", notes=[long_text])
    assert 'deterioration_keyword' in output.escalation_flags

@pytest.mark.asyncio
async def test_nla_confidence_bounds():
    """Verify confidence decays stay bounded within [0.0, 1.0]."""
    agent = NLAAgent()
    eval_time = datetime.now(timezone.utc)
    # TTL is 4h. Make fetched_at 80h ago (19 breaches). Decay penalty is 0.08 * 19 = 1.52.
    # Raw confidence 0.55 -> Net confidence 0.0
    
    with patch('verticals.msignals.src.agents.nla._load_model', return_value=None):
        output = await agent.fetch("patient-123", notes=["respiratory distress"], evaluation_time=eval_time)
        # Manually decay the output using a stale fetched_at timestamp
        output.fetched_at = eval_time - timedelta(hours=80)
        penalized = agent._apply_staleness_penalty(output, eval_time)
        assert penalized.confidence == 0.0
        assert penalized.raw_confidence == 0.55

@pytest.mark.asyncio
async def test_nla_multiple_notes_worst_case():
    """Verify sentiment and keywords are aggregated correctly from last 5 notes."""
    agent = NLAAgent()
    notes = [
        "Patient resting comfortably.",
        "Vital signs stable.",
        "Increased work of breathing noted.", # negative event
    ]
    output = await agent.fetch("patient-123", notes=notes)
    assert output.data['sentiment'] == 'negative'
    assert 'negative_clinical_sentiment' in output.escalation_flags
    assert 'increased work of breathing' in output.data['deterioration_keywords_found']
