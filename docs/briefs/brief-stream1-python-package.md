# Agent Brief — Stream 1: mSignals Python Package
## Agents + Governor Contracts + ICU Coordinator + Conflict Detection Engine

**Status:** Ready to build — awaiting go signal
**Prepared:** 2026-07-01
**Estimated duration:** 1–2 weeks

---

## What You Are Building

The Python backend for the mSignals ICU vertical — a multi-agent patient state alignment system. This is NOT a new framework. It is an adaptation of the existing Austin/MAS agent pattern to a healthcare data context.

You will build:
1. Five ICU agent classes (VAS, LRA, PHA, NLA, HIA) with mock fallback data
2. Governor contracts for the ICU profile
3. An ICU Clinical Coordinator (adapter of Austin's `AlignmentCoordinator`)
4. Compound clinical detection rules (sepsis, AKI, respiratory failure, drug conflict, fluid overload)
5. A MIMIC-IV data pipeline interface (stubbed — the actual data files are not yet available, but the interface must be complete so it can be filled in without changing any agent code)
6. Unit tests for all compound detection rules against synthetic patient data

---

## Context You Need

### What mSignals Is

mSignals is a healthcare vertical of the ALI Multi-Agent Signals (MAS) platform. Its core thesis: in an ICU, multiple independent data domains (vital signs, labs, pharmacy, clinical notes, patient history) each describe the same patient simultaneously but are never synthesized. A patient can be hemodynamically stable by vitals while their lactate is climbing in their labs — that divergence between agents is the sepsis early warning, not noise to be averaged. No existing system detects this because no existing system has an agent architecture. mSignals does.

### The MAS Pattern You Must Follow

Read these files before writing any code. They define the exact interface and patterns your code must match:

```
# Austin agent pattern (read all of these):
versions/signalsv3/src/islm/agents/adp.py
versions/signalsv3/src/islm/agents/arp.py
versions/signalsv3/src/islm/agents/agb.py

# Austin governor contracts:
versions/signalsv3/src/islm/austin/governor/contracts.py

# Austin coordinator (your primary reference):
versions/signalsv3/src/islm/austin/coordinator.py

# Full clinical spec (read sections 3, 4, 5):
verticals/msignals/docs/msignals-whitepaper.md

# Build plan (read Phase 0 and Phase 1):
verticals/msignals/docs/msignals-build-plan.md
```

---

## Directory Structure to Create

```
verticals/msignals/
├── src/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py          # ICU agent base class
│   │   ├── vas.py           # Vital Signs Agent
│   │   ├── lra.py           # Lab Results Agent
│   │   ├── pha.py           # Pharmacy Agent
│   │   ├── nla.py           # Notes / NLP Agent (stub only — full NLP is Stream 3)
│   │   └── hia.py           # History / Context Agent
│   ├── governor/
│   │   ├── __init__.py
│   │   └── contracts_icu.py # ICU governor contracts
│   ├── data/
│   │   ├── __init__.py
│   │   └── mimic.py         # MIMIC-IV data pipeline (interface + stub)
│   ├── rules/
│   │   ├── __init__.py
│   │   └── compound.py      # Compound clinical detection rules
│   └── coordinator.py       # ICU Clinical Coordinator
├── tests/
│   ├── __init__.py
│   ├── test_agents.py       # Agent output schema tests
│   ├── test_compound.py     # Compound detection rule tests (synthetic data)
│   └── test_coordinator.py  # Coordinator conflict detection tests
└── config/
    └── icu_default.json     # Default ICU configuration
```

---

## Decisions Already Made

- **NLP for NLA agent:** BioClinicalBERT (open weights, HuggingFace: `emilyalsentzer/Bio_ClinicalBERT`). Stream 1 writes the NLA stub only — Stream 3 implements the full NLP pipeline. The stub must accept a string and return a valid `NLAOutput` with hardcoded mock values.
- **Drug interaction source:** OpenFDA API (`https://api.fda.gov/drug/drugsfda.json`). PHA agent queries OpenFDA for known interactions. Use the free tier (no API key required for basic queries, 1000 requests/day limit is fine for PoC).
- **MIMIC-IV data:** Not yet available — PhysioNet credentialing in progress. Write the full `PatientStream` interface with type annotations and docstrings. Use `MIMIC_DATA_PATH` env variable for the data root. All methods that read actual files should raise `MIMICDataNotAvailableError` if the path does not exist, rather than crashing.
- **Entity:** mSignals is an ALI vertical. No separate entity considerations.

---

## Agent Specifications

### Base Class (`src/agents/base.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

@dataclass
class AgentOutput:
    agent_id: str
    domain: str
    source: str
    fetched_at: datetime
    freshness_status: str          # 'fresh' | 'stale' | 'unavailable'
    confidence: float              # 0.0–1.0 after staleness penalty applied
    raw_confidence: float          # pre-penalty confidence
    data: dict[str, Any]
    raw_text: str
    escalation_flags: list[str]    # e.g. ['hr_gt_130', 'lactate_gt_2']
    stale_seconds: int = 0         # seconds past TTL (0 if fresh)

class ICUAgent:
    agent_id: str
    domain: str
    ttl_seconds: Optional[int]     # None = event-driven (no TTL)
    publish_threshold: float
    gate_threshold: float
    staleness_penalty_per_ttl: float  # confidence deduction per TTL breach

    def fetch(self, patient_id: str, **kwargs) -> AgentOutput:
        raise NotImplementedError

    def _apply_staleness_penalty(self, output: AgentOutput) -> AgentOutput:
        # Reduce confidence based on how stale the data is
        # staleness_penalty * floor(stale_seconds / ttl_seconds)
        ...
```

### VAS — Vital Signs Agent (`src/agents/vas.py`)

```
Source: Bedside monitor / MIMIC chartevents
TTL: 30 seconds
Publish threshold: 0.90
Gate threshold: 0.70
Staleness penalty: 0.15 per TTL breach

Escalation conditions (set flags, do not alarm internally — coordinator decides):
  hr_gt_130       HR > 130 bpm
  spo2_lt_88      SpO2 < 88%
  sbp_lt_80       Systolic BP < 80 mmHg
  rr_gt_30        Respiratory rate > 30 breaths/min
  temp_gt_38_5    Temperature > 38.5°C
  temp_lt_36      Temperature < 36.0°C
  map_lt_65       Mean arterial pressure < 65 mmHg (sustained > 30 min)
  spo2_trending   SpO2 declining trend over 15-min window (not single point)

MIMIC chartevents item IDs:
  220045 = Heart rate
  220050 = Arterial blood pressure systolic
  220052 = Arterial blood pressure mean (MAP)
  220179 = Non-invasive blood pressure systolic
  220210 = Respiratory rate
  220277 = SpO2 (peripheral)
  223761 = Temperature (°F — convert to °C)

Mock fallback data (used when MIMIC not available):
{
  "hr": 102, "sbp": 94, "dbp": 62, "map": 73,
  "spo2": 95, "rr": 22, "temp_c": 38.4,
  "trend_spo2_15m": "stable"
}
raw_text: "HR 102 bpm · SpO2 95% · BP 94/62 (MAP 73) · RR 22 · Temp 38.4°C"
```

### LRA — Lab Results Agent (`src/agents/lra.py`)

```
Source: LIMS / MIMIC labevents
TTL: 21600 seconds (6 hours)
Publish threshold: 0.85
Gate threshold: 0.65
Staleness penalty: 0.10 per TTL breach

Escalation conditions:
  lactate_gt_2      Lactate > 2.0 mmol/L
  lactate_rising    Lactate increase > 0.5 mmol/L from prior value
  wbc_high          WBC > 12 K/uL
  wbc_low           WBC < 4 K/uL
  creatinine_rise   Creatinine rise ≥ 0.3 mg/dL within 48h OR ≥ 1.5x baseline within 7d
  inr_gt_3_5        INR > 3.5
  platelet_low      Platelet count < 50 K/uL
  bnp_high          BNP > 1000 ng/mL

MIMIC labevents item IDs:
  50813 = Lactate
  51301 = WBC
  50912 = Creatinine
  51274 = PT (for INR calculation)
  51275 = PTT
  51237 = INR(PT)
  51265 = Platelet count
  50885 = Bilirubin (total)

Mock fallback data:
{
  "lactate": 2.4, "lactate_prior_6h": 1.8,
  "wbc": 14.2, "creatinine": 1.1, "creatinine_baseline": 0.9,
  "inr": 1.2, "platelets": 180,
  "result_time": "<fetched_at>"
}
raw_text: "Lactate 2.4↑ (was 1.8 6h ago) · WBC 14.2↑ · Creatinine 1.1 (baseline 0.9, ↑0.2)"
```

### PHA — Pharmacy Agent (`src/agents/pha.py`)

```
Source: CPOE / MIMIC prescriptions + inputevents
TTL: None (event-driven — each new order triggers a fresh fetch)
Publish threshold: 0.99
Gate threshold: 0.85
Staleness penalty: 0.0 (event-driven, no TTL)

Escalation conditions:
  drug_interaction_detected   Known interaction pair active simultaneously
  dose_exceeds_max            Ordered dose > weight-adjusted maximum
  nephrotoxin_active          Aminoglycoside / IV contrast / NSAID / vancomycin active
  anticoagulant_active        Warfarin / heparin / DOAC active
  high_risk_combination       Warfarin + azole antifungal, SSRI + MAOI, etc.

Drug interaction check:
  Use OpenFDA API: https://api.fda.gov/drug/drugsfda.json
  For PoC: maintain a hardcoded HIGH_RISK_PAIRS dict of the 20 most clinically significant
  ICU drug interactions (Warfarin+Fluconazole, Aminoglycoside+loop_diuretic,
  Heparin+NSAIDs, Metformin+IV_contrast, etc.) as fallback when OpenFDA rate-limited.

Mock fallback data:
{
  "active_medications": [
    {"name": "Piperacillin-Tazobactam", "dose": "3.375g", "route": "IV", "frequency": "q6h"},
    {"name": "Norepinephrine", "dose": "0.05 mcg/kg/min", "route": "IV", "frequency": "continuous"}
  ],
  "interactions_detected": [],
  "nephrotoxins_active": [],
  "anticoagulants_active": []
}
raw_text: "Pip-Tazo 3.375g IV q6h · Norepinephrine 0.05 mcg/kg/min · No interactions detected"
```

### NLA — Notes / NLP Agent (`src/agents/nla.py`) — STUB ONLY

```
Source: EHR clinical notes / MIMIC noteevents
TTL: 14400 seconds (4 hours)
Publish threshold: 0.70
Gate threshold: 0.50
Staleness penalty: 0.08 per TTL breach

NOTE: This is a STUB. Full BioClinicalBERT NLP implementation is Stream 3.
The stub must:
  - Accept a list of note strings
  - Return a valid NLAOutput with mock values
  - Be replaceable by Stream 3 without changing any coordinator or test code

Escalation conditions (Stream 3 will detect these):
  negative_clinical_sentiment     Overall note sentiment is negative/concerning
  deterioration_keyword           Any of: "worsening", "altered", "non-responsive",
                                  "distress", "increased work of breathing",
                                  "accessory muscles", "crackles", "edema",
                                  "decreased breath sounds", "unresponsive"

Mock fallback data:
{
  "note_count": 2,
  "last_note_text": "Patient tolerating O2 2L NC, alert and oriented x3",
  "sentiment": "neutral",
  "deterioration_keywords_found": [],
  "nlp_model": "mock"
}
raw_text: "Last note (10:08): tolerating O2, alert and oriented. Sentiment: neutral."
```

### HIA — History / Context Agent (`src/agents/hia.py`)

```
Source: HIE / ADT / MIMIC diagnoses_icd + admissions + patients
TTL: 86400 seconds (24 hours)
Publish threshold: 0.75
Gate threshold: 0.55
Staleness penalty: 0.05 per TTL breach

Escalation conditions:
  prior_sepsis              ICD A41.x in prior admissions
  immunocompromised         ICD D84.x, Z94.x, or active immunosuppressant in PHA
  prior_aki                 ICD N17.x–N19.x in prior admissions
  ckd_known                 ICD N18.x
  chf_known                 ICD I50.x
  copd_known                ICD J44.x
  diabetes_known            ICD E10–E11
  high_risk_combo           Prior sepsis + current fever + current immunocompromise

Mock fallback data:
{
  "age": 62, "sex": "F",
  "prior_diagnoses_icd": ["E11.9", "N39.0"],
  "prior_sepsis": True,
  "immunocompromised": False,
  "prior_aki": False,
  "ckd": False, "chf": False, "copd": False
}
raw_text: "62F · T2DM · Prior UTI (N39.0) · Prior sepsis episode 2024 · No CKD, CHF, or COPD"
```

---

## Governor Contracts (`src/governor/contracts_icu.py`)

Model exactly after `versions/signalsv3/src/islm/austin/governor/contracts.py`. Use the same `AgentContract` dataclass pattern. Values:

```python
ICU_CONTRACTS = {
    'vas': AgentContract(
        agent_id='vas', dispatch='continuous',
        confidence_threshold=0.90, gate_threshold=0.70,
        freshness_ttl_seconds=30, staleness_penalty=0.15,
        escalation_conditions=['hr_gt_130','spo2_lt_88','sbp_lt_80','rr_gt_30',
                               'temp_gt_38_5','temp_lt_36','map_lt_65','spo2_trending']
    ),
    'lra': AgentContract(
        agent_id='lra', dispatch='event',
        confidence_threshold=0.85, gate_threshold=0.65,
        freshness_ttl_seconds=21600, staleness_penalty=0.10,
        escalation_conditions=['lactate_gt_2','lactate_rising','wbc_high','wbc_low',
                               'creatinine_rise','inr_gt_3_5','platelet_low']
    ),
    'pha': AgentContract(
        agent_id='pha', dispatch='event',
        confidence_threshold=0.99, gate_threshold=0.85,
        freshness_ttl_seconds=None, staleness_penalty=0.0,
        escalation_conditions=['drug_interaction_detected','dose_exceeds_max',
                               'nephrotoxin_active','anticoagulant_active']
    ),
    'nla': AgentContract(
        agent_id='nla', dispatch='event',
        confidence_threshold=0.70, gate_threshold=0.50,
        freshness_ttl_seconds=14400, staleness_penalty=0.08,
        escalation_conditions=['negative_clinical_sentiment','deterioration_keyword']
    ),
    'hia': AgentContract(
        agent_id='hia', dispatch='daily',
        confidence_threshold=0.75, gate_threshold=0.55,
        freshness_ttl_seconds=86400, staleness_penalty=0.05,
        escalation_conditions=['prior_sepsis','immunocompromised','high_risk_combo']
    ),
}
```

---

## Compound Detection Rules (`src/rules/compound.py`)

These are pure functions. They take a `dict[str, AgentOutput]` and return a `CompoundResult`.

### Data Structures

```python
@dataclass
class CompoundResult:
    pattern: str                  # 'sepsis' | 'aki' | 'respiratory_failure' | 'drug_conflict' | 'fluid_overload'
    detected: bool
    confidence: float
    agents_contributing: list[str]
    conflict_detected: bool       # True if agent signals diverge
    conflict_agents: list[str]    # Which agents are in conflict
    conflict_description: str
    resolution_directive: str
    action_tier: int              # 1=suppress 2=advisory 3=notify 4=autonomous
    recommended_action: str
```

### Rule: Sepsis (implement exactly)

```python
def detect_sepsis(outputs: dict[str, AgentOutput]) -> CompoundResult:
    """
    Trigger: 3+ of these signals within 2h window:
      VAS: HR > 100 AND (SBP < 100 OR Temp > 38.5 OR Temp < 36.0 OR RR > 22)
      LRA: WBC > 12 or < 4 AND Lactate > 2.0
      HIA: Prior sepsis OR active antibiotics (from PHA)
    
    CRITICAL CONFLICT CASE — detect even if VAS alone is below gate:
      If VAS is hemodynamically STABLE (no flags) AND LRA lactate is RISING (lactate_rising flag):
        This divergence IS the sepsis early warning. Trigger compound detection anyway.
        Set conflict_detected=True, conflict_agents=['vas','lra']
        confidence = lra.confidence * 0.85 (not full compound score, but actionable)
    
    Action tier:
      3 agents contributing: tier 3 (notify attending)
      2 agents + conflict: tier 3
      VAS/LRA conflict only: tier 2 (advisory, recommend repeat lactate)
    
    Recommended action: "Blood cultures x2 · Lactate repeat in 2h · Review antibiotic coverage"
    """
```

### Rule: AKI (implement exactly)

```python
def detect_aki(outputs: dict[str, AgentOutput]) -> CompoundResult:
    """
    Three-agent convergence:
      LRA: creatinine_rise flag set
      VAS: map_lt_65 flag set (sustained — check duration in data dict)
      PHA: nephrotoxin_active flag set
    
    Two-agent sufficient if creatinine_rise + nephrotoxin_active (no VAS required)
    
    Recommended action: "Hold nephrotoxic agents · Nephrology consult · Fluid challenge consider"
    """
```

### Rule: Respiratory Failure (implement exactly)

```python
def detect_respiratory_failure(outputs: dict[str, AgentOutput]) -> CompoundResult:
    """
    AUTONOMOUS TIER (tier 4) if both:
      VAS: spo2_lt_88 AND rr_gt_30
    
    NOTIFY TIER (tier 3) if:
      VAS: spo2_trending AND rr > 25 (trending flag, not threshold breach)
      NLA: deterioration_keyword from respiratory set ('accessory muscles',
           'increased work of breathing', 'distress')
    
    Autonomous action: "Rapid response paged · Supplemental O2 order pre-populated"
    Notify action: "Notify bedside nurse · Document respiratory assessment"
    """
```

### Rule: Drug-Physiology Conflict (implement exactly)

```python
def detect_drug_conflict(outputs: dict[str, AgentOutput]) -> CompoundResult:
    """
    PHA: anticoagulant_active AND drug_interaction_detected
    LRA: inr_gt_3_5 OR platelet_low
    
    Always tier 3 (pharmacist gate required before any further anticoagulant dose).
    conflict_detected always True — PHA and LRA are in disagreement about safety.
    
    Recommended action: "Pharmacist review required · Hold anticoagulant dose · Recheck INR/platelets"
    """
```

### Rule: Fluid Overload (implement exactly)

```python
def detect_fluid_overload(outputs: dict[str, AgentOutput]) -> CompoundResult:
    """
    PHA: total IV fluid > 6L in 24h (check data dict key 'total_iv_24h')
    VAS: spo2_trending (declining) AND rr > 25
    NLA: deterioration_keyword from fluid set ('crackles', 'edema', 'decreased breath sounds')
    LRA: bnp_high (if available — optional, not required for trigger)
    
    Minimum: PHA fluid overload + VAS respiratory deterioration = tier 2 (advisory)
    Three-agent: tier 3 (notify)
    
    Recommended action: "Fluid balance review · Diuresis consider · CXR order"
    """
```

---

## ICU Coordinator (`src/coordinator.py`)

Adapt `versions/signalsv3/src/islm/austin/coordinator.py` to the ICU context. Key differences:

1. **Agents:** 5 ICU agents (VAS, LRA, PHA, NLA, HIA) instead of Austin's 7 ALI agents
2. **Dispatch:** Continuous/event-driven instead of weekly batch
3. **Compound rules:** Call all 5 `detect_*` functions after collecting agent outputs
4. **Output:** Return an `ICUAlignedState` (same structure as Austin's aligned state but with `compound_results` list added)
5. **Temporal alignment:** Before running compound rules, apply staleness penalties to each agent output based on its TTL
6. **Conflict registry:** Collect all `CompoundResult` objects where `conflict_detected=True` into the conflict registry

```python
@dataclass
class ICUAlignedState:
    patient_id: str
    version: int
    agent_outputs: dict[str, AgentOutput]
    compound_results: list[CompoundResult]
    conflicts: list[CompoundResult]       # subset where conflict_detected=True
    aggregate_confidence: float           # weighted mean of contributing agent confidences
    aligned_at: datetime
    state_hash: str                       # sha256 of the serialized aligned state
    highest_action_tier: int              # max tier across all compound results
```

---

## MIMIC-IV Data Pipeline (`src/data/mimic.py`)

Write the complete interface. Every method that reads files must check `MIMIC_DATA_PATH` and raise `MIMICDataNotAvailableError` if not set or path does not exist. Do not crash — raise gracefully so agents fall back to mock data.

```python
class MIMICDataNotAvailableError(Exception):
    """Raised when MIMIC-IV data files are not yet available at MIMIC_DATA_PATH."""
    pass

class PatientStream:
    """
    Replays ICU events for a given patient in chronological order.
    
    Usage:
        stream = PatientStream(subject_id=10006, hadm_id=22239)
        for event in stream.replay(start_hour=0, end_hour=24):
            process(event)
    
    Tables loaded (lazy, on first access):
        chartevents, labevents, prescriptions, inputevents,
        noteevents, diagnoses_icd, icustays, patients, admissions
    """
    
    def __init__(self, subject_id: int, hadm_id: int): ...
    
    def get_vitals(self, window_hours: int = 6) -> pd.DataFrame: ...
    def get_labs(self, window_hours: int = 24) -> pd.DataFrame: ...
    def get_medications(self) -> pd.DataFrame: ...
    def get_notes(self, window_hours: int = 24) -> list[str]: ...
    def get_history(self) -> dict: ...
    def replay(self, start_hour: int = 0, end_hour: int = 24): ...

class MIMICCohort:
    """
    Loads and filters the full MIMIC-IV ICU cohort for validation studies.
    
    Usage:
        cohort = MIMICCohort()
        sepsis_stays = cohort.filter_by_outcome('sepsis')
        for stay in sepsis_stays:
            stream = stay.to_patient_stream()
    """
    
    def filter_by_outcome(self, outcome: str) -> list['ICUStay']: ...
    def filter_by_unit(self, unit_type: str) -> list['ICUStay']: ...
    def sample(self, n: int, seed: int = 42) -> list['ICUStay']: ...
```

---

## Test Requirements (`tests/`)

### `tests/test_compound.py` — the most important test file

Write unit tests for all 5 compound detection rules. Each test uses a synthetic `dict[str, AgentOutput]` — no MIMIC data needed, no external dependencies.

Required test cases:

```python
# Sepsis tests
test_sepsis_three_agent_convergence()       # VAS + LRA + HIA all contributing → tier 3
test_sepsis_vas_lra_conflict()              # VAS stable + LRA lactate rising → conflict tier 2
test_sepsis_below_threshold()               # All agents below gate → no detection
test_sepsis_stale_lra_penalty()             # LRA stale (6h) → confidence penalized, still detects

# AKI tests
test_aki_three_agent()                      # creatinine_rise + map_lt_65 + nephrotoxin → tier 3
test_aki_two_agent_no_vas()                 # creatinine_rise + nephrotoxin → tier 2
test_aki_no_trigger()                       # Normal creatinine, no nephrotoxin → no detection

# Respiratory failure tests
test_respiratory_autonomous()               # spo2_lt_88 + rr_gt_30 → tier 4 autonomous
test_respiratory_notify()                   # spo2_trending + rr 26 + NLA keyword → tier 3
test_respiratory_nla_only()                 # Only NLA keyword, no VAS flag → no detection

# Drug conflict tests
test_drug_conflict_anticoagulant_inr()      # Warfarin + INR 3.8 → tier 3 pharmacist gate
test_drug_conflict_no_anticoagulant()       # Interaction detected but no anticoagulant → advisory only

# Fluid overload tests
test_fluid_three_agent()                    # PHA + VAS + NLA → tier 3
test_fluid_two_agent()                      # PHA + VAS only → tier 2 advisory
```

### `tests/test_agents.py`

Test that each agent:
- Returns a valid `AgentOutput` when called with mock data (no MIMIC path set)
- Applies staleness penalty correctly when `fetched_at` is past TTL
- Sets the correct escalation flags for threshold-breaching values

### `tests/test_coordinator.py`

Test that the `ICUCoordinator`:
- Produces an `ICUAlignedState` with the correct `highest_action_tier` from a synthetic agent output set
- Correctly identifies conflicts in the conflict registry
- Generates a deterministic `state_hash` for the same inputs

---

## Success Criteria

- [ ] All 5 agent classes instantiate and return valid `AgentOutput` from mock data with no MIMIC path set
- [ ] All 5 compound detection rules correctly classify all test cases (0 failures)
- [ ] `ICUCoordinator.align()` produces a valid `ICUAlignedState` for a synthetic 5-agent input
- [ ] `PatientStream` raises `MIMICDataNotAvailableError` gracefully when path not set
- [ ] All tests pass: `cd verticals/msignals && python -m pytest tests/ -v`
- [ ] No external dependencies beyond those already in `versions/signalsv3/requirements.txt` + `pandas`, `httpx`, `transformers` (stub-only for NLA, Stream 3 fills it)

## What NOT to Build

- Do NOT build any dashboard, API, or frontend — that is Stream 2
- Do NOT implement BioClinicalBERT inference — the NLA agent is a stub, that is Stream 3
- Do NOT attempt to run against actual MIMIC data files — the interface is the deliverable
- Do NOT add a FastAPI wrapper — just the Python package
- Do NOT modify any Austin or MAS files — read them as reference only
