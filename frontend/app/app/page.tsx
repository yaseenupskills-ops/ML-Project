'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, Card, StatCard, Pill, EmptyState, Loading } from '../../components/ui';
import { getHealth, getMetrics, getAlerts, getVideoFeedUrl, Alert } from '../../services/api';
import { formatUptime, formatPct, statusColor, tierColor } from '../../lib/format';

export default function DashboardPage() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 5000,
  });

  const metrics = useQuery({
    queryKey: ['metrics'],
    queryFn: getMetrics,
    refetchInterval: 5000,
  });

  const alerts = useQuery({
    queryKey: ['alerts'],
    queryFn: () => getAlerts(),
    refetchInterval: 15000,
  });

  const recent: Alert[] = alerts.data?.alerts.slice(0, 6) ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Dashboard"
        description="Live fall-detection status, camera feed and recent alerts"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-1">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Live Monitor</h2>
            <Pill className={health.data?.camera ? 'text-teal-400' : 'text-red-400'}>
              {health.data?.camera ? 'ONLINE' : 'DEGRADED'}
            </Pill>
          </div>
          <div className="rounded-xl overflow-hidden border border-ink-800 bg-black aspect-video flex items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={getVideoFeedUrl()}
              alt="Live feed"
              className="w-full h-full object-contain"
            />
          </div>
          <div className="mt-3 flex items-center justify-between text-sm text-gray-400">
            <span>Camera source: file/demo</span>
            <Link href="/app/devices" className="text-cyan-500 hover:underline">
              Open feed →
            </Link>
          </div>
        </Card>

        <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-3 gap-4">
          <StatCard title="System" value={health.data?.status === 'ok' ? 'Healthy' : 'Degraded'} />
          <StatCard
            title="FPS"
            value={metrics.data?.fps != null ? metrics.data.fps.toFixed(1) : '—'}
          />
          <StatCard
            title="Uptime"
            value={metrics.data ? formatUptime(metrics.data.uptime_sec) : '—'}
          />
          <StatCard
            title="Falls / min"
            value={metrics.data?.falls_per_min != null ? metrics.data.falls_per_min.toFixed(2) : '—'}
          />
          <StatCard
            title="Alerts triggered"
            value={metrics.data?.alerts_triggered ?? '—'}
          />
          <StatCard
            title="Latest alerts"
            value={alerts.data?.total ?? '—'}
          />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">Recent Alerts</h2>
          <Link href="/app/alerts" className="text-cyan-500 text-sm hover:underline">
            View all →
          </Link>
        </div>
        {alerts.isLoading ? (
          <Loading />
        ) : recent.length === 0 ? (
          <EmptyState message="No alerts recorded yet" />
        ) : (
          <Card className="p-0 overflow-hidden">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-ink-900 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Tier</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((a) => (
                  <tr key={a.timestamp} className="border-b border-ink-800 hover:bg-ink-900/50">
                    <td className="px-4 py-3">
                      <Link href={`/app/alerts/${encodeURIComponent(a.timestamp)}`} className="hover:text-cyan-500">
                        {a.datetime ?? '—'}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{a.subject_id}</td>
                    <td className="px-4 py-3">{formatPct(a.confidence)}</td>
                    <td className="px-4 py-3">
                      <Pill className={tierColor(a.tier)}>{a.tier}</Pill>
                    </td>
                    <td className="px-4 py-3">
                      <Pill className={statusColor(a.status)}>{a.status}</Pill>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>
    </div>
  );
}