# mSignals ICU — Build Plan

**Version:** 0.1 · 2026-07-01
**Author:** ALI / Anthony Monroy
**Status:** Phase 0, 1, and 2 Complete — Awaiting Phase 3 (Validation Study)
**Goal:** Validate the conflict-aware patient state alignment thesis against real ICU data, build a demonstration dashboard, and generate the clinical validation evidence needed for regulated deployment.

---

## Strategic Sequencing Rationale

Live ICU deployment requires FDA SaMD clearance, BAA-covered EHR integration, IRB approval for clinical pilots, and an 18–36 month hospital procurement cycle. That path is correct — but it must be earned, not attempted from a standing start.

The entry point is **MIMIC-IV**: a publicly available, fully de-identified ICU dataset (40,000+ stays, Beth Israel Deaconess) with vitals, labs, medications, notes, and outcomes. No BAA. No IRB. No FDA. mSignals runs its full agent architecture over historical ICU data, validates against known outcomes (sepsis, AKI, respiratory failure), and produces both a working system and publishable evidence — simultaneously.

**The MIMIC validation study is the enterprise sales tool and the 510(k) predicate evidence in one artifact.**

---

## Phase 0 — MIMIC-IV Data Foundation [COMPLETE]

**Duration:** 3–4 weeks
**Goal:** Stand up mSignals agents reading real ICU data from MIMIC-IV. No frontend. No clinical UI. Just the alignment engine working.

### 0.1 MIMIC-IV Data Pipeline

MIMIC-IV (PhysioNet, v2.2) is structured as relational tables. Required tables:

```
chartevents      — vital signs (HR, BP, SpO2, temp, RR) — primary VAS source
labevents        — lab results (lactate, WBC, creatinine, INR) — primary LRA source
prescriptions    — medication orders — primary PHA source
noteevents       — clinical notes (NLP required) — primary NLA source
inputevents      — IV fluids and drips — supplement to PHA
diagnoses_icd    — admission diagnoses — HIA context
icustays         — ICU admission/discharge timestamps, unit type
patients         — demographics (age, gender)
admissions       — hospital-level admission data
```

Build a Python data layer (`msignals/data/mimic.py`) that:
- Loads tables into Pandas/Polars DataFrames
- Exposes a `PatientStream(subject_id, hadm_id)` iterator that replays events in chronological order
- Supports configurable replay speed (real-time simulation or batch processing)

### 0.2 Agent Readers (MIMIC-Adapted)

Each agent reads from MIMIC tables rather than live hospital APIs. The agent interface is identical to live; only the connector changes. This is intentional — live deployment replaces the connector, not the agent.

**VAS (Vital Signs Agent)**
```python
Source: chartevents (itemid in [220045, 220050, 220052, 220179, 220210, 220277])
TTL: 30 seconds simulation / 5 minutes MIMIC replay
Escalation: HR > 130, SpO2 < 88%, SBP < 80 mmHg, RR > 30
```

**LRA (Lab Results Agent)**
```python
Source: labevents (itemid in [50813=lactate, 51301=WBC, 50912=creatinine, 51274=INR])
TTL: 6 hours (MIMIC events naturally spaced 4–8h)
Escalation: Lactate > 2.0 mmol/L, WBC > 12 or < 4 K/uL, creatinine rise > 0.5 from baseline
```

**PHA (Pharmacy Agent)**
```python
Source: prescriptions + inputevents
TTL: Event-driven (each new order triggers)
Escalation: Known interaction pairs (Warfarin+Fluconazole, Aminoglycoside+loop diuretic, etc.)
Drug-drug: Use OpenFDA drug interaction API or DrugBank open dataset
```

**NLA (Notes/NLP Agent)**
```python
Source: noteevents (category in ['Nursing', 'Physician', 'Nursing/Other'])
TTL: 4 hours (async — publish when note appears)
NLP: Extract clinical sentiment + deterioration keywords
Model: BioClinicalBERT (HuggingFace, clinical domain fine-tuned, open weights)
Escalation: Negative clinical sentiment + keywords: "worsening", "altered", "non-responsive", "distress"
```

**HIA (History/Context Agent)**
```python
Source: diagnoses_icd + admissions + patients
TTL: 24 hours (static per admission)
Context: Prior sepsis (ICD A41.x), immunocompromised (ICD D84.x), CKD (ICD N18.x)
Escalation: High-risk history + current pattern match
```

### 0.3 Governor Contracts (ICU Profile)

