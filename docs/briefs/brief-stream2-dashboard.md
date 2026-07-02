# Agent Brief — Stream 2: mSignals ICU Dashboard
## Next.js Dashboard — Nurse View + Doctor View + Mock Patient State

**Status:** Ready to build — awaiting go signal
**Prepared:** 2026-07-01
**Estimated duration:** 1–2 weeks

---

## What You Are Building

A standalone Next.js ICU monitoring dashboard for mSignals — the healthcare vertical of the ALI Multi-Agent Signals (MAS) platform. The dashboard shows clinical staff the aligned patient state produced by 5 independent ICU agents (VAS, LRA, PHA, NLA, HIA), with agent conflicts displayed as the primary clinical signal rather than an averaged risk score.

The application lives at `verticals/msignals/dashboard/` and is entirely separate from the Austin dashboard at `versions/signalsv3/terminal/`. Do not modify Austin files.

You will build:
1. A Next.js app bootstrapped in `verticals/msignals/dashboard/`
2. A Nurse View — patient state at a glance, score-free, action-oriented
3. A Doctor View — full agent telemetry + conflict registry + audit log
4. A 5-node React Flow agent graph (same library Austin uses)
5. Rich mock patient data that exercises all four human gate tiers
6. A `/api/msignals/patient/[id]` API route returning mock data (FastAPI stub for future wiring)

---

## Context You Need

### The Core Design Principle

This dashboard does NOT show a risk score. That is intentional and is the central product differentiator.

Existing ICU systems show: **"Risk score: 74"** — which forces the nurse to decide "is 74 bad enough to call at 3am?"

mSignals shows: **"VAS says stable. LRA says lactate is climbing. Here's why that divergence matters and what to do."**

Every design decision flows from that principle. The most prominent visual element is agent disagreement, not a numeric score.

### What mSignals Is

mSignals has 5 ICU agents, each owning one data domain:
- **VAS** — Vital Signs Agent (HR, SpO2, BP, RR, Temp) — TTL: 30 seconds
- **LRA** — Lab Results Agent (lactate, WBC, creatinine, INR) — TTL: 6 hours
- **PHA** — Pharmacy Agent (active meds, drug interactions) — TTL: event-driven
- **NLA** — Notes / NLP Agent (clinical note sentiment and keywords) — TTL: 4 hours
- **HIA** — History / Context Agent (prior diagnoses, comorbidities) — TTL: 24 hours

Each agent reports a confidence score (0.0–1.0), a freshness status (fresh/stale/unavailable), and escalation flags. When agents disagree about patient stability, the coordinator identifies the conflict and produces a resolution directive with full attribution.

### Human Gate Tiers (drives all alert styling)

- **Tier 1 — Suppress** (confidence < 0.60): Logged only, no UI alert
- **Tier 2 — Advisory** (0.60–0.80): Appears in dashboard, no interrupt
- **Tier 3 — Notify** (0.80–0.92): Push notification to responsible clinician, requires review
- **Tier 4 — Autonomous** (> 0.92 + high severity): Rapid response paged, pre-populated order

### Reference Files — Read These Before Building

```
# Austin dashboard (your primary UI pattern reference):
versions/signalsv3/terminal/src/app/(protected)/teamwork/page.tsx
versions/signalsv3/terminal/src/app/(protected)/alignment/page.tsx
versions/signalsv3/terminal/src/components/layout/Sidebar.tsx

# Full clinical spec — read sections 6 and 7:
verticals/msignals/docs/msignals-whitepaper.md

# Tech stack reference — check package.json for versions:
versions/signalsv3/terminal/package.json
```

The Austin dashboard uses: Next.js 14 (App Router), TypeScript, Tailwind CSS, Shadcn/ui, `@xyflow/react` (React Flow), Lucide icons, Recharts. Match these versions exactly.

---

## Directory Structure to Create

