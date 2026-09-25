'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, Card, StatCard, Pill, Loading } from '../../../components/ui';
import { getHealth, getMetrics, getMe } from '../../../services/api';
import { formatDt, formatUptime } from '../../../lib/format';

export default function SystemPage() {
  const [showRaw, setShowRaw] = useState(false);

  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 5000 });
  const metricsQuery = useQuery({
    queryKey: ['metrics'],
    queryFn: getMetrics,
    refetchInterval: 5000,
  });
  const me = useQuery({ queryKey: ['me'], queryFn: getMe });

  if (metricsQuery.isLoading) return <Loading />;

  const m = metricsQuery.data;

  const details: { label: string; value: React.ReactNode }[] = [
    { label: 'Started at', value: m ? formatDt(m.started_at) : '—' },
    { label: 'Last update', value: m ? formatDt(m.last_update) : '—' },
    { label: 'Last frame', value: m ? formatDt(m.last_frame_ts) : '—' },
    { label: 'Frame age (sec)', value: m?.last_frame_age_sec?.toFixed(2) ?? '—' },
    { label: 'Capture latency (ms)', value: m?.capture_latency_ms?.toFixed(2) ?? '—' },
    { label: 'Pipeline latency (ms)', value: m?.pipeline_latency_ms?.toFixed(2) ?? '—' },
    { label: 'Frames processed', value: m?.frames_processed ?? '—' },
    { label: 'Windows evaluated', value: m?.windows_evaluated ?? '—' },
    { label: 'Alerts triggered', value: m?.alerts_triggered ?? '—' },
    { label: 'Fall candidates', value: m?.fall_candidates ?? '—' },
    { label: 'False positives cancelled', value: m?.false_positives_cancelled ?? '—' },
    { label: 'Recorded segments', value: m?.recorded_segments ?? '—' },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="System" description="Runtime health, live metrics and session" />

      <div className="flex flex-wrap gap-4">
        <StatCard
          title="Status"
          value={health.data?.status === 'ok' ? 'Healthy' : 'Degraded'}
        />
        <StatCard title="Camera" value={health.data?.camera ? 'Connected' : 'Offline'} />
        <StatCard title="FPS" value={m?.fps?.toFixed(1) ?? '—'} />
        <StatCard title="Uptime" value={m ? formatUptime(m.uptime_sec) : '—'} />
        <StatCard title="Falls / min" value={m?.falls_per_min?.toFixed(2) ?? '—'} />
        <StatCard
          title="Pipeline"
          value={m?.pipeline_running ? 'Running' : 'Idle'}
        />
        <StatCard title="Recording" value={m?.recording_active ? 'Active' : 'Off'} />
        <StatCard title="User" value={me.data?.username ?? '—'} />
        <Pill className="self-center">{me.data?.role ?? '—'}</Pill>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Metrics detail</h3>
          <button
            onClick={() => setShowRaw((v) => !v)}
            className="text-xs text-cyan-500 hover:underline"
          >
            {showRaw ? 'Hide raw JSON' : 'Show raw JSON'}
          </button>
        </div>
        {showRaw ? (
          <pre className="text-xs text-gray-300 bg-ink-900 rounded-xl p-4 overflow-x-auto font-mono">
            {JSON.stringify(m, null, 2)}
          </pre>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-3">
            {details.map((d) => (
              <div key={d.label} className="flex justify-between gap-3">
                <span className="text-sm text-gray-400">{d.label}</span>
                <span className="text-sm text-white text-right">{d.value}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}