'use client';

import { use, useState } from 'react';
import Link from 'next/link';
import useSWR from 'swr';
import { Patient } from '@/lib/types';
import { NurseView } from '@/components/patient/NurseView';
import { DoctorView } from '@/components/patient/DoctorView';
import { AgentGraph } from '@/components/patient/AgentGraph';
import { Button } from '@/components/ui/button';
import { Clock, Activity, FileSpreadsheet, Eye, ChevronLeft, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

const fetcher = (url: string) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch patient data');
  return res.json();
});

export default function PatientDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  
  // Tab state: 'nurse' | 'doctor'
  const [activeTab, setActiveTab] = useState<'nurse' | 'doctor'>('nurse');

  // Continuous polling every 5 seconds using SWR
  const { data: patient, error, isLoading } = useSWR<Patient>(
    `/api/msignals/patient/${id}`,
    fetcher,
    { refreshInterval: 5000 }
  );

  const getAdmittedDuration = (admittedAt: string) => {
    const diffMs = Date.now() - new Date(admittedAt).getTime();
    const diffHours = Math.floor(diffMs / 3600000);
    const days = Math.floor(diffHours / 24);
    const hours = diffHours % 24;
    return `${days}d ${hours}h`;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-background text-foreground font-mono space-y-4">
        <Activity className="size-8 text-[#00f3ff] animate-pulse" />
        <div className="text-xs uppercase tracking-widest text-zinc-500 animate-pulse">
          Aligning Multi-Agent State Logs...
        </div>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-background text-foreground font-mono space-y-4">
        <ShieldCheck className="size-8 text-[#ff5050]" />
        <div className="text-sm font-semibold text-zinc-400">
          Patient alignment log not found.
        </div>
        <Link href="/">
          <Button variant="secondary" className="text-xs">
            Return to Census
          </Button>
        </Link>
      </div>
    );
  }

  const state = patient.aligned_state;
  const admittedTime = getAdmittedDuration(patient.admitted_at);

  return (
    <div className="p-8 space-y-6 max-w-[1600px] mx-auto animate-page-in">
      {/* Back Link */}
      <div className="flex items-center justify-between">
        <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-white transition-colors font-mono">
          <ChevronLeft className="size-4" />
          <span>Back to Patient Census</span>
        </Link>
        <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-mono">
          <span>State Hash:</span>
          <span className="text-[#00f3ff] font-semibold">{state.state_hash}</span>
        </div>
      </div>

      {/* Patient Meta Header Bar */}
      <div className="bg-card border border-border rounded-lg p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 select-none">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs font-bold text-[#00f3ff] uppercase tracking-wider px-2 py-0.5 bg-[#00f3ff]/10 border border-[#00f3ff]/20 rounded">
              {patient.bed} · {patient.unit}
            </span>
            <h2 className="text-2xl font-bold tracking-tight text-white font-sans">
              {patient.name}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>{patient.age} y/o {patient.sex === 'M' ? 'Male' : 'Female'}</span>
            <span className="text-zinc-700">|</span>
            <span>Diagnosis: <strong className="text-zinc-350">{patient.primary_diagnosis}</strong></span>
            <span className="text-zinc-700">|</span>
            <span className="inline-flex items-center gap-1.5 font-mono text-[11px]">
              <Clock className="size-3.5 text-zinc-500" />
              Admitted: {admittedTime}
            </span>
          </div>
        </div>

        {/* Tab Toggle Switch (Clinician Scope) */}
        <div className="bg-[#050b14]/80 border border-border p-1 rounded-lg flex items-center shrink-0 w-fit">
          <button
            onClick={() => setActiveTab('nurse')}
            className={cn(
              "px-4 py-1.5 rounded-md text-xs font-semibold tracking-wide transition-all",
              activeTab === 'nurse'
                ? "bg-secondary text-[#00f3ff] shadow border border-border/80"
                : "text-muted-foreground hover:text-white"
            )}
          >
            Nurse View
          </button>
          <button
            onClick={() => setActiveTab('doctor')}
            className={cn(
              "px-4 py-1.5 rounded-md text-xs font-semibold tracking-wide transition-all",
              activeTab === 'doctor'
                ? "bg-secondary text-[#00f3ff] shadow border border-border/80"
                : "text-muted-foreground hover:text-white"
            )}
          >
            Doctor View (Telemetry)
          </button>
        </div>
      </div>

      {/* Side-by-Side Main Grid (Interactive Tabs on Left, Node Graph on Right) */}
      <div className="grid lg:grid-cols-10 gap-6">
        {/* Left 7 Columns: Action View tabs */}
        <div className="lg:col-span-7">
          {activeTab === 'nurse' ? (
            <NurseView patient={patient} />
          ) : (
            <DoctorView patient={patient} />
          )}
        </div>

        {/* Right 3 Columns: Aligned Flow Graph (React Flow canvas) */}
        <div className="lg:col-span-3">
          <div className="sticky top-6 space-y-3 select-none">
            <div className="text-xs font-mono uppercase tracking-widest text-zinc-500 font-bold px-1 flex items-center gap-1.5">
              <Activity className="size-3.5" />
              <span>Alignment Topology Flow</span>
            </div>
            <AgentGraph state={state} />
          </div>
        </div>
      </div>
    </div>
  );
}
