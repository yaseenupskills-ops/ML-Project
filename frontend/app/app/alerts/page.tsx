'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PageHeader,
  Card,
  Button,
  Select,
  Input,
  Pill,
  EmptyState,
  Loading,
} from '../../../components/ui';
import {
  getAlerts,
  patchAlert,
  bulkAlertAction,
  Alert,
  AlertAction,
  AlertTier,
  AlertStatus,
} from '../../../services/api';
import { formatPct, statusColor, tierColor } from '../../../lib/format';

const ACTIONS: { label: string; action: AlertAction }[] = [
  { label: 'Acknowledge', action: 'acknowledge' },
  { label: 'Dismiss', action: 'dismiss' },
  { label: 'Escalate', action: 'escalate' },
];

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [tier, setTier] = useState('');
  const [status, setStatus] = useState('');
  const [subject, setSubject] = useState('');
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const alertsQuery = useQuery({
    queryKey: ['alerts', { tier, status, subject }],
    queryFn: () =>
      getAlerts({
        tier: (tier || undefined) as AlertTier | undefined,
        status: (status || undefined) as AlertStatus | undefined,
        subject_id: subject || undefined,
      }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['alerts'] });

  const patchMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: AlertAction }) => patchAlert(id, action),
    onSuccess: () => {
      setSelected(new Set());
      invalidate();
    },
  });

  const bulkMutation = useMutation({
    mutationFn: ({ ids, action }: { ids: number[]; action: AlertAction }) =>
      bulkAlertAction(ids, action),
    onSuccess: () => {
      setSelected(new Set());
      invalidate();
    },
  });

  const alerts = alertsQuery.data?.alerts ?? [];
  const busy = patchMutation.isPending || bulkMutation.isPending;
  const pendingCount = alerts.filter((a) => a.status === 'pending').length;

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    setSelected((prev) =>
      prev.size === alerts.length ? new Set() : new Set(alerts.map((a) => a.timestamp))
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Alerts" description="Review, acknowledge, dismiss or escalate fall alerts" />

      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs uppercase text-gray-400">Tier</label>
            <Select value={tier} onChange={(e) => setTier(e.target.value)}>
              <option value="">All</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs uppercase text-gray-400">Status</label>
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="dismissed">Dismissed</option>
              <option value="escalated">Escalated</option>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs uppercase text-gray-400">Subject</label>
            <Input
              placeholder="e.g. S1"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-40"
            />
          </div>
          <Button
            variant="secondary"
            onClick={() => {
              setTier('');
              setStatus('');
              setSubject('');
            }}
          >
            Reset
          </Button>
          <span className="ml-auto text-sm text-gray-400">
            {alertsQuery.data?.total ?? 0} alerts · {pendingCount} pending
          </span>
        </div>
      </Card>

      {selected.size > 0 && (
        <Card className="flex items-center gap-3">
          <span className="text-sm text-gray-300">{selected.size} selected</span>
          {ACTIONS.map((a) => (
            <Button
              key={a.action}
              variant="secondary"
              disabled={busy}
              onClick={() => bulkMutation.mutate({ ids: [...selected], action: a.action })}
            >
              {a.label} all
            </Button>
          ))}
          <Button variant="secondary" onClick={() => setSelected(new Set())}>
            Clear
          </Button>
        </Card>
      )}

      {alertsQuery.isLoading ? (
        <Loading />
      ) : alerts.length === 0 ? (
        <EmptyState message="No alerts match the current filters" />
      ) : (
        <Card className="p-0 overflow-hidden">
          <table className="w-full text-left text-sm text-gray-300">
            <thead className="bg-ink-900 text-xs uppercase text-gray-400">
              <tr>
                <th className="px-4 py-3 w-10">
                  <input type="checkbox" checked={selected.size === alerts.length && alerts.length > 0} onChange={toggleAll} />
                </th>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Subject</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3">Tier</th>
                <th className="px-4 py-3">Outcome</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a: Alert) => (
                <tr key={a.timestamp} className="border-b border-ink-800 hover:bg-ink-900/50">
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selected.has(a.timestamp)}
                      onChange={() => toggle(a.timestamp)}
                    />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <Link
                      href={`/app/alerts/${encodeURIComponent(a.timestamp)}`}
                      className="hover:text-cyan-500"
                    >
                      {a.datetime ?? '—'}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{a.subject_id}</td>
                  <td className="px-4 py-3">{formatPct(a.confidence)}</td>
                  <td className="px-4 py-3">
                    <Pill className={tierColor(a.tier)}>{a.tier}</Pill>
                  </td>
                  <td className="px-4 py-3">{a.outcome}</td>
                  <td className="px-4 py-3">
                    <Pill className={statusColor(a.status)}>{a.status}</Pill>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      {ACTIONS.filter(
                        (x) =>
                          !(x.action === 'acknowledge' && a.status === 'acknowledged') &&
                          !(x.action === 'dismiss' && a.status === 'dismissed')
                      ).map((x) => (
                        <Button
                          key={x.action}
                          variant="secondary"
                          className="px-2 py-1 text-xs"
                          disabled={busy}
                          onClick={() => patchMutation.mutate({ id: a.timestamp, action: x.action })}
                        >
                          {x.label}
                        </Button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}