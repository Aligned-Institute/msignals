'use client';

import { Patient } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import { Activity, Thermometer, Wind, FlaskConical } from 'lucide-react';

interface PatientTimelineProps {
  patient: Patient;
}

export function PatientTimeline({ patient }: PatientTimelineProps) {
  // Generate time series labels based on admitted_at / evaluation time
  const getTimelineData = () => {
    const isChen = patient.id === 'demo-002';
    
    if (isChen) {
      // Chen, D. — Respiratory Failure profile
      return [
        { time: '-6h', hr: 95, spo2: 92, lactate: 1.1, wbc: 8.5 },
        { time: '-5h', hr: 98, spo2: 91, lactate: 1.2, wbc: 8.4 },
        { time: '-4h', hr: 102, spo2: 90, lactate: 1.1, wbc: 8.5 },
        { time: '-3h', hr: 108, spo2: 89, lactate: 1.1, wbc: 8.6 },
        { time: '-2h', hr: 112, spo2: 88, lactate: 1.1, wbc: 8.5 },
        { time: '-1h', hr: 115, spo2: 86, lactate: 1.1, wbc: 8.5 },
        { time: 'now', hr: 118, spo2: 84, lactate: 1.1, wbc: 8.5 }
      ];
    } else {
      // Johnson, M. — Sepsis profile (VAS stable, Lactate rising)
      return [
        { time: '-6h', hr: 98, spo2: 96, lactate: 1.8, wbc: 12.0 },
        { time: '-5h', hr: 100, spo2: 95, lactate: 1.9, wbc: 12.4 },
        { time: '-4h', hr: 102, spo2: 96, lactate: 2.0, wbc: 12.8 },
        { time: '-3h', hr: 105, spo2: 95, lactate: 2.1, wbc: 13.1 },
        { time: '-2h', hr: 104, spo2: 96, lactate: 2.2, wbc: 13.5 },
        { time: '-1h', hr: 103, spo2: 95, lactate: 2.3, wbc: 13.9 },
        { time: 'now', hr: 102, spo2: 95, lactate: 2.4, wbc: 14.2 }
      ];
    }
  };

  const data = getTimelineData();

  const chartConfigs = [
    {
      title: 'Heart Rate (bpm)',
      dataKey: 'hr',
      color: '#00ff9d',
      icon: Activity,
      domain: [80, 130]
    },
    {
      title: 'Oxygen Saturation (SpO2 %)',
      dataKey: 'spo2',
      color: '#00f3ff',
      icon: Wind,
      domain: [80, 100]
    },
    {
      title: 'Lactate (mmol/L)',
      dataKey: 'lactate',
      color: '#ffd000',
      icon: FlaskConical,
      domain: [0.5, 3.0]
    },
    {
      title: 'WBC Count (x10³/µL)',
      dataKey: 'wbc',
      color: '#bd00ff',
      icon: FlaskConical,
      domain: [8, 16]
    }
  ];

  return (
    <div className="space-y-4">
      <div className="text-xs font-mono uppercase tracking-widest text-zinc-500 font-bold px-1">
        Clinical Trends (Last 6 Hours)
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {chartConfigs.map((chart) => {
          const Icon = chart.icon;
          return (
            <Card key={chart.dataKey} className="bg-card border-border select-none">
              <CardHeader className="p-4 border-b border-border/40 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-xs font-semibold text-zinc-300 font-mono">
                  {chart.title}
                </CardTitle>
                <Icon className="size-3.5 text-zinc-500" />
              </CardHeader>
              <CardContent className="p-2 pt-4">
                <div className="h-28 w-full font-mono text-[9px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data} margin={{ top: 5, right: 10, left: -25, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis
                        dataKey="time"
                        stroke="#7a8fa8"
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="#7a8fa8"
                        domain={chart.domain}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: '#0a1628',
                          border: '1px solid rgba(255,255,255,0.1)',
                          borderRadius: '4px',
                          color: '#fff',
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey={chart.dataKey}
                        stroke={chart.color}
                        strokeWidth={2}
                        dot={{ r: 2, fill: chart.color }}
                        activeDot={{ r: 4 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