```
verticals/msignals/dashboard/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.ts
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                    # Redirects to /patient/demo
│   │   ├── patient/
│   │   │   └── [id]/
│   │   │       ├── page.tsx            # Patient view (nurse + doctor tabs)
│   │   │       └── layout.tsx
│   │   └── api/
│   │       └── msignals/
│   │           └── patient/
│   │               └── [id]/
│   │                   └── route.ts    # Mock API (FastAPI stub)
│   ├── components/
│   │   ├── layout/
│   │   │   └── Sidebar.tsx
│   │   ├── patient/
│   │   │   ├── AgentGraph.tsx          # React Flow 5-node graph
│   │   │   ├── NurseView.tsx           # Nurse tab content
│   │   │   ├── DoctorView.tsx          # Doctor tab content
│   │   │   ├── AgentStatusGrid.tsx     # 5-agent freshness + confidence grid
│   │   │   ├── ConflictBanner.tsx      # Active conflict display
│   │   │   ├── GateAlert.tsx           # Tier-3/4 alert component
│   │   │   ├── PatientTimeline.tsx     # 6h trend charts (Recharts)
│   │   │   └── AuditLog.tsx            # Immutable audit trail list
│   │   └── ui/                         # Shadcn components (copy from Austin terminal)
│   ├── lib/
│   │   ├── mock-data.ts                # MOCK_PATIENT_STATE + MOCK_AUDIT_LOG
│   │   └── types.ts                    # Shared TypeScript types
│   └── styles/
│       └── globals.css
```

---

## TypeScript Types (`src/lib/types.ts`)

```typescript
export type FreshnessStatus = 'fresh' | 'stale' | 'unavailable'
export type ActionTier = 1 | 2 | 3 | 4
export type EscalationFlag = string

export interface AgentOutput {
  agent_id: 'vas' | 'lra' | 'pha' | 'nla' | 'hia'
  domain: string
  confidence: float               // post-staleness-penalty confidence
  raw_confidence: number
  freshness_status: FreshnessStatus
  stale_seconds: number           // 0 if fresh
  fetched_at: string              // ISO 8601
  escalation_flags: EscalationFlag[]
  raw_text: string                // human-readable summary of what the agent saw
  data: Record<string, unknown>   // domain-specific data fields
}

export interface CompoundResult {
  pattern: 'sepsis' | 'aki' | 'respiratory_failure' | 'drug_conflict' | 'fluid_overload'
  detected: boolean
  confidence: number
  agents_contributing: string[]
  conflict_detected: boolean
  conflict_agents: string[]
  conflict_description: string
  resolution_directive: string
  action_tier: ActionTier
  recommended_action: string
}

export interface AuditEntry {
  timestamp: string               // ISO 8601
  event_type: 'conflict_flagged' | 'agent_suppressed' | 'interaction_clear' | 'autonomous_action' | 'notify_sent'
  agent_id?: string
  tier: ActionTier
  description: string
  clinician_action?: string       // set if clinician confirmed/dismissed
}

export interface ICUAlignedState {
  patient_id: string
  version: number
  aligned_at: string              // ISO 8601
  state_hash: string
  agent_outputs: Record<string, AgentOutput>
  compound_results: CompoundResult[]
  conflicts: CompoundResult[]     // subset where conflict_detected=true
  aggregate_confidence: number
  highest_action_tier: ActionTier
  audit_log: AuditEntry[]
}

export interface Patient {
  id: string
  name: string
  age: number
  sex: 'M' | 'F'
  bed: string
  unit: string
  admitted_at: string
  primary_diagnosis: string
  aligned_state: ICUAlignedState
}
```

---

## Mock Data (`src/lib/mock-data.ts`)

This is the demo centerpiece. It must exercise all four human gate tiers simultaneously across different compound patterns so reviewers see the full system capability.

