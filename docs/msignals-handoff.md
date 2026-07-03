# mSignals ICU — Project Handoff

**Issued:** 2026-07-02
**From:** Antigravity AI
**To:** Next Agent
**Current Status:** Phase 0, 1, and 2 Complete — Awaiting Phase 3 (Validation Study) & Schmidt Sciences Enhancements

---

## 1. Project Overview & Status

We have completed the three primary bootstrap streams for the mSignals ICU multi-agent alignment vertical. The project is fully functional, fully tested (100% test pass rate), and tracked on the remote repository.

*   **Stream 1 — Backend ICU alignment engine:** Implemented the core `ICUAgent` ABC in [base.py](file:///Users/warmachine/Documents/PROJECTS/ALI/2-Labs/Research/mas/verticals/msignals/src/agents/base.py), 5 clinical agents (`vas.py`, `lra.py`, `pha.py`, `nla.py`, `hia.py`), governor contracts, MIMIC data lazy loaders, compound evaluation rules (Sepsis, AKI, Resp Failure, Drug-Physiology Conflict, Fluid Overload), and the `ICUCoordinator`.
*   **Stream 2 — Next.js 16 Dark-Theme Dashboard:** Created a premium dashboard under `dashboard/` with dynamic React Flow 5-node horizontal topology mapping, tabbed Doctor telemetry view, Nurse action checklist view, historical Recharts trend charts, and real-time SWR polling routes.
*   **Stream 3 — Notes NLP BioClinicalBERT Agent:** Replaced the NLA mock stub with a zero-shot clinical notes embedding classifier using `emilyalsentzer/Bio_ClinicalBERT` and a keyword-guided negation fallback engine.

---

## 2. Directory Map (Clickable)

*   [src/agents/base.py](file:///Users/warmachine/Documents/PROJECTS/ALI/2-Labs/Research/mas/verticals/msignals/src/agents/base.py) - ICUAgent base ABC & AgentOutput schema
*   [src/agents/nla.py](file:///Users/warmachine/Documents/PROJECTS/ALI/2-Labs/Research/mas/verticals/msignals/src/agents/nla.py) - BioClinicalBERT zero-shot & regex fallback Notes Agent
*   [src/coordinator.py](file:///Users/warmachine/Documents/PROJECTS/ALI/2-Labs/Research/mas/verticals/msignals/src/coordinator.py) - ICUCoordinator (temporal alignment & conflict registry)
*   [src/rules/compound.py](file:///Users/warmachine/Documents/PROJECTS/ALI/2-Labs/Research/mas/verticals/msignals/src/rules/compound.py) - ICU compound risk & divergence rules
*   [dashboard/src/app/page.tsx](file:///Users/warmachine/Documents/PROJECTS/ALI/2-Labs/Research/mas/verticals/msignals/dashboard/src/app/page.tsx) - Clinical Census panel
*   [dashboard/src/app/patient/\[id\]/page.tsx](file:///Users/warmachine/Documents/PROJECTS/ALI/2-Labs/Research/mas/verticals/msignals/dashboard/src/app/patient/%5Bid%5D/page.tsx) - Patient aligned details view (tabs, graph, charts)
*   [tests/test_nla.py](file:///Users/warmachine/Documents/PROJECTS/ALI/2-Labs/Research/mas/verticals/msignals/tests/test_nla.py) - Notes Agent unit tests (20 labeled notes)
*   [docs/msignals-build-plan.md](file:///Users/warmachine/Documents/PROJECTS/ALI/2-Labs/Research/mas/verticals/msignals/docs/msignals-build-plan.md) - Master Phase roadmap

---

## 3. Platform & Framework Specifications

To prevent compiler or runtime regressions, adhere to the following stack rules:
1.  **Tailwind CSS v4 Configuration:** Tailwind v4 removes the config file structure. Define all custom styles, theme variables, and extensions inside the `@theme` directive of the [globals.css](file:///Users/warmachine/Documents/PROJECTS/ALI/2-Labs/Research/mas/verticals/msignals/dashboard/src/app/globals.css) file. Do not create or run a `tailwind.config.ts` file, as it will break the PostCSS compilation.
2.  **Radix Primitives:** In this workspace, Radix components are imported directly from `"radix-ui"` (e.g. `import { Slot } from "radix-ui"`) rather than modular `@radix-ui/react-...` packages.
3.  **Local Dev Server Port:** If Austin is running on localhost:3000, start the mSignals dashboard on **localhost:3001** to avoid port collisions:
    ```bash
    npm run dev -- -p 3001
    ```
4.  **NLA Dynamic Loading:** The NLP agent imports torch/transformers dynamically during model initialization. If weights are missing, it falls back gracefully to a regex pipeline, reporting `nlp_model: 'regex_fallback'`.

---

## 4. Verification and Execution Commands

Run these commands from `verticals/msignals/` to verify backend correctness:
*   **Run All 31 Unit Tests:**
    ```bash
    PYTHONPATH=. pytest tests/ -v
    ```
*   **Verify Dashboard Build:**
    ```bash
    cd dashboard/ && npm run build
    ```
*   **Launch Dashboard Dev Server:**
    ```bash
    cd dashboard/ && npm run dev -- -p 3001
    ```

---

## 5. Next Steps — Starting Phase 3 (Validation Study)

Your priority is to conduct **Phase 3 — Validation Study and Publication**. Follow this sequence:

1.  **Prepare the Retrospective Cohort:**
    *   Load the downloaded MIMIC-IV demo dataset under `verticals/msignals/data/physionet.org/files/mimic-iv-demo/2.2`.
    *   Filter adult patients with hospital stays ≥ 24 hours.
    *   Map diagnoses to ICD codes (sepsis: `A41.x`, AKI: `N17.x-N19.x`, respiratory failure: `J96.x`).
2.  **Run Comparative Benchmarks:**
    *   Implement baseline models for comparison:
        *   Single-parameter thresholds (traditional bedside alarms)
        *   Epic Deterioration Index score trajectory
        *   SIRS/SOFA score progression
    *   Run the `ICUCoordinator` over these patient streams.
3.  **Validate Metrics:**
    *   Measure the AUROC score at a 6-hour forecast window for sepsis and AKI.
    *   Quantify early warning lead time: how many minutes earlier does the multi-agent alignment registry detect deterioration compared to the single-alarm baseline?
    *   Assert false alarm rates stay below the threshold limits.
4.  **Draft Manuscript:**
    *   Prepare results for publication targeting *Critical Care Medicine* or *JAMIA* to provide the peer-reviewed clinical validation required for future FDA 510(k) applications.

---

## 6. Schmidt Sciences Proposal Enhancements (Future Phases)

To align with the Tier 2 Schmidt Sciences proposal specifications, the next agent must architect and implement the following primitives:

### 6.1 Multi-Principal Agent Registry (Phase 6)
*   **Database Migrations:** Add `principal_id` (UUID), `payment_address` (text), `scope_constraints` (JSONB), and `reputation_score` (float) columns to the `source_registry` table schema.
*   **Access Control:** Reject any agent query during fetch cycles that is not registered and validated within active scope boundaries.

### 6.2 Dual-Node Consensus Orchestrator (Phase 6)
*   **Active-Active Execution:** Configure the `ICUCoordinator` to run in a dual-node topology (Primary and Secondary instances).
*   **Consensus Check:** Compare AlignedState output hashes from both nodes. Disagreement on final outputs raises a `consensus_failure` alert to the `alerts` database table and halts settlement.

### 6.3 Resilient Sub-Agent Triads (Phase 7)
*   **Refactor Agents:** Transition each raw domain agent in `src/agents/` to a structured Runner-Watcher-Verifier triad:
    *   `Runner`: Stateful/stateless telemetry data collector.
    *   `Watcher`: Process health monitor enforcing agent TTL, executing respawns, and reporting failures to the Overseer.
    *   `Verifier`: Output format validator gating coordinator publication.

### 6.4 Continuous Operation Mode (Phase 8)
*   **Scheduler:** Trigger runner operations autonomously on fixed TTL durations (`dispatch_schedule` table).
*   **Live CAS & Alerts:** Update the aligned states table incrementally and trigger events to `alerts` when confidence shifts exceed delta bounds.

### 6.5 x402 Micropayments & ZKP Verification (Phase 9)
*   **Micropayments:** Gate Circle USDC payments based on quality scores evaluated by the `PaymentAuthorizationGate`.
*   **ADP 8.5 ZKP Proofs:** Incorporate zero-knowledge tokens verifying context provenance on the Arc L1 blockchain.
