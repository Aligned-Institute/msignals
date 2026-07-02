'use client';

import { ActionTier } from '@/lib/types';
import { AlertTriangle, ShieldCheck, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface GateAlertProps {
  tier: ActionTier;
  description: string;
}

export function GateAlert({ tier, description }: GateAlertProps) {
  if (tier <= 1) return null; // Suppressed / Tier-1 does not render alerts

  return (
    <div
      className={cn(
        "relative w-full rounded-lg border p-4 font-mono select-none overflow-hidden transition-all duration-100",
        tier === 4
          ? "bg-[#ff5050]/10 border-[#ff5050] text-[#ff5050] glow-red animate-pulse"
          : "bg-[#ffd000]/10 border-[#ffd000] text-[#ffd000] glow-yellow"
      )}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          {tier === 4 ? (
            <Zap className="size-5 fill-current animate-bounce" />
          ) : (
            <AlertTriangle className="size-5 fill-current" />
          )}
        </div>
        <div className="flex-1 space-y-1">
          <div className="text-xs uppercase tracking-widest font-bold">
            {tier === 4 ? "🚨 Tier 4: Autonomous Action Executed" : "🔔 Tier 3: Critical Clinician Notification"}
          </div>
          <p className="text-sm font-medium text-white/90 leading-relaxed">
            {description}
          </p>
          {tier === 4 && (
            <div className="text-[10px] bg-[#ff5050]/20 text-[#ff8080] border border-[#ff5050]/30 rounded px-2.5 py-1 w-fit mt-2 font-semibold">
              Rapid Response Team Paged · 1-Click Order Pre-populated
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