```typescript
// Primary demo patient: sepsis compound conflict (VAS stable / LRA deteriorating)
// This is the canonical mSignals case — the conflict IS the clinical signal

export const MOCK_PATIENT_JOHNSON: Patient = {
  id: 'demo-001',
  name: 'Johnson, M.',
  age: 62,
  sex: 'F',
  bed: 'Bed 4',
  unit: 'MICU',
  admitted_at: new Date(Date.now() - (2 * 86400 + 14 * 3600) * 1000).toISOString(),
  primary_diagnosis: 'Sepsis — source under investigation',
  aligned_state: {
    patient_id: 'demo-001',
    version: 47,
    aligned_at: new Date(Date.now() - 3 * 60000).toISOString(),
    state_hash: 'a3f9b2e1c7d4f8a2',
    aggregate_confidence: 0.87,
    highest_action_tier: 3,
    agent_outputs: {
      vas: {
        agent_id: 'vas', domain: 'vital_signs', confidence: 0.88, raw_confidence: 0.90,
        freshness_status: 'fresh', stale_seconds: 0,
        fetched_at: new Date(Date.now() - 12000).toISOString(),
        escalation_flags: [],
        raw_text: 'HR 102 bpm · SpO2 95% · BP 94/62 (MAP 73) · RR 22 · Temp 38.4°C',
        data: { hr: 102, sbp: 94, dbp: 62, map: 73, spo2: 95, rr: 22, temp_c: 38.4,
                trend_spo2_15m: 'stable', trend_bp_1h: 'slight_decline' }
      },
      lra: {
        agent_id: 'lra', domain: 'laboratory', confidence: 0.91, raw_confidence: 0.91,
        freshness_status: 'fresh', stale_seconds: 0,
        fetched_at: new Date(Date.now() - 47 * 60000).toISOString(),
        escalation_flags: ['lactate_gt_2', 'lactate_rising', 'wbc_high'],
        raw_text: 'Lactate 2.4↑ (was 1.8 6h ago) · WBC 14.2↑ · Creatinine 1.1 (baseline 0.9)',
        data: { lactate: 2.4, lactate_prior_6h: 1.8, wbc: 14.2, creatinine: 1.1,
                creatinine_baseline: 0.9, inr: 1.2, platelets: 180 }
      },
      pha: {
        agent_id: 'pha', domain: 'pharmacy', confidence: 0.99, raw_confidence: 0.99,
        freshness_status: 'fresh', stale_seconds: 0,
        fetched_at: new Date(Date.now() - 22 * 60000).toISOString(),
        escalation_flags: [],
        raw_text: 'Pip-Tazo 3.375g IV q6h · Norepinephrine 0.05 mcg/kg/min · No interactions',
        data: {
          active_medications: [
            { name: 'Piperacillin-Tazobactam', dose: '3.375g', route: 'IV', frequency: 'q6h' },
            { name: 'Norepinephrine', dose: '0.05 mcg/kg/min', route: 'IV', frequency: 'continuous' },
          ],
          interactions_detected: [], nephrotoxins_active: [], anticoagulants_active: [],
          total_iv_24h_liters: 2.8
        }
      },
      nla: {
        agent_id: 'nla', domain: 'clinical_notes', confidence: 0.52, raw_confidence: 0.70,
        freshness_status: 'stale', stale_seconds: (4 * 3600) + (22 * 60),
        fetched_at: new Date(Date.now() - ((4 * 3600) + (22 * 60)) * 1000).toISOString(),
        escalation_flags: [],
        raw_text: 'Last note (10:08): tolerating O2 2L NC, alert and oriented x3. Sentiment: neutral.',
        data: { note_count: 2, sentiment: 'neutral', deterioration_keywords_found: [], nlp_model: 'mock' }
      },
      hia: {
        agent_id: 'hia', domain: 'patient_history', confidence: 0.81, raw_confidence: 0.81,
        freshness_status: 'fresh', stale_seconds: 0,
        fetched_at: new Date(Date.now() - 6 * 3600000).toISOString(),
        escalation_flags: ['prior_sepsis'],
        raw_text: '62F · T2DM (E11.9) · Prior UTI (N39.0) · Prior sepsis episode 2024 · No CKD/CHF/COPD',
        data: { age: 62, sex: 'F', prior_diagnoses_icd: ['E11.9', 'N39.0'],
                prior_sepsis: true, immunocompromised: false, prior_aki: false }
      }
    },
    compound_results: [
      {
        pattern: 'sepsis', detected: true, confidence: 0.87,
        agents_contributing: ['lra', 'hia'],
        conflict_detected: true,
        conflict_agents: ['vas', 'lra'],
        conflict_description: 'VAS reports hemodynamic compensation (BP recovering post-vasopressor wean). LRA reports ongoing metabolic stress — lactate climbing post-wean rather than clearing, which is the key discordance.',
        resolution_directive: 'LRA weighted primary — lactate trend post-wean outweighs momentary pressure recovery as sepsis staging signal. Vasopressor wean may be premature. Aggregate confidence penalized −0.04 for inter-agent divergence.',
        action_tier: 3,
        recommended_action: 'Blood cultures x2 · Lactate repeat in 2h · Review antibiotic coverage · Hold vasopressor wean pending repeat labs'
      },
      {
        pattern: 'aki', detected: false, confidence: 0.38,
        agents_contributing: ['lra'],
        conflict_detected: false, conflict_agents: [],
        conflict_description: '',
        resolution_directive: 'Creatinine elevation present (0.2 above baseline) but below KDIGO Stage 1 threshold. PHA: no active nephrotoxins. VAS: MAP > 65. Below advisory threshold — logged only.',
        action_tier: 1,
        recommended_action: 'Monitor creatinine at next lab draw'
      }
    ],
    conflicts: [
      // same as compound_results[0] — this is the sepsis conflict
    ],
    audit_log: [
      {
        timestamp: new Date(Date.now() - 3 * 60000).toISOString(),
        event_type: 'conflict_flagged', agent_id: 'lra', tier: 3,
        description: 'VAS↔LRA divergence detected — sepsis compound pattern. Attending notified via push.'
      },
      {
        timestamp: new Date(Date.now() - 75 * 60000).toISOString(),
        event_type: 'agent_suppressed', agent_id: 'nla', tier: 1,
        description: 'NLA confidence 0.52 below gate threshold 0.50 — suppressed from compound scoring.'
      },
      {
        timestamp: new Date(Date.now() - 98 * 60000).toISOString(),
        event_type: 'interaction_clear', agent_id: 'pha', tier: 1,
        description: 'PHA interaction check: Pip-Tazo + Norepinephrine — no known interaction. Logged, no clinical action.'
      },
      {
        timestamp: new Date(Date.now() - 210 * 60000).toISOString(),
        event_type: 'notify_sent', tier: 3,
        description: 'VAS: BP dip noted (MAP 61) — attending notified.',
        clinician_action: 'Vasopressor dose increased 0.04 → 0.05 mcg/kg/min. Wean deferred.'
      }
    ]
  }
}

// Second demo patient: Tier-4 autonomous alert (respiratory failure)
// Shows the highest human gate tier for contrast
export const MOCK_PATIENT_CHEN: Patient = {
  id: 'demo-002',
  name: 'Chen, D.',
  age: 74,
  sex: 'M',
  bed: 'Bed 7',
  unit: 'MICU',
  admitted_at: new Date(Date.now() - 18 * 3600000).toISOString(),
  primary_diagnosis: 'COPD exacerbation',
  aligned_state: {
    patient_id: 'demo-002',
    version: 12,
    aligned_at: new Date(Date.now() - 45000).toISOString(),
    state_hash: 'b7c2d9e4f1a3b8c0',
    aggregate_confidence: 0.95,
    highest_action_tier: 4,
    agent_outputs: {
      vas: {
        agent_id: 'vas', domain: 'vital_signs', confidence: 0.97, raw_confidence: 0.97,
        freshness_status: 'fresh', stale_seconds: 0,
        fetched_at: new Date(Date.now() - 8000).toISOString(),
        escalation_flags: ['spo2_lt_88', 'rr_gt_30', 'spo2_trending'],
        raw_text: 'SpO2 84%↓↓ (15-min decline confirmed) · RR 31 · HR 118 · BP 142/88',
        data: { hr: 118, sbp: 142, dbp: 88, map: 106, spo2: 84, rr: 31, temp_c: 37.1,
                trend_spo2_15m: 'declining', spo2_15m_ago: 89 }
      },
      lra: { agent_id: 'lra', domain: 'laboratory', confidence: 0.72, raw_confidence: 0.85,
             freshness_status: 'stale', stale_seconds: 8200, fetched_at: new Date(Date.now() - 8.2 * 3600000).toISOString(),
             escalation_flags: [], raw_text: 'ABG pH 7.31 · PaCO2 58 · Bicarb 24 (8h prior)',
             data: { ph: 7.31, paco2: 58, bicarb: 24 } },
      pha: { agent_id: 'pha', domain: 'pharmacy', confidence: 0.99, raw_confidence: 0.99,
             freshness_status: 'fresh', stale_seconds: 0, fetched_at: new Date(Date.now() - 5 * 60000).toISOString(),
             escalation_flags: [], raw_text: 'Albuterol neb q4h · Ipratropium q6h · IV methylprednisolone',
             data: { active_medications: [], interactions_detected: [] } },
      nla: { agent_id: 'nla', domain: 'clinical_notes', confidence: 0.68, raw_confidence: 0.68,
             freshness_status: 'fresh', stale_seconds: 0, fetched_at: new Date(Date.now() - 35 * 60000).toISOString(),
             escalation_flags: ['deterioration_keyword'],
             raw_text: 'Nurse note 14:05: "Increased work of breathing. Using accessory muscles. Distressed."',
             data: { sentiment: 'negative', deterioration_keywords_found: ['increased work of breathing', 'accessory muscles', 'distressed'] } },
      hia: { agent_id: 'hia', domain: 'patient_history', confidence: 0.82, raw_confidence: 0.82,
             freshness_status: 'fresh', stale_seconds: 0, fetched_at: new Date(Date.now() - 4 * 3600000).toISOString(),
             escalation_flags: ['copd_known'],
             raw_text: '74M · COPD GOLD III · 2 prior intubations · Ex-smoker 40 pack-year',
             data: { age: 74, sex: 'M', copd: true, prior_intubations: 2 } }
    },
    compound_results: [
      {
        pattern: 'respiratory_failure', detected: true, confidence: 0.95,
        agents_contributing: ['vas', 'nla', 'hia'],
        conflict_detected: false, conflict_agents: [],
        conflict_description: 'All agents converge — no conflict. High-confidence autonomous alert.',
        resolution_directive: 'VAS autonomous threshold breached (SpO2 < 88 + RR > 30). NLA confirms clinical distress. HIA: prior intubations increase urgency. Rapid response protocol activated.',
        action_tier: 4,
        recommended_action: '🚨 AUTONOMOUS — Rapid response paged · Supplemental O2 titration order pre-populated · Anesthesia notification queued'
      }
    ],
    conflicts: [],
    audit_log: [
      { timestamp: new Date(Date.now() - 45000).toISOString(), event_type: 'autonomous_action', tier: 4,
        description: '🚨 Autonomous alert fired — SpO2 84%, RR 31, 15-min decline confirmed. Rapid response paged.' },
      { timestamp: new Date(Date.now() - 38 * 60000).toISOString(), event_type: 'notify_sent', tier: 3,
        description: 'SpO2 89% trending down — physician notified.', clinician_action: 'O2 increased to 6L NC. Continue monitoring.' }
    ]
  }
}

export const DEMO_PATIENTS: Patient[] = [MOCK_PATIENT_JOHNSON, MOCK_PATIENT_CHEN]
```

