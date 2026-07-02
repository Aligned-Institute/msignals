'use client';

import Link from 'next/link';
import { DEMO_PATIENTS } from '@/lib/mock-data';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Users, Clock, AlertTriangle, ShieldCheck, Zap } from 'lucide-react';

export default function PatientCensus() {
  const getAdmittedDuration = (admittedAt: string) => {
    const diffMs = Date.now() - new Date(admittedAt).getTime();
    const diffHours = Math.floor(diffMs / 3600000);
    const days = Math.floor(diffHours / 24);
    const hours = diffHours % 24;
    return `${days}d ${hours}h`;
  };

  const getTierBadge = (tier: number) => {
    switch (tier) {
      case 4:
        return (
          <Badge className="bg-[#ff5050] text-white border-none glow-red font-mono px-3 py-1 flex items-center gap-1.5 animate-pulse">
            <Zap className="size-3.5 fill-current" />
            <span>T4: Autonomous Alert</span>
          </Badge>
        );
      case 3:
        return (
          <Badge className="bg-[#ffd000] text-black border-none glow-yellow font-mono px-3 py-1 flex items-center gap-1.5">
            <AlertTriangle className="size-3.5 fill-current" />
            <span>T3: Clinical Notify</span>
          </Badge>
        );
      case 2:
        return (
          <Badge className="bg-[#00f3ff]/20 text-[#00f3ff] border border-[#00f3ff]/30 font-mono px-3 py-1 flex items-center gap-1.5">
            <AlertTriangle className="size-3.5" />
            <span>T2: Advisory</span>
          </Badge>
        );
      default:
        return (
          <Badge className="bg-zinc-800 text-zinc-400 border border-zinc-700 font-mono px-3 py-1 flex items-center gap-1.5">
            <ShieldCheck className="size-3.5" />
            <span>T1: Suppressed</span>
          </Badge>
        );
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 animate-page-in">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent font-sans">
            ICU Patient Census
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time multi-agent clinical coordination and divergence status for MICU beds.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground bg-secondary/30 px-3 py-1.5 rounded-lg border border-border">
          <Users className="size-3.5 text-[#00ff9d]" />
          <span>Active Units: 2/2 Beds Occupied</span>
        </div>
      </div>

      {/* Patient Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {DEMO_PATIENTS.map((patient) => {
          const state = patient.aligned_state;
          const duration = getAdmittedDuration(patient.admitted_at);
          
          return (
            <Card key={patient.id} className="bg-card hover-lift overflow-hidden border border-border">
              {/* Card Header Banner */}
              <div className="bg-[#050b14]/60 px-6 py-4 flex items-center justify-between border-b border-border">
                <div className="font-mono text-[#00f3ff] text-xs font-semibold tracking-wider">
                  {patient.bed} · {patient.unit}
                </div>
                {getTierBadge(state.highest_action_tier)}
              </div>

              <CardContent className="p-6 space-y-6">
                {/* Details */}
                <div>
                  <h2 className="text-xl font-bold tracking-tight text-white">{patient.name}</h2>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground mt-1.5">
                    <span>{patient.age} y/o {patient.sex === 'M' ? 'Male' : 'Female'}</span>
                    <span className="text-zinc-700">|</span>
                    <span className="flex items-center gap-1">
                      <Clock className="size-3" />
                      Admitted: {duration}
                    </span>
                  </div>
                </div>

                {/* Clinical Context */}
                <div className="space-y-2">
                  <div className="text-[10px] uppercase font-mono tracking-widest text-zinc-500">Diagnosis</div>
                  <p className="text-sm text-zinc-300 font-medium">
                    {patient.primary_diagnosis}
                  </p>
                </div>

                {/* Telemetry Summary */}
                <div className="grid grid-cols-2 gap-4 border-t border-border pt-4 text-xs font-mono">
                  <div>
                    <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1">State Confidence</div>
                    <span className="text-[#00ff9d] font-bold text-sm">
                      {Math.round(state.aggregate_confidence * 100)}%
                    </span>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1">Active Conflicts</div>
                    <span className={state.conflicts.length > 0 ? "text-[#ffd000] font-bold text-sm" : "text-zinc-500 text-sm"}>
                      {state.conflicts.length}
                    </span>
                  </div>
                </div>

                {/* Link */}
                <div className="pt-2">
                  <Link href={`/patient/${patient.id}`} className="w-full block">
                    <Button variant="secondary" className="w-full text-xs font-semibold py-2">
                      Open Alignment Telemetry
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
