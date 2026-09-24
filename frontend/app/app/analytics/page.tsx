'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, Skeleton, ErrorState, Card, Button, Select, StatCard } from '@/components/ui';
import { 
  getAnalyticsSummary, 
  getAlertsOverTime, 
  getStateBreakdown, 
  getResponseTimeHistogram, 
  getFeedbackBreakdown,
  getModelVersionDistribution 
} from '@/services/analytics';
import { queryKeys, POLL_ANALYTICS } from '@/lib/constants';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { Activity, BarChart3, PieChart as PieIcon, Clock, ThumbsUp, RotateCw } from 'lucide-react';

export default function AnalyticsPage() {
  const [days, setDays] = useState<number>(30);

  const { data: summary, isLoading: loadingSummary, error: errorSummary, refetch } = useQuery({
    queryKey: queryKeys.analytics.summary(days),
    queryFn: () => getAnalyticsSummary({ days }),
    refetchInterval: POLL_ANALYTICS,
  });

  const { data: overTime, isLoading: loadingOverTime } = useQuery({
    queryKey: queryKeys.analytics.alertsOverTime(days),
    queryFn: () => getAlertsOverTime({ days }),
    refetchInterval: POLL_ANALYTICS,
  });

  const { data: stateBreakdown } = useQuery({
    queryKey: queryKeys.analytics.stateBreakdown(days),
    queryFn: () => getStateBreakdown({ days }),
  });

  const { data: responseHistogram } = useQuery({
    queryKey: queryKeys.analytics.responseTimeHistogram(days),
    queryFn: () => getResponseTimeHistogram({ days }),
  });

  const { data: feedbackData } = useQuery({
    queryKey: queryKeys.analytics.feedbackBreakdown(days),
    queryFn: () => getFeedbackBreakdown({ days }),
  });

  if (errorSummary) {
    return (
      <div className="flex flex-col h-full gap-4 max-w-6xl mx-auto w-full">
        <PageHeader title="Analytics" description="System trends and event metrics" />
        <ErrorState error="Failed to load analytics data" onRetry={() => refetch()} />
      </div>
    );
  }

  // Format Alerts Over Time
  const timeSeriesData = overTime?.dates.map((date, idx) => ({
    date: date.slice(5),
    High: overTime.high[idx] || 0,
    Medium: overTime.medium[idx] || 0,
    Low: overTime.low[idx] || 0,
  })) || [];

  // Format State Breakdown for Pie
  const statePieData = stateBreakdown ? [
    { name: 'Confirmed', value: stateBreakdown.confirmed, color: '#f43f5e' },
    { name: 'Cancelled (Grace)', value: stateBreakdown.cancelled, color: '#64748b' },
    { name: 'Pending Review', value: stateBreakdown.pending, color: '#f59e0b' },
  ].filter(d => d.value > 0) : [];

  // Format Response Time Histogram
  const histogramData = responseHistogram?.buckets.map((bucket, idx) => ({
    bucket,
    count: responseHistogram.counts[idx] || 0,
  })) || [];

  // Format Feedback Breakdown
  const feedbackBarData = feedbackData ? [
    { type: 'True Fall', count: feedbackData.true_fall, fill: '#10b981' },
    { type: 'False Alarm', count: feedbackData.false_positive, fill: '#f59e0b' },
    { type: 'Uncertain', count: feedbackData.uncertain, fill: '#06b6d4' },
    { type: 'System Error', count: feedbackData.system_failure, fill: '#f43f5e' },
  ] : [];

  return (
    <div className="flex flex-col h-full gap-6 max-w-7xl mx-auto w-full pb-12 animate-in fade-in duration-200">
      
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-ink-800 pb-4">
        <PageHeader 
          title="Telemetry & Analytics" 
          description="Historical trends, response efficiency, and algorithmic accuracy signals" 
        />
        <div className="flex items-center gap-2">
          <Select 
            value={String(days)} 
            onChange={(e) => setDays(Number(e.target.value))} 
            className="py-1.5 text-xs font-mono"
          >
            <option value="7">Last 7 Days</option>
            <option value="30">Last 30 Days</option>
            <option value="90">Last 90 Days</option>
          </Select>
          <Button 
            variant="secondary" 
            onClick={() => refetch()} 
            className="py-1.5 text-xs flex items-center gap-1.5"
          >
            <RotateCw size={13} />
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      {loadingSummary ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard 
            title="Total Detections" 
            value={summary?.total_events ?? 0} 
          />
          <StatCard 
            title="Confirmed Falls" 
            value={summary?.confirmed_events ?? 0} 
            className="border-rose-500/30 text-rose-400"
          />
          <StatCard 
            title="False Alarms Cancelled" 
            value={summary?.cancelled_events ?? 0} 
            className="border-emerald-500/30 text-emerald-400"
          />
          <StatCard 
            title="Median Response Time" 
            value={`${summary?.response_time_median_seconds ? summary.response_time_median_seconds.toFixed(1) : '0.0'}s`}
            className="border-cyan-500/30 text-cyan-400"
          />
        </div>
      )}

      {/* Row 1: Alerts Over Time by Tier & Event State Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Alerts Over Time */}
        <Card className="lg:col-span-2 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white flex items-center gap-2">
              <Activity size={18} className="text-cyan-400" />
              Event Volume by Severity Tier
            </h3>
            <span className="text-xs text-gray-500 font-mono">Past {days} days</span>
          </div>

          <div className="h-72 w-full">
            {timeSeriesData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={timeSeriesData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
                  <XAxis dataKey="date" stroke="#737373" fontSize={11} tickLine={false} />
                  <YAxis stroke="#737373" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#171717', borderColor: '#404040', borderRadius: '8px', color: '#fff' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '6px' }} />
                  <Bar dataKey="High" fill="#f43f5e" stackId="a" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="Medium" fill="#f59e0b" stackId="a" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="Low" fill="#06b6d4" stackId="a" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-gray-500">
                No event data recorded for this time range.
              </div>
            )}
          </div>
        </Card>

        {/* State Breakdown Pie */}
        <Card className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white flex items-center gap-2">
              <PieIcon size={18} className="text-amber-400" />
              Outcome Resolution
            </h3>
          </div>

          <div className="h-72 w-full flex flex-col items-center justify-center">
            {statePieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statePieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="45%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                  >
                    {statePieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#171717', borderColor: '#404040', borderRadius: '8px', color: '#fff' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-sm text-gray-500">No resolution data available.</div>
            )}
          </div>
        </Card>
      </div>

      {/* Row 2: Response Time Distribution & Caregiver Feedback */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Response Time Histogram */}
        <Card className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white flex items-center gap-2">
              <Clock size={18} className="text-emerald-400" />
              Caregiver Response Time Distribution
            </h3>
            <span className="text-xs text-gray-500 font-mono">Seconds to acknowledge</span>
          </div>

          <div className="h-64 w-full">
            {histogramData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={histogramData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
                  <XAxis dataKey="bucket" stroke="#737373" fontSize={11} tickLine={false} />
                  <YAxis stroke="#737373" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#171717', borderColor: '#404040', borderRadius: '8px', color: '#fff' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Bar dataKey="count" name="Acknowledged Events" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-gray-500">
                No response time data logged yet.
              </div>
            )}
          </div>
        </Card>

        {/* Feedback Breakdown */}
        <Card className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white flex items-center gap-2">
              <ThumbsUp size={18} className="text-cyan-400" />
              Caregiver Ground-Truth Feedback
            </h3>
            <span className="text-xs text-gray-500 font-mono">Model evaluation</span>
          </div>

          <div className="h-64 w-full">
            {feedbackBarData.length > 0 && feedbackBarData.some(f => f.count > 0) ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={feedbackBarData} layout="vertical" margin={{ top: 10, right: 20, left: 20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#262626" horizontal={false} />
                  <XAxis type="number" stroke="#737373" fontSize={11} tickLine={false} allowDecimals={false} />
                  <YAxis dataKey="type" type="category" stroke="#a3a3a3" fontSize={11} tickLine={false} width={85} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#171717', borderColor: '#404040', borderRadius: '8px', color: '#fff' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Bar dataKey="count" name="Submissions" radius={[0, 4, 4, 0]}>
                    {feedbackBarData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-gray-500">
                No feedback submitted yet.
              </div>
            )}
          </div>
        </Card>

      </div>

    </div>
  );
}
