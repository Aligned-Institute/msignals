import { Patient } from "./types";

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
      {
        pattern: 'sepsis', detected: true, confidence: 0.87,
        agents_contributing: ['lra', 'hia'],
        conflict_detected: true,
        conflict_agents: ['vas', 'lra'],
        conflict_description: 'VAS reports hemodynamic compensation (BP recovering post-vasopressor wean). LRA reports ongoing metabolic stress — lactate climbing post-wean rather than clearing, which is the key discordance.',
        resolution_directive: 'LRA weighted primary — lactate trend post-wean outweighs momentary pressure recovery as sepsis staging signal. Vasopressor wean may be premature. Aggregate confidence penalized −0.04 for inter-agent divergence.',
        action_tier: 3,
        recommended_action: 'Blood cultures x2 · Lactate repeat in 2h · Review antibiotic coverage · Hold vasopressor wean pending repeat labs'
      }
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
        clinician_action: 'Vasopressor dose increased 0.04 → 0.05 mcg/kg/min. Defer wean.'
      }
    ]
  }
};

// Second demo patient: Tier-4 autonomous alert (respiratory failure)
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
};

export const DEMO_PATIENTS: Patient[] = [MOCK_PATIENT_JOHNSON, MOCK_PATIENT_CHEN];
