'use client';

import { Patient } from '@/lib/types';
import { AgentStatusGrid } from './AgentStatusGrid';
import { ConflictBanner } from './ConflictBanner';
import { GateAlert } from './GateAlert';
import { PatientTimeline } from './PatientTimeline';
import { AuditLog } from './AuditLog';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { FileText, ClipboardList } from 'lucide-react';

interface NurseViewProps {
  patient: Patient;
}

export function NurseView({ patient }: NurseViewProps) {
  const state = patient.aligned_state;
  const activeConflict = state.conflicts[0];

  // Action checklist items extracted from recommendations
  const getChecklistItems = () => {
    if (patient.id === 'demo-002') {
      return [
        { id: 'c1', text: 'TITRATE supplemental O2 to maintain saturation above 88%' },
        { id: 'c2', text: 'VERIFY rapid response page has been received by medical lead' },
        { id: 'c3', text: 'PREPARE non-invasive positive pressure ventilation (NIPPV) cart' },
        { id: 'c4', text: 'CONFIRM stat ABG order drawn and sent to lab' }
      ];
    } else {
      return [
        { id: 'j1', text: 'DRAW stat blood cultures x2 (two separate sites)' },
        { id: 'j2', text: 'MEASURE repeat lactate level (due within 2h)' },
        { id: 'j3', text: 'VERIFY active Pip-Tazo infusion schedule' },
        { id: 'j4', text: 'HOLD vasopressor wean protocol pending clinical review' }
      ];
    }
  };

  return (
    <div className="space-y-6">
      {/* Alert Tier Header Banner */}
      <GateAlert
        tier={state.highest_action_tier}
        description={
          activeConflict
            ? activeConflict.recommended_action
            : state.compound_results[0]?.recommended_action || "Patient state normal. Continue routine continuous vitals and lab alignment monitoring."
        }
      />

      {/* Active Conflict Detail */}
      {activeConflict && <ConflictBanner conflict={activeConflict} />}

      {/* Agent Monitoring Status Grid */}
      <div className="space-y-3">
        <div className="text-xs font-mono uppercase tracking-widest text-zinc-500 font-bold px-1">
          Agent Monitoring Feed (Freshness & Confidence)
        </div>
        <AgentStatusGrid agents={state.agent_outputs} />
      </div>

      {/* Grid: Checklist & Timeline */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Checklist */}
        <Card className="bg-card border-border select-none lg:col-span-1">
          <div className="px-5 py-4 border-b border-border bg-[#050b14]/50 flex items-center gap-2">
            <ClipboardList className="size-4 text-[#00f3ff]" />
            <h4 className="text-xs font-bold text-white tracking-wide uppercase font-mono">
              Action Checklist
            </h4>
          </div>
          <CardContent className="p-5 space-y-4">
            {getChecklistItems().map((item) => (
              <div key={item.id} className="flex items-start gap-3 text-xs leading-relaxed">
                <Checkbox id={item.id} className="mt-0.5" />
                <label
                  htmlFor={item.id}
                  className="font-medium text-zinc-300 cursor-pointer select-none"
                >
                  {item.text}
                </label>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Audit Log preview */}
        <div className="lg:col-span-2">
          <AuditLog logs={state.audit_log.slice(0, 3)} />
        </div>
      </div>

      {/* Timeline Graphs */}
      <PatientTimeline patient={patient} />
    </div>
  );
}
