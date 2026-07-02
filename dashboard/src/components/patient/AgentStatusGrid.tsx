'use client';

import { useState } from 'react';
import { AgentOutput } from '@/lib/types';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Clock, ShieldAlert, CheckCircle2, AlertCircle, HelpCircle, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentStatusGridProps {
  agents: Record<string, AgentOutput>;
  onSelectAgent?: (agentId: string) => void;
}

export function AgentStatusGrid({ agents, onSelectAgent }: AgentStatusGridProps) {
  const [selectedAgent, setSelectedAgent] = useState<AgentOutput | null>(null);

  const getAgentLabel = (id: string) => {
    switch (id) {
      case 'vas': return 'Vital Signs [VAS]';
      case 'lra': return 'Lab Results [LRA]';
      case 'pha': return 'Pharmacy [PHA]';
      case 'nla': return 'Clinical Notes [NLA]';
      case 'hia': return 'Patient History [HIA]';
      default: return id.toUpperCase();
    }
  };

  const getFreshnessBadge = (status: string, staleSec: number) => {
    switch (status) {
      case 'fresh':
        return (
          <Badge className="bg-[#00ff9d]/15 text-[#00ff9d] border border-[#00ff9d]/30 font-mono text-[10px] px-2 py-0.5">
            <CheckCircle2 className="size-3 mr-1 inline" /> Fresh
          </Badge>
        );
      case 'stale':
        const hours = Math.floor(staleSec / 3600);
        const mins = Math.floor((staleSec % 3600) / 60);
        const label = hours > 0 ? `${hours}h ${mins}m ago` : `${mins}m ago`;
        return (
          <Badge className="bg-[#ffd000]/15 text-[#ffd000] border border-[#ffd000]/30 font-mono text-[10px] px-2 py-0.5">
            <Clock className="size-3 mr-1 inline" /> Stale ({label})
          </Badge>
        );
      default:
        return (
          <Badge className="bg-zinc-800 text-zinc-400 border border-zinc-700 font-mono text-[10px] px-2 py-0.5">
            <HelpCircle className="size-3 mr-1 inline" /> Unavailable
          </Badge>
        );
    }
  };

  const getStalenessPrompt = (id: string, status: string, staleSec: number) => {
    if (status !== 'stale') return null;
    const hours = Math.round(staleSec / 3600);
    switch (id) {
      case 'vas': return 'Document vitals or check monitor feed';
      case 'lra': return 'Check pending stat labs';
      case 'pha': return 'Verify medication list';
      case 'nla': return `No notes in ${hours}h. Document assessment`;
      case 'hia': return 'Verify history context';
      default: return 'Needs verification';
    }
  };

  return (
    <>
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {Object.values(agents).map((agent) => {
          const isStale = agent.freshness_status === 'stale';
          const prompt = getStalenessPrompt(agent.agent_id, agent.freshness_status, agent.stale_seconds);
          
          return (
            <Card
              key={agent.agent_id}
              onClick={() => {
                setSelectedAgent(agent);
                if (onSelectAgent) onSelectAgent(agent.agent_id);
              }}
              className={cn(
                "bg-card hover-lift cursor-pointer border relative select-none",
                isStale ? "border-[#ffd000]/30" : "border-border",
                agent.escalation_flags.length > 0 && !isStale && "border-[#ff5050]/30"
              )}
            >
              <CardContent className="p-4 flex flex-col justify-between h-full min-h-[140px] space-y-3">
                {/* Name & Freshness */}
                <div className="space-y-1.5">
                  <div className="text-xs font-bold text-white tracking-wide">
                    {getAgentLabel(agent.agent_id)}
                  </div>
                  {getFreshnessBadge(agent.freshness_status, agent.stale_seconds)}
                </div>

                {/* Score or Flags */}
                <div className="flex items-baseline justify-between">
                  <div className="font-mono text-zinc-500 text-[10px] uppercase tracking-wider">
                    Confidence
                  </div>
                  <div className={cn(
                    "text-xl font-bold font-mono",
                    agent.confidence > 0.8 ? "text-[#00ff9d]" : agent.confidence > 0.6 ? "text-[#ffd000]" : "text-[#ff5050]"
                  )}>
                    {Math.round(agent.confidence * 100)}%
                  </div>
                </div>

                {/* Prompts/Alerts */}
                {prompt && (
                  <div className="text-[10px] text-[#ffd000] font-mono leading-tight bg-[#ffd000]/5 border border-[#ffd000]/10 rounded p-1.5 flex gap-1 items-start">
                    <ShieldAlert className="size-3 shrink-0 mt-0.5" />
                    <span>{prompt}</span>
                  </div>
                )}
                
                {agent.escalation_flags.length > 0 && !isStale && (
                  <div className="text-[10px] text-[#ff5050] font-mono leading-tight bg-[#ff5050]/5 border border-[#ff5050]/10 rounded p-1.5 flex gap-1 items-start">
                    <AlertCircle className="size-3 shrink-0 mt-0.5" />
                    <span>Flags: {agent.escalation_flags.join(', ')}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Raw Telemetry Dialog */}
      <Dialog open={selectedAgent !== null} onOpenChange={(open) => !open && setSelectedAgent(null)}>
        <DialogContent className="sm:max-w-lg bg-[#0a1628] border border-border text-foreground font-mono">
          {selectedAgent && (
            <>
              <DialogHeader className="border-b border-border pb-4">
                <DialogTitle className="text-base font-bold text-[#00f3ff] flex items-center gap-2">
                  <FileText className="size-5" />
                  Raw Telemetry Output: {getAgentLabel(selectedAgent.agent_id)}
                </DialogTitle>
                <DialogDescription className="text-zinc-500 text-xs mt-1">
                  Fetched at: {new Date(selectedAgent.fetched_at).toLocaleString()}
                </DialogDescription>
              </DialogHeader>

              <div className="py-4 space-y-4">
                {/* Meta details */}
                <div className="grid grid-cols-2 gap-4 text-xs bg-secondary/20 p-3 rounded border border-border/40">
                  <div>
                    <span className="text-zinc-500">Domain:</span> {selectedAgent.domain}
                  </div>
                  <div>
                    <span className="text-zinc-500">Source:</span> {selectedAgent.agent_id === 'vas' ? 'chartevents' : selectedAgent.agent_id === 'lra' ? 'labevents' : 'prescriptions'}
                  </div>
                  <div>
                    <span className="text-zinc-500">Raw Confidence:</span> {Math.round(selectedAgent.raw_confidence * 100)}%
                  </div>
                  <div>
                    <span className="text-zinc-500">Penalized:</span> {Math.round((selectedAgent.raw_confidence - selectedAgent.confidence) * 100)}%
                  </div>
                </div>

                {/* Raw Text */}
                <div className="space-y-1.5">
                  <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold">Clinical Output Text</div>
                  <pre className="whitespace-pre-wrap rounded border border-border bg-[#050b14]/80 p-4 text-xs text-[#00ff9d] leading-relaxed overflow-x-auto">
                    {selectedAgent.raw_text}
                  </pre>
                </div>

                {/* Escalation Flags */}
                {selectedAgent.escalation_flags.length > 0 && (
                  <div className="space-y-1.5">
                    <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold">Active Escalation Flags</div>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedAgent.escalation_flags.map((flag) => (
                        <Badge key={flag} className="bg-[#ff5050]/20 text-[#ff5050] border border-[#ff5050]/30 text-[10px] px-2 py-0.5">
                          {flag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
