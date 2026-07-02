'use client';

import { Patient, AgentOutput, CompoundResult } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { AuditLog } from './AuditLog';
import { ShieldCheck, ToggleLeft, ArrowRightLeft, ShieldAlert, Cpu, GitBranch, AlertCircle, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DoctorViewProps {
  patient: Patient;
}

export function DoctorView({ patient }: DoctorViewProps) {
  const state = patient.aligned_state;

  const getAgentName = (id: string) => {
    switch (id) {
      case 'vas': return 'Vital Signs [VAS]';
      case 'lra': return 'Lab Results [LRA]';
      case 'pha': return 'Pharmacy [PHA]';
      case 'nla': return 'Clinical Notes [NLA]';
      case 'hia': return 'Patient History [HIA]';
      default: return id.toUpperCase();
    }
  };

  const getFreshnessStyle = (status: string) => {
    switch (status) {
      case 'fresh': return 'text-[#00ff9d]';
      case 'stale': return 'text-[#ffd000]';
      default: return 'text-zinc-500';
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Agent Telemetry Cards (detailed confidence penalty readouts) */}
      <div className="space-y-3">
        <div className="text-xs font-mono uppercase tracking-widest text-zinc-500 font-bold px-1 flex items-center gap-1.5">
          <Cpu className="size-3.5" />
          <span>Active Agent Telemetry Readouts</span>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4">
          {Object.values(state.agent_outputs).map((agent) => {
            const isStale = agent.freshness_status === 'stale';
            const penalty = agent.raw_confidence - agent.confidence;
            
            return (
              <Card key={agent.agent_id} className="bg-card border-border select-none overflow-hidden">
                <CardHeader className="px-4 py-3 border-b border-border/40 bg-[#050b14]/50 flex flex-row items-center justify-between space-y-0">
                  <span className="text-xs font-bold text-white tracking-wide">
                    {getAgentName(agent.agent_id)}
                  </span>
                  <Cpu className="size-3.5 text-zinc-500" />
                </CardHeader>
                <CardContent className="p-4 space-y-3 text-xs">
                  {/* Confidence Summary */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px] font-mono text-zinc-500">
                      <span>Telemetry Conf.</span>
                      <span className={getFreshnessStyle(agent.freshness_status)}>
                        {agent.freshness_status.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-2xl font-bold font-mono text-white flex items-baseline gap-1">
                      {Math.round(agent.confidence * 100)}%
                      {penalty > 0 && (
                        <span className="text-[10px] text-[#ff5050] font-normal">
                          (−{Math.round(penalty * 100)}%)
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Math Breakdown */}
                  <div className="bg-[#050b14]/30 border border-border/40 rounded p-2 font-mono text-[10px] text-zinc-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Raw Conf:</span>
                      <span>{Math.round(agent.raw_confidence * 100)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Stale Penalty:</span>
                      <span className={penalty > 0 ? "text-[#ff5050]" : ""}>
                        {penalty > 0 ? `-${Math.round(penalty * 100)}%` : '0%'}
                      </span>
                    </div>
                    <div className="flex justify-between border-t border-border/30 pt-1 mt-1 font-bold text-zinc-300">
                      <span>Net Score:</span>
                      <span>{Math.round(agent.confidence * 100)}%</span>
                    </div>
                  </div>

                  {/* Raw summary */}
                  <div className="space-y-1">
                    <div className="text-[9px] uppercase tracking-wider text-zinc-500 font-bold">Latest Output</div>
                    <p className="text-[11px] text-zinc-300 line-clamp-3 font-sans leading-relaxed">
                      {agent.raw_text}
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* 2. Conflict Registry (active vs historical/suppressed conflicts) */}
      <div className="space-y-3">
        <div className="text-xs font-mono uppercase tracking-widest text-zinc-500 font-bold px-1 flex items-center gap-1.5">
          <GitBranch className="size-3.5" />
          <span>Clinical Conflict & Rule Resolution Registry</span>
        </div>

        <div className="rounded-lg border border-border bg-[#050b14]/30 overflow-hidden">
          <Table className="font-mono text-xs select-none">
            <TableHeader className="bg-secondary/20">
              <TableRow className="border-b border-border/80">
                <TableHead className="text-zinc-500 py-3 pl-5">Clinical Rule Pattern</TableHead>
                <TableHead className="text-zinc-500 py-3">Trigger Status</TableHead>
                <TableHead className="text-zinc-500 py-3">Divergence Type</TableHead>
                <TableHead className="text-zinc-500 py-3">Conflict Agents</TableHead>
                <TableHead className="text-zinc-500 py-3">Clinical Conflict Description</TableHead>
                <TableHead className="text-zinc-500 py-3 pr-5 text-right">Action Tier</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {state.compound_results.map((rule, idx) => (
                <TableRow key={idx} className="border-b border-border hover:bg-secondary/10">
                  <TableCell className="font-bold text-white py-3 pl-5 capitalize">
                    {rule.pattern.replace('_', ' ')}
                  </TableCell>
                  <TableCell className="py-3">
                    {rule.detected ? (
                      <Badge className="bg-[#ff5050]/15 text-[#ff5050] border border-[#ff5050]/30 font-mono text-[9px] px-2 py-0.5">
                        TRIGGERED
                      </Badge>
                    ) : (
                      <Badge className="bg-zinc-800 text-zinc-500 border border-zinc-700 font-mono text-[9px] px-2 py-0.5">
                        CLEAR
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="py-3">
                    {rule.conflict_detected ? (
                      <Badge className="bg-[#ffd000]/15 text-[#ffd000] border border-[#ffd000]/30 font-mono text-[9px] px-2 py-0.5">
                        DIVERGENT
                      </Badge>
                    ) : (
                      <span className="text-zinc-500">None</span>
                    )}
                  </TableCell>
                  <TableCell className="py-3 font-bold text-zinc-300">
                    {rule.conflict_agents.length > 0 ? rule.conflict_agents.map(a => a.toUpperCase()).join(' ↔ ') : '—'}
                  </TableCell>
                  <TableCell className="text-zinc-300 py-3 max-w-[280px] font-sans leading-relaxed">
                    {rule.conflict_detected ? rule.conflict_description : 'No active inter-agent conflicts registered.'}
                  </TableCell>
                  <TableCell className="text-right py-3 pr-5 font-bold text-white">
                    Tier {rule.action_tier}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* 3. Audit Log table */}
      <div className="space-y-3">
        <AuditLog logs={state.audit_log} />
      </div>
    </div>
  );
}
