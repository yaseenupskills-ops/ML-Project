'use client';

import React, { use } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader, Card, Button, Pill, EmptyState, Loading } from '../../../../components/ui';
import { getAlerts, patchAlert, AlertAction } from '../../../../services/api';
import { formatPct, formatDt, statusColor, tierColor } from '../../../../lib/format';

export default function AlertDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const queryClient = useQueryClient();
  const timestamp = Number(id);

  const alertsQuery = useQuery({
    queryKey: ['alerts'],
    queryFn: () => getAlerts(),
    enabled: !isNaN(timestamp),
  });

  const alert = alertsQuery.data?.alerts.find((a) => a.timestamp === timestamp);

  const patchMutation = useMutation({
    mutationFn: (action: AlertAction) => patchAlert(timestamp, action),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }),
  });

  if (alertsQuery.isLoading) return <Loading />;

  if (!alert) {
    return (
      <div className="flex flex-col gap-4">
        <PageHeader title="Alert Details" />
        <EmptyState message={isNaN(timestamp) ? 'Invalid alert id' : 'Alert not found'} />
        <Link href="/app/alerts" className="text-cyan-500 hover:underline">
          ← Back to alerts
        </Link>
      </div>
    );
  }

  const rows: { label: string; value: React.ReactNode }[] = [
    { label: 'Timestamp', value: alert.datetime ?? formatDt(alert.timestamp) },
    { label: 'Subject ID', value: alert.subject_id },
    { label: 'Clip ID', value: alert.clip_id },
    { label: 'Confidence', value: formatPct(alert.confidence) },
    {
      label: 'Tier',
      value: <Pill className={tierColor(alert.tier)}>{alert.tier}</Pill>,
    },
    { label: 'Outcome', value: alert.outcome },
    { label: 'Grace period response', value: alert.response_time != null ? `${alert.response_time}s` : '—' },
    {
      label: 'Status',
      value: <Pill className={statusColor(alert.status)}>{alert.status}</Pill>,
    },
    { label: 'Acknowledged by', value: alert.acknowledged_by ?? '—' },
    { label: 'Acknowledged at', value: alert.acknowledged_at != null ? formatDt(alert.acknowledged_at) : '—' },
    { label: 'Video clip', value: alert.video_clip_path || '—' },
  ];

  return (
    <div className="flex flex-col gap-4 max-w-3xl">
      <div>
        <Link href="/app/alerts" className="text-cyan-500 text-sm hover:underline">
          ← Back to alerts
        </Link>
        <PageHeader title="Alert Details" description={`Alert ${alert.timestamp}`} />
      </div>

      <Card>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
          {rows.map((r) => (
            <div key={r.label} className="flex flex-col gap-1">
              <dt className="text-xs uppercase text-gray-400">{r.label}</dt>
              <dd className="text-sm text-white break-words">{r.value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-gray-300">Actions</span>
        <Button
          disabled={alert.status === 'acknowledged' || patchMutation.isPending}
          onClick={() => patchMutation.mutate('acknowledge')}
        >
          Acknowledge
        </Button>
        <Button
          variant="secondary"
          disabled={alert.status === 'dismissed' || patchMutation.isPending}
          onClick={() => patchMutation.mutate('dismiss')}
        >
          Dismiss
        </Button>
        <Button
          variant="secondary"
          disabled={patchMutation.isPending}
          onClick={() => patchMutation.mutate('escalate')}
        >
          Escalate
        </Button>
        <span className="text-xs text-gray-500">
          Escalation re-sends an urgent email notification.
        </span>
      </Card>
    </div>
  );
}