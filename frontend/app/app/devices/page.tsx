'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PageHeader,
  Card,
  Button,
  Pill,
  Loading,
  EmptyState,
  StatCard,
} from '../../../components/ui';
import {
  getMetrics,
  getRecordings,
  startRecording,
  stopRecording,
  getVideoFeedUrl,
  getRecordingVideoUrl,
} from '../../../services/api';
import { formatDt, formatUptime, formatMb } from '../../../lib/format';

export default function DevicesPage() {
  const queryClient = useQueryClient();
  const [activeRecording, setActiveRecording] = useState<string | null>(null);

  const metricsQuery = useQuery({
    queryKey: ['metrics'],
    queryFn: getMetrics,
    refetchInterval: 5000,
  });

  const recordingsQuery = useQuery({
    queryKey: ['recordings'],
    queryFn: getRecordings,
    refetchInterval: 10000,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['recordings'] });
    queryClient.invalidateQueries({ queryKey: ['metrics'] });
  };

  const record = useMutation({
    mutationFn: () => (metricsQuery.data?.recording_active ? stopRecording() : startRecording()),
    onSuccess: invalidate,
  });

  const recording = metricsQuery.data?.recording_active;
  const recordings = recordingsQuery.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Devices" description="Camera monitoring and opt-in recording" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Live Feed</h2>
            <div className="flex items-center gap-2">
              <Pill className={recording ? 'text-red-400' : 'text-teal-400'}>
                {recording ? '● RECORDING' : 'CAMERA ONLINE'}
              </Pill>
            </div>
          </div>
          <div className="rounded-xl overflow-hidden border border-ink-800 bg-black aspect-video flex items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={getVideoFeedUrl()} alt="Live camera feed" className="w-full h-full object-contain" />
          </div>
        </Card>

        <div className="flex flex-col gap-4">
          <Card>
            <h3 className="font-semibold mb-3">Recording</h3>
            <p className="text-sm text-gray-400 mb-4">
              {recording
                ? 'A recording segment is being written to disk. Stop to finalize the current segment.'
                : 'Recording is off by default (privacy-first). Start to capture segments to disk.'}
            </p>
            <Button
              variant={recording ? 'secondary' : 'primary'}
              disabled={record.isPending}
              onClick={() => record.mutate()}
            >
              {record.isPending ? '…' : recording ? 'Stop recording' : 'Start recording'}
            </Button>
          </Card>
          <Card>
            <h3 className="font-semibold mb-3">Camera</h3>
            <div className="grid grid-cols-2 gap-3">
              <StatCard title="FPS" value={metricsQuery.data?.fps?.toFixed(1) ?? '—'} />
              <StatCard title="Uptime" value={metricsQuery.data ? formatUptime(metricsQuery.data.uptime_sec) : '—'} />
              <StatCard title="Frame age" value={metricsQuery.data?.last_frame_age_sec?.toFixed(1) ?? '—'} />
              <StatCard title="Segments" value={metricsQuery.data?.recorded_segments ?? '—'} />
            </div>
          </Card>
        </div>
      </div>

      <div>
        <h2 className="font-semibold mb-3">Recordings</h2>
        {recordingsQuery.isLoading ? (
          <Loading />
        ) : recordings.length === 0 ? (
          <EmptyState message="No recordings on this device yet" />
        ) : (
          <div className="flex flex-col gap-3">
            {recordings
              .slice()
              .sort((a, b) => b.created - a.created)
              .map((r) => (
                <Card key={r.name} className="p-0 overflow-hidden">
                  <button
                    className="w-full flex flex-wrap items-center gap-4 px-4 py-3 text-left hover:bg-ink-900/50"
                    onClick={() => setActiveRecording(activeRecording === r.name ? null : r.name)}
                  >
                    <span className="text-cyan-500 flex-1 min-w-40 break-all">{r.name}</span>
                    <span className="text-sm text-gray-400">{formatMb(r.size_mb)}</span>
                    <span className="text-sm text-gray-400">{formatDt(r.created)}</span>
                    <Pill className="text-gray-300">{r.alerts.length} alerts</Pill>
                    <span className="text-xs text-gray-500">
                      {activeRecording === r.name ? 'hide ▲' : 'play ▶'}
                    </span>
                  </button>
                  {activeRecording === r.name && (
                    <div className="px-4 pb-4">
                      <video
                        src={getRecordingVideoUrl(r.name)}
                        controls
                        className="w-full max-h-72 rounded-xl bg-black border border-ink-800"
                      />
                      <div className="mt-3 flex flex-wrap gap-2">
                        {r.alerts.map((al) => (
                          <Pill key={al.timestamp} className="text-xs">
                            {al.offset_sec.toFixed(1)}s · {al.subject_id} · {al.tier} ·{' '}
                            {(al.confidence * 100).toFixed(0)}%
                          </Pill>
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}