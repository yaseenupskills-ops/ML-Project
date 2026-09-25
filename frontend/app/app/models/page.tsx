'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, Card, StatCard, Pill, Loading } from '../../../components/ui';
import { getMetrics, getHealth } from '../../../services/api';
import { formatUptime } from '../../../lib/format';

export default function ModelsPage() {
  const metricsQuery = useQuery({
    queryKey: ['metrics'],
    queryFn: getMetrics,
    refetchInterval: 5000,
  });
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 5000 });

  if (metricsQuery.isLoading) return <Loading />;

  const m = metricsQuery.data;

  const models = [
    {
      name: 'Random Forest baseline',
      status: 'Available',
      path: 'models/rf_baseline.joblib',
      description: 'Feature-based classifier trained on MediaPipe pose keypoint features.',
    },
    {
      name: 'CNN-LSTM (phase 2)',
      status: 'Available',
      path: 'models/cnn_lstm.pt',
      description: 'Sequence model over pose windows; used when the pipeline is enabled.',
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Models" description="Detection models and live inference pipeline status" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 flex flex-col gap-3">
          {models.map((model) => (
            <Card key={model.name} className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold">{model.name}</h3>
                <p className="text-sm text-gray-400 mt-1">{model.description}</p>
                <p className="text-xs text-gray-500 mt-1 font-mono">{model.path}</p>
              </div>
              <Pill className="text-teal-400">{model.status}</Pill>
            </Card>
          ))}
        </div>

        <div className="flex flex-col gap-4">
          <Card>
            <h3 className="font-semibold mb-3">Pipeline</h3>
            <div className="grid grid-cols-2 gap-3">
              <StatCard
                title="Pipeline running"
                value={m?.pipeline_running ? 'Yes' : 'No'}
              />
              <StatCard
                title="Camera status"
                value={health.data?.camera ? 'Online' : 'Offline'}
              />
              <StatCard title="Frames processed" value={m?.frames_processed ?? '—'} />
              <StatCard title="Windows evaluated" value={m?.windows_evaluated ?? '—'} />
            </div>
          </Card>
          <Card>
            <h3 className="font-semibold mb-3">Detection</h3>
            <div className="grid grid-cols-2 gap-3">
              <StatCard title="Falls / min" value={m?.falls_per_min?.toFixed(2) ?? '—'} />
              <StatCard title="Uptime" value={m ? formatUptime(m.uptime_sec) : '—'} />
              <StatCard title="Fall candidates" value={m?.fall_candidates ?? '—'} />
              <StatCard title="FP cancelled" value={m?.false_positives_cancelled ?? '—'} />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}