```python
# msignals/governor/contracts_icu.py

ICU_CONTRACTS = {
    'vas': AgentContract(
        agent_id='vas',
        dispatch='continuous',
        confidence_threshold=0.90,
        gate_threshold=0.70,
        freshness_ttl_seconds=30,
        staleness_penalty=0.15,  # confidence penalty per TTL breach
        escalation_conditions=['hr_gt_130', 'spo2_lt_88', 'sbp_lt_80', 'rr_gt_30']
    ),
    'lra': AgentContract(
        agent_id='lra',
        dispatch='event',
        confidence_threshold=0.85,
        gate_threshold=0.65,
        freshness_ttl_seconds=21600,  # 6h
        staleness_penalty=0.10,
        escalation_conditions=['lactate_gt_2', 'wbc_abnormal', 'creatinine_rise']
    ),
    'pha': AgentContract(
        agent_id='pha',
        dispatch='event',
        confidence_threshold=0.99,
        gate_threshold=0.85,
        freshness_ttl_seconds=None,  # event-driven, no TTL
        staleness_penalty=0.0,
        escalation_conditions=['drug_interaction_detected', 'dose_exceeds_max']
    ),
    'nla': AgentContract(
        agent_id='nla',
        dispatch='event',
        confidence_threshold=0.70,
        gate_threshold=0.50,
        freshness_ttl_seconds=14400,  # 4h
        staleness_penalty=0.08,
        escalation_conditions=['negative_clinical_sentiment', 'deterioration_keyword']
    ),
    'hia': AgentContract(
        agent_id='hia',
        dispatch='daily',
        confidence_threshold=0.75,
        gate_threshold=0.55,
        freshness_ttl_seconds=86400,  # 24h
        staleness_penalty=0.05,
        escalation_conditions=['high_risk_history_match']
    ),
}
```

### 0.4 ICU Clinical Coordinator

Extend Austin's `AlignmentCoordinator` with ICU-specific:

- **Temporal alignment**: before synthesis, align all agent outputs to a common time window. Apply staleness penalty to confidence for any agent whose last update is past TTL.
- **Conflict detection**: compare agent positions on patient stability. Define conflict as: any two agents whose implied patient state differ by > 1 standard deviation from expected concordance given their individual confidence levels.
- **Compound scoring**: sepsis, AKI, and respiratory failure each have a defined multi-agent compound rule set (see Loop definitions below).
- **Conflict registry**: output for each alignment cycle includes `conflicts: List[ConflictRecord]` with agents involved, divergence magnitude, and resolution directive.

---

## Phase 1 — Conflict Detection Engine [COMPLETE]

**Duration:** 4–6 weeks
**Goal:** A working synthesis engine that detects compound clinical signals earlier than single-domain approaches. Validated on MIMIC-IV retrospectively.

### 1.1 Clinical Compound Rules

Define the five highest-value compound patterns as first-class detection targets:

**Sepsis (qSOFA + SIRS compound)**
```
Trigger: Any 3 of:
  VAS: HR > 100 AND (SBP < 100 OR temp > 38.5 OR temp < 36.0 OR RR > 22)
  LRA: WBC > 12 or < 4 AND Lactate > 2.0
  HIA: Suspected infection source in history or active antibiotics (PHA)
Conflict signal: VAS stable + LRA lactate climbing = early sepsis (pre-threshold)
Confidence weight: LRA primary, VAS corroborating, HIA context multiplier
```

**AKI (KDIGO Stage 1+)**
```
Trigger:
  LRA: Creatinine rise ≥ 0.3 mg/dL within 48h OR ≥ 1.5x baseline within 7d
  VAS: MAP < 65 mmHg sustained > 30 min
  PHA: Nephrotoxic agent administered (aminoglycoside, contrast, NSAID, vancomycin)
Conflict signal: VAS hemodynamic instability + LRA renal rise + PHA nephrotoxin = AKI cascade
```

**Respiratory Failure**
```
Trigger:
  VAS: SpO2 < 92% trending (not single point) AND RR > 25
  VAS: Tidal volume declining (if ventilated)
  NLA: Documentation of "increased work of breathing", "accessory muscles"
High-conf autonomous: SpO2 < 88% + RR > 30 = immediate alert regardless of other agents
```

**Drug-Physiology Conflict (PHA/VAS/LRA)**
```
Trigger:
  PHA: Anticoagulant active
  LRA: INR > 3.5 or platelet < 50K
  VAS: (optional) hemodynamic instability
Resolution: Pharmacist gate required before any further anticoagulant dose
```

**Fluid Overload (CHF/ARDS risk)**
```
Trigger:
  PHA: Total IV fluid input > 6L in 24h
  VAS: SpO2 declining, RR rising
  LRA: BNP/proBNP > 1000 (if available)
NLA: Documentation of "crackles", "edema", "decreased breath sounds"
```

