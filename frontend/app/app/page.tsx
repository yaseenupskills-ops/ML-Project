'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  PageHeader, 
  StatCard, 
  Card, 
  Badge, 
  Button, 
  GraceBanner, 
  LiveStatusStrip, 
  StaleBanner, 
  TierPill, 
  StateBadge,
  Skeleton
} from '@/components/ui';
import { getAnalyticsSummary, getAlertsOverTime, getModelVersionDistribution } from '@/services/analytics';
import { getEvents } from '@/services/events';
import { getDevices } from '@/services/devices';
import { getNotifications, retryNotification } from '@/services/notifications';
import { getSystemHealth } from '@/services/system';
import { acknowledgeAlert } from '@/services/alerts';
import { useStore } from '@/lib/store';
import { formatDateTimeTz, formatRelativeTime } from '@/lib/date';
import { formatSubjectName } from '@/lib/subject-display';
import { queryKeys, POLL_ALERTS_LIST, POLL_EVENT_PENDING, POLL_DASHBOARD } from '@/lib/constants';
import { useToast } from '@/components/ui/Toast';
import { 
  AlertTriangle, 
  ShieldCheck, 
  Activity, 
  Clock, 
  Cpu, 
  Server, 
  Eye, 
  BellOff, 
  RotateCw, 
  ExternalLink,
  CheckCircle2,
  XCircle,
  Radio
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend 
} from 'recharts';
import type { FallEvent, Device, Notification } from '@/types';

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useStore();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const role = user?.role || 'caregiver';
  const isMlEngineer = role === 'ml_engineer';

  // 1. Pending grace events (highest urgency, polled frequently)
  const { data: pendingEvents, isError: pendingError } = useQuery({
    queryKey: ['events', 'pending_grace'],
    queryFn: () => getEvents({ state: 'PENDING', page_size: 10 }),
    refetchInterval: POLL_EVENT_PENDING,
  });

  // 2. Summary analytics
  const { 
    data: summary, 
    isLoading: loadingSummary, 
    isError: summaryError, 
    failureCount: summaryFailures 
  } = useQuery({
    queryKey: queryKeys.analytics.summary(30),
    queryFn: () => getAnalyticsSummary({ days: 30 }),
    refetchInterval: POLL_DASHBOARD,
  });

  // 3. Needs Attention Events (OPEN alerts or PENDING confirmation)
  const { 
    data: openEventsData, 
    isLoading: loadingOpenEvents,
    isError: openEventsError 
  } = useQuery({
    queryKey: ['events', 'needs_attention'],
    queryFn: () => getEvents({ alert_status: 'OPEN', page_size: 10 }),
    refetchInterval: POLL_ALERTS_LIST,
    enabled: role !== 'ml_engineer',
  });

  // 4. Recent Events (Timeline)
  const { 
    data: recentEventsData, 
    isLoading: loadingRecentEvents 
  } = useQuery({
    queryKey: ['events', 'recent_activity'],
    queryFn: () => getEvents({ page_size: 8 }),
    refetchInterval: POLL_ALERTS_LIST,
  });

  // 5. Devices for fleet health
  const { 
    data: devices, 
    isLoading: loadingDevices, 
    isError: devicesError 
  } = useQuery({
    queryKey: queryKeys.devices.list(),
    queryFn: () => getDevices(),
    refetchInterval: 15000,
  });

  // 6. System health
  const { 
    data: systemHealth, 
    isError: systemError 
  } = useQuery({
    queryKey: queryKeys.system.health,
    queryFn: () => getSystemHealth(),
    refetchInterval: 15000,
  });

  // 7. Failed notifications for operator/admin
  const { data: failedNotifications } = useQuery({
    queryKey: ['notifications', 'failed'],
    queryFn: () => getNotifications({ status: 'FAILED' }),
    refetchInterval: 15000,
    enabled: role === 'admin' || role === 'operator',
  });

  // 8. Alerts Over Time for admin
  const { data: alertsOverTime } = useQuery({
    queryKey: queryKeys.analytics.alertsOverTime(14),
    queryFn: () => getAlertsOverTime({ days: 14 }),
    enabled: role === 'admin',
  });

  // 9. Model Version Distribution for ML Engineer
  const { data: modelDist } = useQuery({
    queryKey: queryKeys.analytics.modelVersionDistribution(),
    queryFn: () => getModelVersionDistribution(),
    enabled: isMlEngineer,
  });

  // Acknowledge quick action mutation
  const ackMutation = useMutation({
    mutationFn: (alertId: string) => acknowledgeAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.events.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.analytics.summary() });
      toast('success', 'Alert acknowledged');
    },
    onError: (err: any) => {
      toast('error', err.message || 'Failed to acknowledge alert');
    }
  });

  // Notification retry mutation
  const retryMutation = useMutation({
    mutationFn: (id: string) => retryNotification(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      toast('success', 'Notification retry queued');
    }
  });

  // Aggregated live status
  const hasDeviceError = devices?.some(d => d.status === 'ERROR' || d.status === 'OFFLINE');
  const cameraStatus: 'ok' | 'error' = (devices && devices.length > 0 && !hasDeviceError) ? 'ok' : (devices?.length === 0 ? 'ok' : 'error');
  const modelStatus: 'ok' | 'error' = systemHealth?.database === 'ok' ? 'ok' : 'error';
  const backendStatus: 'ok' | 'error' = (!systemError && !summaryError) ? 'ok' : 'error';
  const isStale = summaryFailures >= 2 || (summaryError && devicesError);

  // Chart data formatting for admin
  const chartData = alertsOverTime?.dates.map((date, idx) => ({
    date: date.slice(5), // MM-DD
    High: alertsOverTime.high[idx] || 0,
    Medium: alertsOverTime.medium[idx] || 0,
    Low: alertsOverTime.low[idx] || 0,
  })) || [];

  // Model distribution formatting for ML Engineer
  const modelChartData = modelDist?.versions.map((ver, idx) => ({
    version: ver,
    devices: modelDist.device_counts[idx] || 0,
  })) || [];

  const pendingList = pendingEvents?.items || [];
  const needsAttentionList = openEventsData?.items || [];
  const recentList = recentEventsData?.items || [];

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full pb-12 animate-in fade-in duration-200">
      
      {/* 1. Global Live Status Ribbon */}
      <LiveStatusStrip 
        cameraStatus={cameraStatus}
        modelStatus={modelStatus}
        backendStatus={backendStatus}
      />

      {/* Stale Connection Banner */}
      {isStale && <StaleBanner onRetry={() => queryClient.invalidateQueries()} />}

      {/* 2. Critical Grace-Period Emergency Banner */}
      {pendingList.length > 0 && (
        <div className="flex flex-col gap-2">
          {pendingList.map(event => (
            <GraceBanner key={event.id} event={event} />
          ))}
        </div>
      )}

      {/* Header section with Role Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-ink-800 pb-4">
        <div>
          <PageHeader 
            title={`Welcome back, ${user?.name || 'User'}`}
            description="Real-time privacy-preserving fall detection & telemetry overview"
          />
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="info" className="capitalize px-3 py-1 font-mono text-xs">
            Role: {role.replace('_', ' ')}
          </Badge>
          <Button 
            variant="secondary" 
            className="flex items-center gap-2 text-xs py-1.5 px-3"
            onClick={() => queryClient.invalidateQueries()}
          >
            <RotateCw size={13} />
            Refresh
          </Button>
        </div>
      </div>

      {/* 3. Role-Adaptive KPI StatCards */}
      {loadingSummary ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {/* Caregiver KPIs */}
          {role === 'caregiver' && (
            <>
              <StatCard 
                title="Open Alerts" 
                value={summary?.open_alerts ?? 0} 
                className="border-warning/30 bg-gradient-to-br from-ink-900 to-amber-950/20 text-amber-400"
              />
              <StatCard 
                title="Escalated Alerts" 
                value={summary?.escalated_alerts ?? 0} 
                className="border-rose-500/30 bg-gradient-to-br from-ink-900 to-rose-950/20 text-rose-400"
              />
              <StatCard 
                title="Confirmed Today" 
                value={summary?.confirmed_events ?? 0} 
                className="border-emerald-500/30 text-emerald-400"
              />
              <StatCard 
                title="Avg Response Time" 
                value={`${summary?.response_time_avg_seconds ? summary.response_time_avg_seconds.toFixed(1) : '0.0'}s`}
              />
            </>
          )}

          {/* Admin KPIs */}
          {role === 'admin' && (
            <>
              <StatCard 
                title="Active Devices" 
                value={summary?.active_devices ?? devices?.filter(d => d.status === 'HEALTHY').length ?? 0} 
                className="border-emerald-500/30 text-emerald-400"
              />
              <StatCard 
                title="Offline Devices" 
                value={summary?.offline_devices ?? devices?.filter(d => d.status === 'OFFLINE' || d.status === 'ERROR').length ?? 0} 
                className="border-rose-500/30 text-rose-400"
              />
              <StatCard 
                title="Total Events (30d)" 
                value={summary?.total_events ?? 0} 
              />
              <StatCard 
                title="Confirmed Falls" 
                value={summary?.confirmed_events ?? 0} 
                className="border-warning/30 text-amber-300"
              />
              <StatCard 
                title="False Positives" 
                value={summary?.false_positive_feedback ?? 0} 
              />
              <StatCard 
                title="Failed Alerts (Email/SMS)" 
                value={summary?.notification_failures ?? failedNotifications?.length ?? 0} 
                className="border-rose-500/30 text-rose-400"
              />
            </>
          )}

          {/* Operator KPIs */}
          {role === 'operator' && (
            <>
              <StatCard 
                title="Healthy Devices" 
                value={devices?.filter(d => d.status === 'HEALTHY').length ?? 0} 
                className="border-emerald-500/30 text-emerald-400"
              />
              <StatCard 
                title="Degraded / Warning" 
                value={devices?.filter(d => d.status === 'DEGRADED').length ?? 0} 
                className="border-warning/30 text-amber-400"
              />
              <StatCard 
                title="Offline Devices" 
                value={devices?.filter(d => d.status === 'OFFLINE' || d.status === 'ERROR').length ?? 0} 
                className="border-rose-500/30 text-rose-400"
              />
              <StatCard 
                title="Failed Notifications" 
                value={failedNotifications?.length ?? 0} 
                className="border-rose-500/30 text-rose-400"
              />
            </>
          )}

          {/* ML Engineer KPIs (Masked & aggregate) */}
          {isMlEngineer && (
            <>
              <StatCard 
                title="Total Evaluated Events" 
                value={summary?.total_events ?? 0} 
              />
              <StatCard 
                title="Confirmed Falls" 
                value={summary?.confirmed_events ?? 0} 
                className="border-emerald-500/30 text-emerald-400"
              />
              <StatCard 
                title="False Positive Feedback" 
                value={summary?.false_positive_feedback ?? 0} 
                className="border-amber-500/30 text-amber-400"
              />
              <StatCard 
                title="Uncertain Feedback" 
                value={summary?.uncertain_feedback ?? 0} 
                className="border-cyan-500/30 text-cyan-400"
              />
            </>
          )}
        </div>
      )}

      {/* 4. Admin Chart: Alerts Over Time */}
      {role === 'admin' && chartData.length > 0 && (
        <Card className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white flex items-center gap-2">
              <Activity size={18} className="text-cyan-400" />
              Alerts Over Time (By Severity Tier)
            </h3>
            <span className="text-xs text-gray-400">Past 14 days</span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
                <XAxis dataKey="date" stroke="#737373" fontSize={11} tickLine={false} />
                <YAxis stroke="#737373" fontSize={11} tickLine={false} allowDecimals={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#171717', borderColor: '#404040', borderRadius: '8px', color: '#fff' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
                <Bar dataKey="High" fill="#f43f5e" stackId="a" radius={[0, 0, 0, 0]} />
                <Bar dataKey="Medium" fill="#f59e0b" stackId="a" radius={[0, 0, 0, 0]} />
                <Bar dataKey="Low" fill="#06b6d4" stackId="a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* 5. ML Engineer: Model Distribution Chart */}
      {isMlEngineer && modelChartData.length > 0 && (
        <Card className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white flex items-center gap-2">
              <Cpu size={18} className="text-cyan-400" />
              Active Model Version Distribution
            </h3>
            <Button 
              variant="secondary" 
              className="text-xs py-1"
              onClick={() => router.push('/app/models')}
            >
              View Model Registry →
            </Button>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
                <XAxis dataKey="version" stroke="#737373" fontSize={11} tickLine={false} />
                <YAxis stroke="#737373" fontSize={11} tickLine={false} allowDecimals={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#171717', borderColor: '#404040', borderRadius: '8px', color: '#fff' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Bar dataKey="devices" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* 6. Operator View: Fleet Health Matrix & Notification Issues */}
      {role === 'operator' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Non-healthy devices */}
          <Card className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-white flex items-center gap-2">
                <Server size={18} className="text-amber-400" />
                Fleet Disruption & Health Warnings
              </h3>
              <Button 
                variant="secondary" 
                className="text-xs py-1"
                onClick={() => router.push('/app/devices')}
              >
                All Devices
              </Button>
            </div>
            
            <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
              {devices && devices.filter(d => d.status !== 'HEALTHY').length > 0 ? (
                devices.filter(d => d.status !== 'HEALTHY').map(d => (
                  <div key={d.id} className="bg-ink-950 p-3 rounded-xl border border-ink-800 flex items-center justify-between">
                    <div>
                      <div className="font-medium text-white text-sm">{d.name}</div>
                      <div className="text-xs text-gray-400">{d.location || 'Location unassigned'} • Last seen {d.last_seen ? formatRelativeTime(d.last_seen) : 'Never'}</div>
                    </div>
                    <Badge variant={d.status === 'DEGRADED' ? 'warning' : 'error'}>
                      {d.status}
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-gray-500 text-sm flex flex-col items-center gap-2">
                  <CheckCircle2 className="text-emerald-500" size={32} />
                  <span>All devices in the fleet are operating normally.</span>
                </div>
              )}
            </div>
          </Card>

          {/* Failed notification attempts */}
          <Card className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-white flex items-center gap-2">
                <BellOff size={18} className="text-rose-400" />
                Failed Dispatch Notifications
              </h3>
              <Badge variant="error">{failedNotifications?.length || 0} Failed</Badge>
            </div>

            <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
              {failedNotifications && failedNotifications.length > 0 ? (
                failedNotifications.map(n => (
                  <div key={n.id} className="bg-ink-950 p-3 rounded-xl border border-rose-950/40 flex items-center justify-between">
                    <div>
                      <div className="font-medium text-sm text-gray-200">
                        {n.channel} {n.kind} Dispatch
                      </div>
                      <div className="text-xs text-rose-400/90 font-mono mt-0.5">
                        Attempts: {n.attempts} • Error: {n.error_code || 'Timeout'}
                      </div>
                    </div>
                    <Button 
                      variant="secondary" 
                      className="text-xs py-1 px-2.5"
                      onClick={() => retryMutation.mutate(n.id)}
                      disabled={retryMutation.isPending}
                    >
                      Retry
                    </Button>
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-gray-500 text-sm flex flex-col items-center gap-2">
                  <CheckCircle2 className="text-emerald-500" size={32} />
                  <span>No notification delivery failures.</span>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* 7. Main Working Split: Needs Attention Feed & Recent Timeline */}
      {role !== 'operator' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          
          {/* Needs Attention Column */}
          <Card className="flex flex-col gap-4 border-warning/20 min-h-[460px]">
            <div className="flex items-center justify-between border-b border-ink-800 pb-3">
              <h3 className="font-bold text-white flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-400"></span>
                </span>
                Needs Immediate Attention
              </h3>
              <Badge variant={needsAttentionList.length > 0 ? 'warning' : 'default'}>
                {needsAttentionList.length} Unresolved
              </Badge>
            </div>

            <div className="flex-1 overflow-y-auto pr-1 space-y-3 max-h-[420px]">
              {loadingOpenEvents ? (
                <div className="space-y-3">
                  <Skeleton className="h-24 rounded-xl" />
                  <Skeleton className="h-24 rounded-xl" />
                </div>
              ) : needsAttentionList.length > 0 ? (
                needsAttentionList.map(event => {
                  const subjectTitle = formatSubjectName(event.subject_display_name, event.subject_id, isMlEngineer);
                  const isAckable = event.alert && event.alert.status === 'OPEN';

                  return (
                    <div 
                      key={event.id} 
                      className="bg-ink-950 p-4 rounded-xl border border-ink-800 hover:border-amber-500/40 transition-colors flex flex-col gap-3"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-semibold text-white text-base flex items-center gap-2">
                            {subjectTitle}
                            <TierPill tier={event.tier} />
                          </div>
                          <div className="text-xs text-gray-400 mt-1 flex items-center gap-2">
                            <span>{event.device_name || 'Camera 1'}</span>
                            <span>•</span>
                            <span>{formatRelativeTime(event.created_at)}</span>
                          </div>
                        </div>

                        {/* Model score tooltip warning */}
                        <div className="text-right">
                          <div className="text-xs font-mono font-bold text-gray-300">
                            Model score: {Math.round((event.confidence || 0) * 100)}%
                          </div>
                          <span className="text-[10px] text-gray-500">Uncalibrated score</span>
                        </div>
                      </div>

                      {/* Evidence summary if present */}
                      {event.evidence_summary && (
                        <p className="text-xs text-gray-300 bg-ink-900/60 p-2 rounded-lg border border-ink-800/80">
                          {event.evidence_summary}
                        </p>
                      )}

                      <div className="flex gap-2 pt-1 border-t border-ink-800/60">
                        {isAckable && (
                          <Button 
                            variant="primary" 
                            className="flex-1 text-xs py-1.5"
                            onClick={() => ackMutation.mutate(event.alert!.id)}
                            disabled={ackMutation.isPending}
                          >
                            Acknowledge
                          </Button>
                        )}
                        <Button 
                          variant="secondary" 
                          className="flex-1 text-xs py-1.5 flex items-center justify-center gap-1.5"
                          onClick={() => router.push(`/app/alerts/${event.id}`)}
                        >
                          <Eye size={13} />
                          Inspect Evidence
                        </Button>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-gray-500 gap-2">
                  <CheckCircle2 size={36} className="text-emerald-500/60" />
                  <p className="text-sm font-medium text-gray-400">All alerts are acknowledged and clear.</p>
                  <span className="text-xs text-gray-600">The system is actively monitoring feeds.</span>
                </div>
              )}
            </div>
          </Card>

          {/* Recent Activity Timeline Column */}
          <Card className="flex flex-col gap-4 min-h-[460px]">
            <div className="flex items-center justify-between border-b border-ink-800 pb-3">
              <h3 className="font-bold text-white flex items-center gap-2">
                <Clock size={16} className="text-cyan-400" />
                Audit Trail & Activity
              </h3>
              <Button 
                variant="secondary" 
                className="text-xs py-1"
                onClick={() => router.push('/app/alerts')}
              >
                View Full Log →
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 relative max-h-[420px]">
              <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-ink-800"></div>

              <div className="space-y-4 relative">
                {loadingRecentEvents ? (
                  <div className="space-y-3 pl-8">
                    <Skeleton className="h-16 rounded-xl" />
                    <Skeleton className="h-16 rounded-xl" />
                  </div>
                ) : recentList.length > 0 ? (
                  recentList.map((event) => {
                    const subjectTitle = formatSubjectName(event.subject_display_name, event.subject_id, isMlEngineer);
                    const isConfirmed = event.state === 'CONFIRMED';
                    const isCancelled = event.state === 'CANCELLED';

                    return (
                      <div key={event.id} className="relative pl-8 group">
                        {/* Timeline status dot */}
                        <div className={`absolute left-[8px] top-2 w-2.5 h-2.5 rounded-full ring-4 ring-ink-900 ${
                          isConfirmed ? 'bg-rose-500' : isCancelled ? 'bg-slate-500' : 'bg-amber-400'
                        }`} />

                        <div className="bg-ink-950 p-3 rounded-xl border border-ink-800 hover:border-ink-700 transition-colors">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-semibold text-white">
                              {subjectTitle}
                            </span>
                            <span className="text-[11px] text-gray-400 font-mono">
                              {formatDateTimeTz(event.created_at)}
                            </span>
                          </div>

                          <div className="flex items-center justify-between mt-2 pt-2 border-t border-ink-900 text-xs">
                            <div className="flex items-center gap-2">
                              <StateBadge state={event.state} />
                              <TierPill tier={event.tier} />
                            </div>
                            <span className="text-gray-400 text-[11px]">
                              {event.device_name || 'Edge unit'}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-sm text-gray-500 pl-8">No recent activity detected.</p>
                )}
              </div>
            </div>
          </Card>

        </div>
      )}

    </div>
  );
}
