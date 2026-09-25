'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, Card, Loading, EmptyState, StatCard } from '../../../components/ui';
import { getAnalyticsSubjects } from '../../../services/api';
import { formatDateLocal } from '../../../lib/format';

function TrendBars({ trend }: { trend: { date: string; count: number }[] }) {
  const max = Math.max(1, ...trend.map((t) => t.count));
  return (
    <div className="flex items-end gap-[2px] h-10">
      {trend.map((t, i) => (
        <div
          key={i}
          title={`${formatDateLocal(t.date)} — ${t.count}`}
          className="flex-1 rounded-t-sm"
          style={{
            height: `${t.count === 0 ? 6 : (t.count / max) * 100}%`,
            backgroundColor: t.count === 0 ? '#0d1425' : '#06B6D4',
          }}
        />
      ))}
    </div>
  );
}

export default function SubjectsPage() {
  const subjects = useQuery({ queryKey: ['analytics-subjects'], queryFn: getAnalyticsSubjects });

  if (subjects.isLoading) return <Loading />;

  const data = subjects.data ?? [];

  if (data.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <PageHeader title="Subjects" description="Per-subject alert rollups and 14-day trends" />
        <EmptyState message="No subject data yet" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Subjects" description="Per-subject alert rollups and 14-day trends" />

      <div className="flex flex-wrap gap-4">
        <StatCard title="Subjects" value={data.length} />
        <StatCard title="Total alerts" value={data.reduce((sum, s) => sum + s.alerts, 0)} />
        <StatCard
          title="Total high-risk"
          value={data.reduce((sum, s) => sum + s.high_risk, 0)}
        />
      </div>

      <Card className="p-0 overflow-hidden">
        <table className="w-full text-left text-sm text-gray-300">
          <thead className="bg-ink-900 text-xs uppercase text-gray-400">
            <tr>
              <th className="px-4 py-3">Subject</th>
              <th className="px-4 py-3">Alerts</th>
              <th className="px-4 py-3">High risk</th>
              <th className="px-4 py-3">Avg confidence</th>
              <th className="px-4 py-3">Escalation rate</th>
              <th className="px-4 py-3">Avg response (min)</th>
              <th className="px-4 py-3">14-day trend</th>
            </tr>
          </thead>
          <tbody>
            {data.map((sub) => (
              <tr key={sub.subject_id} className="border-b border-ink-800 hover:bg-ink-900/50">
                <td className="px-4 py-3 font-medium">{sub.subject_id}</td>
                <td className="px-4 py-3">{sub.alerts}</td>
                <td className="px-4 py-3">{sub.high_risk}</td>
                <td className="px-4 py-3">{(sub.avg_confidence * 100).toFixed(1)}%</td>
                <td className="px-4 py-3">{sub.escalation_rate_pct.toFixed(1)}%</td>
                <td className="px-4 py-3">
                  {sub.avg_response_min != null ? Math.round(sub.avg_response_min).toLocaleString() : '—'}
                </td>
                <td className="px-4 py-3 min-w-56">
                  <TrendBars trend={sub.trend} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <p className="text-sm text-gray-500">
        See the full aggregation on the{' '}
        <Link href="/app/analytics" className="text-cyan-500 hover:underline">
          Analytics page
        </Link>
        .
      </p>
    </div>
  );
}