### 1.2 Validation Protocol (MIMIC-IV Retrospective)

Run mSignals on all MIMIC-IV ICU stays with known outcomes (sepsis: ICD A41.x, AKI: ICD N17.x-N19.x, respiratory failure: ICD J96.x).

**Primary metric:** Time-to-detection vs. onset of clinical deterioration (defined as first clinical intervention in the record).

**Comparison baseline:**
- Single-parameter alarm (reproduce current Philips/GE approach)
- Epic Deterioration Index score (published coefficients from Brajer et al. 2020)
- SOFA score trajectory (standard ICU severity measure)

**Expected mSignals advantage:** Compound signal detection at lower individual-agent confidence levels catches deterioration patterns 60–120 minutes earlier by identifying agent conflicts pre-threshold.

**Statistical target:** AUROC ≥ 0.82 for sepsis onset at 6h horizon, with alarm rate ≤ 2x baseline (not dramatically higher alarm burden).

---

## Phase 2 — ICU Dashboard (Research / Demonstration) [COMPLETE]

**Duration:** 6–8 weeks
**Goal:** A visual tool that makes the conflict-aware synthesis engine legible to clinicians. Not for clinical use — no FDA required. Used for research validation, stakeholder demos, and pilot site conversations.

### 2.1 Design Principles

**One principle above all:** The most prominent visual element is the **agent disagreement state**, not a risk score.

Existing systems show you a number. mSignals shows you a conversation between data sources — and specifically where that conversation breaks down.

**Nurse view:** Action-oriented. What does this patient need right now? Which agents are stale (should I check a new lab)? What is the escalation status?

**Doctor view:** Synthesis-oriented. What is the aligned patient state? Where are the active conflicts? What is the evidence quality behind the recommendation?

### 2.2 Nurse View — Wireframe

```
┌─────────────────────────────────────────────────────────────────────┐
│  BED 4 — JOHNSON, M.  62F  · Admitted 2d 14h · Unit: MICU          │
│  Aligned State: ⚠️  DIVERGENCE DETECTED  · Updated 14:32:07         │
├──────────────────────────┬──────────────────────────────────────────┤
│  AGENT STATUS            │  ACTIVE CONFLICT                         │
│                          │                                          │
│  VAS ●  FRESH   0.88 ↔  │  ⚠️ VAS ↔ LRA DIVERGENCE                │
│  LRA ●  FRESH   0.91     │                                          │
│  PHA ●  FRESH   0.99     │  VAS says: hemodynamically stable        │
│  NLA ⚪  STALE  0.52     │  (HR 102, BP 94/62, SpO2 95%)           │
│  HIA ●  FRESH   0.81     │                                          │
│                          │  LRA says: metabolic deterioration       │
│  Freshness clock:        │  (Lactate 2.4↑ · WBC 14.2↑ · posted     │
│  NLA last note: 4h 22m   │  47 min ago)                            │
│  → Document or flag      │                                          │
│                          │  Compound sepsis score: 0.87             │
│                          │  → ACTION: Blood cultures + ABX review  │
├──────────────────────────┴──────────────────────────────────────────┤
│  TIMELINE (last 6h)                                                  │
│                                                                      │
│  HR:    ████░░░░████████████████████  102 ↑                        │
│  SpO2:  ████████████████████░░░░████   95%                         │
│  Lact:  ░░░░░░░░░░░░░████████████      2.4 ↑↑                     │
│  WBC:   ░░░░░░░░░░░░░░░░░░████████    14.2 ↑                      │
│                                                                      │
│  ● 13:45  LRA conflict detected — sepsis compound pattern           │
│  ● 12:22  PHA: Piperacillin-Tazobactam active (appropriate)        │
│  ● 10:11  VAS: BP dip resolved — vasopressor weaned                │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 Doctor View — Wireframe

```
┌─────────────────────────────────────────────────────────────────────┐
│  ALIGNED STATE v47  ·  BED 4  ·  hash:a3f9b2e1  ·  14:32:07       │
│  Aggregate confidence: 0.87  ·  Conflict registry: 1 active         │
├────────────────────────────────┬────────────────────────────────────┤
│  AGENT TELEMETRY               │  CONFLICT REGISTRY                 │
│                                │                                    │
│  [VAS]  conf: 0.88  fresh      │  #1 · VAS ↔ LRA · conf_divergence  │
│  HR 102  SpO2 95%  BP 94/62   │                                    │
│  RR 22   Temp 38.4°C          │  VAS position: hemodynamically      │
│                                │  compensated — pressure recovering  │
│  [LRA]  conf: 0.91  fresh      │  after vasopressor wean            │
│  Lactate 2.4 ↑ (was 1.8 6h)  │                                    │
│  WBC 14.2  Creat 1.1 (↑0.2)  │  LRA position: metabolic stress     │
│                                │  ongoing — lactate still climbing   │
│  [PHA]  conf: 0.99  fresh      │  post-wean (not clearing)          │
│  Pip-Tazo 3.375g q6h active   │                                    │
│  No interactions detected      │  Resolution: LRA weighted primary  │
│                                │  (lactate trend > pressure trend   │
│  [NLA]  conf: 0.52  STALE 4h  │  for sepsis staging). Vasopressor  │
│  Last note: 10:08 "tolerating │  wean may be premature.            │
│  O2, alert and oriented"       │                                    │
│                                │  Recommendation: Repeat lactate    │
│  [HIA]  conf: 0.81  fresh      │  in 2h. Hold vasopressor wean.    │
│  Hx: UTI 2024, T2DM, no CKD  │  Blood cultures if not drawn.      │
│  Immunocompromised: No         │                                    │
├────────────────────────────────┴────────────────────────────────────┤
│  HUMAN GATE LOG                                                      │
│  14:31  Conflict flagged → Attending notified (push)                │
│  13:45  Auto-suppressed: NLA conf 0.52 < gate threshold 0.50        │
│  12:22  PHA interaction check: clear — logged, no action            │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.4 What the Dashboard Does That the Competition Cannot

