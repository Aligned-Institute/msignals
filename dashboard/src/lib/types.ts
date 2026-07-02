export type FreshnessStatus = 'fresh' | 'stale' | 'unavailable';
export type ActionTier = 1 | 2 | 3 | 4;
export type EscalationFlag = string;

export interface AgentOutput {
  agent_id: 'vas' | 'lra' | 'pha' | 'nla' | 'hia';
  domain: string;
  confidence: number;
  raw_confidence: number;
  freshness_status: FreshnessStatus;
  stale_seconds: number;           // 0 if fresh
  fetched_at: string;              // ISO 8601
  escalation_flags: EscalationFlag[];
  raw_text: string;                // human-readable summary of what the agent saw
  data: Record<string, unknown>;   // domain-specific data fields
}

export interface CompoundResult {
  pattern: 'sepsis' | 'aki' | 'respiratory_failure' | 'drug_conflict' | 'fluid_overload';
  detected: boolean;
  confidence: number;
  agents_contributing: string[];
  conflict_detected: boolean;
  conflict_agents: string[];
  conflict_description: string;
  resolution_directive: string;
  action_tier: ActionTier;
  recommended_action: string;
}

export interface AuditEntry {
  timestamp: string;               // ISO 8601
  event_type: 'conflict_flagged' | 'agent_suppressed' | 'interaction_clear' | 'autonomous_action' | 'notify_sent';
  agent_id?: string;
  tier: ActionTier;
  description: string;
  clinician_action?: string;       // set if clinician confirmed/dismissed
}

export interface ICUAlignedState {
  patient_id: string;
  version: number;
  aligned_at: string;              // ISO 8601;
  state_hash: string;
  agent_outputs: Record<string, AgentOutput>;
  compound_results: CompoundResult[];
  conflicts: CompoundResult[];     // subset where conflict_detected=true
  aggregate_confidence: number;
  highest_action_tier: ActionTier;
  audit_log: AuditEntry[];
}

export interface Patient {
  id: string;
  name: string;
  age: number;
  sex: 'M' | 'F';
  bed: string;
  unit: string;
  admitted_at: string;
  primary_diagnosis: string;
  aligned_state: ICUAlignedState;
}