---

## Component Specifications

### `AgentGraph.tsx` — React Flow 5-node graph

Model exactly after Austin's teamwork page React Flow graph, but with 5 ICU agent nodes instead of 7 ALI agents.

Node layout (horizontal left-to-right, coordinator in center):
```
VAS ──┐
LRA ──┤
PHA ──── [COORDINATOR] ──── [HUMAN GATE] ──── Aligned State
NLA ──┤
HIA ──┘
```

Node color coding:
- Fresh + no escalation flags: green (`#00ff9d`)
- Stale: amber (`#ffd000`)
- Escalation flags active: red (`#ff5050`)
- Unavailable: gray (`#444`)

Edge animation: pulse edge from each agent to coordinator when that agent has active escalation flags. No pulse when agent is below gate threshold.

Clicking a node opens the same telemetry drawer pattern as Austin — shows the `AgentOutput.raw_text` + escalation flags + confidence bar.

Conflict edge: when `conflict_detected: true`, draw a dashed red edge between the conflicting agent nodes with a label showing the conflict pattern.

### `NurseView.tsx` — Match the whitepaper wireframe exactly

Top section — Patient header bar:
- Bed number, patient name, age/sex
- Admitted duration (calculated from `admitted_at`)
- Aligned state badge: green "ALIGNED" or amber "⚠️ DIVERGENCE DETECTED"
- Last updated timestamp