| Capability | mSignals | Epic DI | Philips | Dascena |
|---|---|---|---|---|
| Show WHICH agents disagree | ✅ | ❌ | ❌ | ❌ |
| Show WHY the conflict matters | ✅ | ❌ | ❌ | ❌ |
| Freshness indicator per agent | ✅ | ❌ | ⚠️ | ❌ |
| Prompt nurse for stale data | ✅ | ❌ | ❌ | ❌ |
| Attribution per recommendation | ✅ | ❌ | ❌ | ❌ |
| Conflict as the primary visual | ✅ | ❌ | ❌ | ❌ |
| Auditable reasoning trail | ✅ | ❌ | ⚠️ | ❌ |
| Score-free nurse view | ✅ | ❌ | ❌ | ❌ |

**Score-free nurse view** deserves emphasis. Existing systems give nurses a number: Deterioration Index 74. What does 74 mean? Higher is worse? Is 74 bad enough to call the attending at 3am? A number puts cognitive burden on the nurse. mSignals gives the nurse a narrative: *VAS says stable, LRA says deteriorating, here is what to do about that.* The clinical action is already specified.

### 2.5 Tech Stack (Research Dashboard)

- **Backend**: FastAPI (existing MAS stack) + mSignals ICU coordinator
- **Data**: MIMIC-IV (Phase 0–2) → live FHIR R4 (Phase 4)
- **Frontend**: Next.js + React Flow (reuse Austin dashboard architecture)
- **Agent status visualization**: Adapt Austin's 7-node graph → 5-node ICU agent graph with same telemetry drawer pattern
- **Timeline**: D3.js multi-series time chart with conflict markers
- **Conflict panel**: structured ConflictRecord display (existing Austin alignment inspector pattern, domain-adapted)

---

## Phase 3 — Validation Study and Publication [NEXT PHASE]

**Duration:** 8–12 weeks
**Goal:** Peer-reviewable evidence that mSignals conflict-aware synthesis outperforms existing approaches on MIMIC-IV. This is the AWP paper — published through ASII.

### Study Design

**Cohort:** MIMIC-IV adult ICU stays ≥ 24h (approximately 22,000 stays after exclusions)
**Outcomes:** Sepsis (A41.x), AKI (N17–N19), respiratory failure (J96.x), ICU mortality
**Primary metric:** AUROC for outcome detection at 6h prediction horizon
**Alarm burden metric:** True positive rate at fixed false positive rate (2 alarms/patient/day)

### Comparison Arms

1. Single-parameter alarm (reproduce current standard of care)
2. Epic Deterioration Index (published coefficients)
3. SOFA score trajectory
4. **mSignals conflict-aware synthesis** (primary arm)

### Expected Findings

Based on published compound-signal literature:
- mSignals should detect sepsis onset 60–90 minutes earlier than single-domain approaches at equivalent alarm burden
- Conflict-detection specifically: VAS/LRA divergence pattern should predict sepsis-3 criteria with AUROC > 0.84 at 6h
- AKI: PHA/LRA/VAS compound pattern (nephrotoxin + hemodynamic + renal rise) should outperform individual domain models by > 15% AUROC

