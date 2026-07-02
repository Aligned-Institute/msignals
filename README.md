# mSignals: Multi-Agent Patient State Alignment Engine

mSignals is an acute care monitoring platform powered by the Aligned Institute's Multi-Principal Agent System. It continuously aligns patient telemetry, notes, and medication streams to identify early clinical deterioration in the ICU.

Unlike generic risk scoring systems, mSignals is built around a core clinical differentiator: **detecting and resolving inter-agent conflicts and clinical divergence** (such as vital sign stability masking rising laboratory lactate levels) rather than outputting a single aggregate risk score.

---

## Repository Structure

```
verticals/msignals/
├── config/
│   └── icu_default.json         # Default agent parameters, publish & gate thresholds
├── data/
│   └── physionet.org/           # MIMIC-IV demo dataset (ignored by git, retrieve locally)
├── src/                         # STREAM 1 — CLINICAL REASONING BACKEND
│   ├── coordinator.py           # ICU Coordinator (temporal alignment & conflict registry)
│   ├── agents/
│   │   ├── base.py              # Standalone ICUAgent ABC & AgentOutput schema
│   │   ├── vas.py               # Vital Signs Agent
│   │   ├── lra.py               # Lab Results Agent
│   │   ├── pha.py               # Pharmacy Agent
│   │   ├── nla.py               # Clinical Notes Agent (NLP keyword scanner stub)
│   │   └── hia.py               # Patient History Agent (prior sepsis & comorbidities)
│   ├── data/
│   │   └── mimic.py             # MIMIC-IV lazy loading loader
│   ├── governor/
│   │   └── contracts_icu.py     # ICU governor contracts (gating & publishing thresholds)
│   └── rules/
│       └── compound.py          # Rules: Sepsis, AKI, Resp Failure, Drug Conflict, Fluid Overload
├── tests/                       # STREAM 1 — BACKEND UNIT TESTS
│   ├── test_agents.py
│   ├── test_compound.py
│   └── test_coordinator.py
└── dashboard/                   # STREAM 2 — NEXT.JS CLINICAL DASHBOARD
    ├── postcss.config.mjs       # Tailwind CSS v4 configurations
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx       # Clinical theme layout (Outfit & Inter fonts, Sidebar)
    │   │   ├── page.tsx         # Patient Census View (MICU occupancy)
    │   │   └── patient/[id]/    # Patient Detail View (tabs: Nurse / Doctor)
    │   ├── components/
    │   │   ├── patient/
    │   │   │   ├── AgentGraph.tsx      # React Flow 5-node horizontal network topology
    │   │   │   ├── NurseView.tsx       # Nurse Dashboard (score-free, action checklist)
    │   │   │   ├── DoctorView.tsx      # Doctor Dashboard (telemetry confidence math)
    │   │   │   ├── AgentStatusGrid.tsx # Freshness grid & raw text overlays
    │   │   │   ├── ConflictBanner.tsx  # Vis-à-vis clinical divergence display
    │   │   │   ├── GateAlert.tsx       # Action alert banners (T3 Notify vs. T4 Autonomous)
    │   │   │   ├── PatientTimeline.tsx # Recharts grid trends (HR, SpO2, Lactate, WBC)
    │   │   │   └── AuditLog.tsx        # Aligned state audit log
    │   │   └── ui/              # Shadcn UI primitives
    │   └── lib/
    │       ├── mock-data.ts     # Profile mocks for Sepsis Conflict and Resp Failure
    │       └── types.ts         # TypeScript definitions matching backend schemas
```

---

## Core Product Abstractions

### 1. Standalone Base Agent (`src/agents/base.py`)
To prevent system-level framework changes from causing breaking failures in patient monitoring pipelines, the `ICUAgent` base class is standalone (decoupled from parent repositories). It features:
*   Timezone-aware UTC datetime tracking.
*   A step-wise confidence degradation decay algorithm:
    $$\text{breaches} = \lfloor \frac{\text{stale\_seconds}}{\text{ttl\_seconds}} \rfloor$$
    $$\text{net\_confidence} = \max(0, \text{raw\_confidence} - \text{penalty\_per\_ttl} \times \text{breaches})$$

### 2. Sepsis Conflict Logic & Resolution
Standard sepsis scores miss early shock when vital signs are temporarily normal (compensated). mSignals identifies a critical **VAS/LRA Sepsis Conflict** when:
*   **Vital Signs Agent (VAS)** is stable (no flags triggered).
*   **Lab Results Agent (LRA)** reports a rising lactate level (`lactate_rising` flag).
*   The system scales LRA confidence ($LRA_{\text{confidence}} \times 0.85$), alerts the clinician of occult hypoperfusion, and overrides pressor wean instructions.

---

## Setup and Installation

### Stream 1: Python Package Setup
1. Create a python virtual environment and install standard testing dependencies (e.g. `pytest`, `pytest-asyncio`):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install pytest pytest-asyncio
   ```
2. Run the test suite:
   ```bash
   PYTHONPATH=. python3 -m pytest tests/ -v
   ```

### Stream 2: Next.js Clinical Dashboard
The dashboard uses **Next.js 16 (App Router)**, **Tailwind CSS v4**, and **React Flow v12**.
1. Navigate to the dashboard directory:
   ```bash
   cd dashboard
   ```
2. Install dependencies:
   ```bash
   npm install --legacy-peer-deps
   ```
3. Run the development server (configured on port `3001` to avoid conflicts with other local dev servers):
   ```bash
   npm run dev -- -p 3001
   ```
4. Access the dashboard at [http://localhost:3001](http://localhost:3001).

---

## Verification Summary
*   **Backend Tests:** All 24 clinical rule and agent alignment scenarios pass (100% success rate).
*   **Frontend Compilation:** `npm run build` generates clean optimized production bundles with 0 compilation warnings or errors.
