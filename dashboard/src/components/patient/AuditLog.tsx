'use client';

import { AuditEntry } from '@/lib/types';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { GitCompare, ToggleLeft, Activity, UserCheck, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AuditLogProps {
  logs: AuditEntry[];
}

export function AuditLog({ logs }: AuditLogProps) {
  const getEventBadge = (type: string) => {
    switch (type) {
      case 'conflict_flagged':
        return (
          <Badge className="bg-[#ffd000]/15 text-[#ffd000] border border-[#ffd000]/30 font-mono text-[9px] px-2 py-0.5 flex items-center gap-1 w-fit">
            <GitCompare className="size-3" /> Divergence
          </Badge>
        );
      case 'agent_suppressed':
        return (
          <Badge className="bg-zinc-800 text-zinc-400 border border-zinc-700 font-mono text-[9px] px-2 py-0.5 flex items-center gap-1 w-fit">
            <ToggleLeft className="size-3" /> Suppressed
          </Badge>
        );
      case 'autonomous_action':
        return (
          <Badge className="bg-[#ff5050]/15 text-[#ff5050] border border-[#ff5050]/30 font-mono text-[9px] px-2 py-0.5 flex items-center gap-1 w-fit">
            <Activity className="size-3" /> Autonomous
          </Badge>
        );
      case 'notify_sent':
        return (
          <Badge className="bg-[#00f3ff]/15 text-[#00f3ff] border border-[#00f3ff]/30 font-mono text-[9px] px-2 py-0.5 flex items-center gap-1 w-fit">
            <ShieldAlert className="size-3" /> Alert Sent
          </Badge>
        );
      default:
        return (
          <Badge className="bg-zinc-800 text-zinc-300 border border-zinc-750 font-mono text-[9px] px-2 py-0.5 flex items-center gap-1 w-fit">
            <UserCheck className="size-3" /> Log Event
          </Badge>
        );
    }
  };

  return (
    <div className="rounded-lg border border-border bg-[#050b14]/30 overflow-hidden">
      <div className="px-5 py-4 border-b border-border bg-[#050b14]/50 flex items-center justify-between">
        <h4 className="text-xs font-bold text-white tracking-wide uppercase font-mono">
          ICU Aligned State Audit Log
        </h4>
        <div className="text-[10px] text-zinc-500 font-mono">
          Immutable Blockchain Ledger Hash: verified
        </div>
      </div>
      <Table className="font-mono text-xs select-none">
        <TableHeader className="bg-secondary/20">
          <TableRow className="border-b border-border/80">
            <TableHead className="text-zinc-500 w-[120px] py-3 pl-5">Timestamp</TableHead>
            <TableHead className="text-zinc-500 w-[140px] py-3">Event Type</TableHead>
            <TableHead className="text-zinc-500 py-3">Description</TableHead>
            <TableHead className="text-zinc-500 py-3 pr-5 text-right">Clinician Override / Note</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {logs.map((log, index) => (
            <TableRow key={index} className="border-b border-border hover:bg-secondary/10">
              <TableCell className="text-zinc-400 font-medium py-3 pl-5">
                {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </TableCell>
              <TableCell className="py-3">
                {getEventBadge(log.event_type)}
              </TableCell>
              <TableCell className="text-zinc-200 py-3 font-sans leading-relaxed">
                {log.description}
              </TableCell>
              <TableCell className="text-right py-3 pr-5">
                {log.clinician_action ? (
                  <div className="inline-flex items-center gap-1 text-[11px] text-[#00ff9d] bg-[#00ff9d]/5 border border-[#00ff9d]/20 px-2 py-0.5 rounded font-sans text-left">
                    <UserCheck className="size-3 text-[#00ff9d] shrink-0" />
                    <span>{log.clinician_action}</span>
                  </div>
                ) : (
                  <span className="text-zinc-600">—</span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