### Publication Target

*Critical Care Medicine* or *JAMIA* (Journal of the American Medical Informatics Association) — both accept computational/systems papers without live clinical validation if the methodology is retrospective MIMIC-based. This is the standard path for ICU AI research before clinical translation.

---

## Phase 4 — Live Clinical Pilot (Regulated)

**Duration:** 12–18 months (begins after Phase 3 publication)
**Goal:** Observational (no autonomous action) deployment at a single pilot site to validate MIMIC findings on live data.

### Pre-requisites

- Phase 3 paper submitted / accepted
- FDA Pre-Submission (Q-Sub) meeting to establish regulatory strategy
- Pilot site selected: academic medical center with research-friendly IRB and Epic installation
- BAA signed
- IRB approval (observational, no clinical intervention)

### Integration Stack (Live)

```
Bedside monitor → HL7 v2 ADT/ORU feed → VAS connector
Epic FHIR R4 API → LRA connector (lab results)
Epic FHIR R4 API → PHA connector (medication orders)
Epic NLP Service / Azure Health NLP → NLA connector
Epic FHIR R4 API → HIA connector (patient history)
```

Epic's FHIR R4 API is production-ready. The challenge is the HL7 v2 bedside monitor feed — Philips and GE both expose HL7 v2 ORU messages from their monitoring hardware. A middleware layer (Mirth Connect or Rhapsody) normalizes this to the VAS connector interface.

### Pilot Deployment Model

- **Observational only** (no alerts generated to clinical staff) — purely recording what mSignals would have flagged vs. what actually happened
- **Duration:** 90 days, minimum 200 patient-stays
- **Primary question:** Does the MIMIC validation AUROC hold on live data?
- **Secondary question:** What is the false positive rate in a live workflow?

### Phase 4 Output

- Live validation data supporting 510(k) submission
- Clinician feedback on dashboard usability (nurse view, doctor view)
- Integration playbook for Epic + bedside monitor environment

---

## Phase 5 — Commercial Deployment

**Duration:** 18–24 months after Phase 3 (concurrent with Phase 4)
**Milestones:**

1. **510(k) submission** — Class II SaMD, predicate: Philips Guardian / early warning scoring systems
2. **Epic App Orchard listing** — in-workflow integration (eliminates separate screen problem)
3. **First IDN contract** — 400+ bed academic medical center, 3-year term
4. **Pricing model:** $150–350/bed/year SaaS for monitoring layer + $50K implementation fee

---

## Build Priority Summary

| Phase | Duration | Deliverable | Clinical Risk |
|---|---|---|---|
| 0 — MIMIC Data Foundation | 3–4 wks | Working agents on real ICU data | None |
| 1 — Conflict Detection Engine | 4–6 wks | Compound pattern detection + validation | None |
| 2 — Research Dashboard | 6–8 wks | Nurse + doctor views, demo-ready | None |
| 3 — Validation Study | 8–12 wks | Published paper, AUROC evidence | None |
| 4 — Live Clinical Pilot | 12–18 mos | Observational live validation | Low (observational) |
| 5 — Commercial | 18–24 mos from P3 | FDA cleared, Epic-integrated product | Managed |

**Phases 0–3 are buildable now with the existing MAS stack, zero regulatory overhead, and MIMIC-IV as the data source. The path from working research system to clinical publication is 6–9 months of focused build. That publication is what unlocks the hospital conversations.**

---

## Open Questions Before Phase 0 Start

1. **NLP model selection**: BioClinicalBERT (open weights, clinical domain) vs. commercial (Azure Health NLP, AWS Comprehend Medical, Google MedPaLM). Open weights preferred for research phase; commercial for production.
2. **MIMIC-IV access**: Requires PhysioNet credentialing (free, ~2 week process). Must be completed before Phase 0 starts.
3. **Drug interaction data source**: OpenFDA (free, limited) vs. DrugBank (licensed, comprehensive). DrugBank open dataset covers ~10,000 interactions.
4. **Pilot site identification**: Should begin stakeholder conversations now. Academic medical centers with existing MAS/AI research programs (UCSF, Johns Hopkins, Beth Israel) are natural first targets — they already use MIMIC, which reduces integration unfamiliarity.
5. **mSignals legal entity**: Does mSignals operate as an ALI vertical or a separate entity for FDA sponsorship purposes?

---

*Build plan connects to: `msignals-whitepaper.md` (clinical argument), `mas/implementation_plan.md` (platform architecture), `mas/HANDOFF.md` (task tracking).*