Left panel — Agent Status Grid:
- 5 rows, one per agent
- Each row: colored dot (green/amber/red by freshness), agent ID, freshness label ("FRESH" / "STALE Xh Ym"), confidence value, right arrow
- If any agent is stale: amber "⚠️ Document or flag" note beneath that row
- Clicking an agent row opens its telemetry drawer

Right panel — Active Conflict (if any):
- Prominent amber/red border panel
- Conflict pattern title (e.g., "⚠️ VAS ↔ LRA DIVERGENCE")
- Plain English: "VAS says: [raw_text summary]" / "LRA says: [raw_text summary]"
- Resolution directive text
- Compound confidence score
- "→ ACTION: [recommended_action]" in highlighted block

If no conflict: show green "All agents aligned" panel with aggregate confidence.

Human Gate tier alert (pinned at top if tier 3 or 4):
- Tier 4 (autonomous): full-width red alert banner — "🚨 AUTONOMOUS ACTION TAKEN — [description]"
- Tier 3 (notify): full-width amber banner — "🔔 Clinician notification sent — [description]"

Bottom panel — Patient Timeline (Recharts LineChart):
- 6h window, 4 series: HR, SpO2, Lactate, WBC
- Generate synthetic trend data from the mock `data` fields (interpolate between current values and reasonable 6h-ago values)
- Event markers: dots on the timeline for each audit log entry

