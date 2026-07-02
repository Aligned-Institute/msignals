'use client';

import { CompoundResult } from '@/lib/types';
import { GitCompare, ArrowRightLeft, ShieldAlert } from 'lucide-react';

interface ConflictBannerProps {
  conflict: CompoundResult;
}

export function ConflictBanner({ conflict }: ConflictBannerProps) {
  return (
    <div className="rounded-lg border border-border bg-gradient-to-br from-[#0a1628]/95 to-[#162236]/40 p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <GitCompare className="size-4.5 text-[#ffd000]" />
          <h3 className="text-sm font-semibold text-[#ffd000] font-sans tracking-wide">
            Active Clinical Conflict Detected
          </h3>
        </div>
        <div className="text-[10px] font-mono bg-zinc-800 text-zinc-400 border border-zinc-700 px-2 py-0.5 rounded">
          Sepsis Pattern #102
        </div>
      </div>

      {/* Vis-a-vis representation */}
      <div className="grid md:grid-cols-2 gap-4 relative">
        {/* Connector Icon */}
        <div className="hidden md:flex absolute inset-0 items-center justify-center pointer-events-none">
          <div className="bg-[#101f35] border border-border rounded-full p-2 text-zinc-500">
            <ArrowRightLeft className="size-4 text-[#ffd000]" />
          </div>
        </div>

        {/* VAS Side */}
        <div className="bg-[#050b14]/50 border border-border/40 rounded-lg p-4 space-y-2">
          <div className="text-[10px] font-mono uppercase tracking-wider text-[#00f3ff]">
            [VAS] Vital Signs Agent
          </div>
          <div className="text-xs font-semibold text-white/90">
            Hemodynamic Compensation Active
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Patient vital signs indicate normal MAP (73 mmHg), stable heart rate (102 bpm), and no pressure alerts. Indicates compensation is holding.
          </p>
        </div>

        {/* LRA Side */}
        <div className="bg-[#050b14]/50 border border-border/40 rounded-lg p-4 space-y-2">
          <div className="text-[10px] font-mono uppercase tracking-wider text-[#bd00ff]">
            [LRA] Lab Results Agent
          </div>
          <div className="text-xs font-semibold text-[#ff5050]">
            Ongoing Metabolic Stress
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Lactate levels rose from 1.8 to 2.4 mmol/L over the last 6 hours post-wean, indicating occult cellular hypoperfusion.
          </p>
        </div>
      </div>

      {/* Resolution Directive */}
      <div className="bg-[#ffd000]/5 border border-[#ffd000]/25 rounded-lg p-4 flex gap-3 text-xs">
        <ShieldAlert className="size-5 text-[#ffd000] shrink-0 mt-0.5" />
        <div className="space-y-1 leading-relaxed">
          <div className="font-bold text-[#ffd000] uppercase tracking-wider font-mono">
            MAS Control Resolution Directive:
          </div>
          <p className="text-zinc-300 font-medium font-mono text-[11px]">
            {conflict.resolution_directive}
          </p>
        </div>
      </div>
    </div>
  );
}
