'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { useQuery, useMutation } from '@tanstack/react-query';
import { PageHeader, Card, StatCard, Button, Loading, EmptyState } from '../../../components/ui';
import {
  getAnalyticsSummary,
  getAnalyticsSubjects,
  getAnalyticsResponseTimes,
  downloadAnalyticsCsv,
} from '../../../services/api';
import { formatNumber } from '../../../lib/format';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function Heatmap({ heatmap }: { heatmap: number[][] }) {
  const max = Math.max(1, ...heatmap.flat());
  return (
    <div className="grid grid-rows-7 gap-1">
      {heatmap.map((row, i) => (
        <div key={i} className="grid grid-cols-[2rem_1fr] items-center gap-1">
          <span className="text-[10px] text-gray-500">{DAYS[i]}</span>
          <div className="grid grid-cols-24 gap-[2px]">
            {Array.from({ length: 24 }).map((_, h) => {
              const count = row[h] ?? 0;
              const intensity = count === 0 ? 0.08 : 0.3 + (count / max) * 0.7;
              return (
                <div
                  key={h}
                  title={`${DAYS[i]} ${h}:00 — ${count}`}
                  className="h-3 rounded-sm"
                  style={{ backgroundColor: `rgba(6,182,212,${intensity})` }}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const summary = useQuery({ queryKey: ['analytics-summary'], queryFn: getAnalyticsSummary });
  const subjects = useQuery({ queryKey: ['analytics-subjects'], queryFn: getAnalyticsSubjects });
  const responseTimes = useQuery({
    queryKey: ['analytics-response-times'],
    queryFn: getAnalyticsResponseTimes,
  });

  const exportMutation = useMutation({
    mutationFn: downloadAnalyticsCsv,
  });

  const s = summary.data;
  const rt = responseTimes.data;

  if (summary.isLoading) return <Loading />;

  const statusStats = s
    ? [
        { title: 'Pending', value: s.pending, color: 'text-amber-400' },
        { title: 'Acknowledged', value: s.acknowledged, color: 'text-teal-400' },
        { title: 'Escalated', value: s.escalated, color: 'text-red-400' },
        { title: 'Dismissed', value: s.dismissed, color: 'text-gray-400' },
      ]
    : [];

  const tierData = Object.entries(s?.by_tier ?? {}).map(([tier, count]) => ({
    name: tier,
    count,
  }));

  const histData = (s?.confidence_histogram ?? []).map((h) => ({
    name: h.range_pct,
    count: h.count,
  }));

  const funnelData = (s?.escalation_funnel.stages ?? []).map((st) => ({
    name: st.stage,
    count: st.count,
  }));

  const rtHistData = (rt?.histogram ?? []).slice(0, 20).map((h) => ({
    name: h.range_min,
    count: h.count,
  }));

return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Analytics" description="Aggregate alert statistics, trends and response performance" />

      <div className="flex flex-wrap gap-4">
        {s && (
          <div className="flex flex-wrap gap-4 flex-1">
            <StatCard title="Total alerts" value={s.total} />
            <StatCard title="High risk (conf ≥ 0.85)" value={s.high_risk} />
            <StatCard title="Avg confidence" value={`${(s.avg_confidence * 100).toFixed(1)}%`} />
            <StatCard title="This week" value={s.week_over_week.this_week} />
            <StatCard
              title="WoW change"
              value={`${s.week_over_week.pct_change >= 0 ? '+' : ''}${s.week_over_week.pct_change.toFixed(1)}%`}
            />
            <StatCard title="Daily avg (7d)" value={s.week_over_week.daily_avg.toFixed(2)} />
          </div>
        )}
        {exportMutation.isError && (
          <p className="text-red-400 text-sm">Export failed — please try again.</p>
        )}
        <Button
          variant="secondary"
          disabled={exportMutation.isPending}
          onClick={() => exportMutation.mutate()}
        >
          {exportMutation.isPending ? 'Exporting…' : 'Export CSV'}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <h3 className="font-semibold mb-3">By Status</h3>
          <div className="grid grid-cols-2 gap-3">
            {statusStats.map((st) => (
              <div key={st.title} className="flex flex-col gap-1">
                <span className="text-sm text-gray-400">{st.title}</span>
                <span className={`text-2xl font-bold ${st.color}`}>{st.value}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={funnelData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#0d1425" />
                <XAxis dataKey="name" stroke="#6b7280" fontSize={12} />
                <YAxis stroke="#6b7280" fontSize={12} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#040c1d', border: '1px solid #050c1e', borderRadius: 12 }}
                />
                <Bar dataKey="count" fill="#06B6D4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Ack rate {s?.escalation_funnel.acknowledged_rate_pct.toFixed(0)}% · Escalation rate{' '}
            {s?.escalation_funnel.escalated_rate_pct.toFixed(0)}% (of pending)
          </p>
        </Card>

        <Card>
          <h3 className="font-semibold mb-3">Alerts by Tier</h3>
          {tierData.length === 0 ? (
            <EmptyState message="No data" />
          ) : (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={tierData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#0d1425" />
                  <XAxis dataKey="name" stroke="#6b7280" fontSize={12} />
                  <YAxis stroke="#6b7280" fontSize={12} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#040c1d', border: '1px solid #050c1e', borderRadius: 12 }}
                  />
                  <Bar dataKey="count" fill="#14B8A6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card>
          <h3 className="font-semibold mb-3">Weekly Heatmap</h3>
          {s?.heatmap?.length ? (
            <Heatmap heatmap={s.heatmap} />
          ) : (
            <EmptyState message="No data" />
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <h3 className="font-semibold mb-3">Confidence Histogram</h3>
          {histData.length === 0 ? (
            <EmptyState message="No data" />
          ) : (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={histData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#0d1425" />
                  <XAxis dataKey="name" stroke="#6b7280" fontSize={10} interval={1} />
                  <YAxis stroke="#6b7280" fontSize={12} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#040c1d', border: '1px solid #050c1e', borderRadius: 12 }}
                  />
                  <Bar dataKey="count" fill="#06B6D4" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card>
          <h3 className="font-semibold mb-3">Response Time (to acknowledge, minutes)</h3>
          {rt ? (
            <>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <StatCard title="Mean" value={rt.mean_min != null ? formatNumber(Math.round(rt.mean_min)) : '—'} />
                <StatCard title="Median" value={rt.median_min != null ? formatNumber(Math.round(rt.median_min)) : '—'} />
                <StatCard title="P95" value={rt.p95_min != null ? formatNumber(Math.round(rt.p95_min)) : '—'} />
              </div>
              {rt.n_actioned === 0 ? (
                <EmptyState message="No acknowledged alerts yet" />
              ) : (
                <div className="h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={rtHistData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#0d1425" />
                      <XAxis dataKey="name" stroke="#6b7280" fontSize={9} interval={1} />
                      <YAxis stroke="#6b7280" fontSize={12} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#040c1d', border: '1px solid #050c1e', borderRadius: 12 }}
                      />
                      <Bar dataKey="count" fill="#14B8A6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          ) : (
            <Loading />
          )}
        </Card>
      </div>

      <Card>
        <h3 className="font-semibold mb-3">Subjects</h3>
        {subjects.isLoading ? (
          <Loading />
        ) : (subjects.data ?? []).length === 0 ? (
          <EmptyState message="No subject data" />
        ) : (
          <div className="w-full overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-ink-900 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3">Alerts</th>
                  <th className="px-4 py-3">High risk</th>
                  <th className="px-4 py-3">Escalation rate</th>
                  <th className="px-4 py-3">Avg confidence</th>
                  <th className="px-4 py-3">Avg response (min)</th>
                </tr>
              </thead>
              <tbody>
                {(subjects.data ?? []).map((sub) => (
                  <tr key={sub.subject_id} className="border-b border-ink-800 hover:bg-ink-900/50">
                    <td className="px-4 py-3">{sub.subject_id}</td>
                    <td className="px-4 py-3">{sub.alerts}</td>
                    <td className="px-4 py-3">{sub.high_risk}</td>
                    <td className="px-4 py-3">{sub.escalation_rate_pct.toFixed(1)}%</td>
                    <td className="px-4 py-3">{(sub.avg_confidence * 100).toFixed(1)}%</td>
                    <td className="px-4 py-3">
                      {sub.avg_response_min != null ? Math.round(sub.avg_response_min).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}