Activity list below timeline: most recent 4 audit log entries as compact rows

### `DoctorView.tsx` — Match the whitepaper wireframe exactly

Left column — Agent Telemetry panel:
- Each agent gets a card with: agent_id badge, domain, confidence (raw and post-penalty), freshness status, TTL remaining or stale duration, escalation flags as colored tags, `raw_text`
- Stale agents: amber background, staleness penalty displayed ("−0.18 penalty · conf was 0.70")

Right column — Conflict Registry:
- One card per conflict in `compound_results` where `conflict_detected: true`
- Shows: conflict ID, conflicting agents, position of each agent, resolution directive, confidence penalty applied
- "Below threshold" compound results shown in a collapsed "Suppressed signals" list

Bottom — Human Gate Log (AuditLog component):
- Full `audit_log` array rendered as a table
- Columns: timestamp, tier badge, event type, description, clinician action (if any)
- "Immutable audit trail" label — no delete or edit affordances

### `ConflictBanner.tsx`

```tsx
// Props: conflict: CompoundResult | null
// If null: renders green "All agents aligned" banner
// If conflict: renders amber border panel with the conflict description and resolution directive
// Should be the visually dominant element when conflict is present
```

### `GateAlert.tsx`

```tsx
// Props: tier: ActionTier, description: string, autonomousAction?: string
// Tier 4: red full-width banner with pulsing border animation
// Tier 3: amber full-width banner
// Tier 2: small advisory pill (non-intrusive)
// Tier 1: nothing rendered (suppressed)
```

---

## API Route (`src/app/api/msignals/patient/[id]/route.ts`)

```typescript
// GET /api/msignals/patient/[id]
// Returns mock data for demo-001 and demo-002
// Returns 404 for any other id
// In production: this route will proxy to the FastAPI backend at MSIGNALS_API_URL env var
// If MSIGNALS_API_URL is set and reachable, proxy. Otherwise return mock + previewMode: true.

export async function GET(request: Request, { params }: { params: { id: string } }) {
  const patient = DEMO_PATIENTS.find(p => p.id === params.id)
  if (!patient) return Response.json({ error: 'Patient not found' }, { status: 404 })
  return Response.json({ ...patient, previewMode: true })
}
```

---

## Styling & Color System

Match Austin's dark clinical aesthetic exactly. Colors:
```
background: #09090b (zinc-950)
card: #18181b (zinc-900)
border: #27272a (zinc-800)
green (fresh/aligned): #00ff9d
amber (stale/conflict): #ffd000
red (critical/autonomous): #ff5050
blue (info): #00f3ff
purple (agent accent): #bd00ff
```

Do not use any non-dark backgrounds. This is a clinical tool intended for use in darkened ICU environments.

---

## Navigation

Sidebar (minimal):
```
mSignals
─────────────
🏥 Patient Census    /
📊 Patient State     /patient/[id]
```

Patient Census page (the root `/` page): simple list of DEMO_PATIENTS as cards — bed number, name, age/sex, admitted duration, highest action tier badge. Clicking navigates to the patient detail page.

---

## Success Criteria

- [ ] `npm run dev` starts without TypeScript errors
- [ ] `/` shows patient census with MOCK_PATIENT_JOHNSON (Tier 3 badge) and MOCK_PATIENT_CHEN (Tier 4 badge)
- [ ] Clicking Johnson opens Nurse View with: amber "DIVERGENCE DETECTED" header, VAS↔LRA conflict panel, NLA staleness prompt, Tier 3 notify banner
- [ ] Clicking Doctor View tab shows: agent telemetry cards, conflict registry with resolution directive, full audit log
- [ ] Clicking Chen opens Nurse View with: Tier 4 autonomous alert banner (red, pulsing), green "All agents aligned" conflict panel (no conflict — convergent failure)
- [ ] React Flow graph renders with 5 nodes — VAS/LRA red (escalation flags), NLA amber (stale), PHA/HIA green
- [ ] Dashed red edge visible between VAS and LRA on Johnson patient (conflict edge)
- [ ] `npm run build` completes with no errors

## What NOT to Build

- Do NOT modify Austin files in `versions/signalsv3/`
- Do NOT build authentication — demo dashboard is unauthenticated for PoC
- Do NOT add FHIR integration, HL7 parsing, or any real clinical data connection
- Do NOT add a mobile view — desktop clinical workstation only
- Do NOT add user preferences, settings, or notification infrastructure
- Do NOT write unit tests — that is Stream 1's responsibility for the backend logic
