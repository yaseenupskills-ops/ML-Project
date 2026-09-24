'use client';

import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  PageHeader, 
  Card, 
  Badge, 
  Button, 
  StatCard, 
  Skeleton, 
  ErrorState 
} from '@/components/ui';
import { RoleGuard } from '@/components/layout/RoleGuard';
import { getDevices } from '@/services/devices';
import { getSystemHealth } from '@/services/system';
import { getNotifications, retryNotification } from '@/services/notifications';
import { useStore } from '@/lib/store';
import { queryKeys } from '@/lib/constants';
import { formatDateTimeTz, formatRelativeTime } from '@/lib/date';
import { useToast } from '@/components/ui/Toast';
import { 
  Server, 
  Database, 
  Cpu, 
  Clock, 
  BellOff, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  RotateCw,
  HardDrive,
  Activity
} from 'lucide-react';
import type { Device, Notification } from '@/types';

export default function SystemPage() {
  return (
    <RoleGuard allowedRoles={['caregiver', 'admin', 'operator']}>
      <SystemContent />
    </RoleGuard>
  );
}

function SystemContent() {
  const { user } = useStore();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const role = user?.role || 'caregiver';
  const isAdmin = role === 'admin';

  // 1. Devices fleet query
  const { data: devices, isLoading: loadingDevices, error: errorDevices, refetch: refetchDevices } = useQuery({
    queryKey: queryKeys.devices.list(),
    queryFn: getDevices,
    refetchInterval: 15000,
  });

  // 2. Backend health query
  const { data: health, isLoading: loadingHealth, error: errorHealth, refetch: refetchHealth } = useQuery({
    queryKey: queryKeys.system.health,
    queryFn: getSystemHealth,
    refetchInterval: 15000,
  });

  // 3. Failed notifications query (admin/operator only)
  const { data: failedNotifications, isLoading: loadingNotifs } = useQuery({
    queryKey: ['notifications', 'failed'],
    queryFn: () => getNotifications({ status: 'FAILED' }),
    refetchInterval: 15000,
    enabled: role === 'admin' || role === 'operator',
  });

  // Notification retry mutation
  const retryMut = useMutation({
    mutationFn: (id: string) => retryNotification(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      toast('success', 'Notification retry queued');
    },
    onError: (err: any) => {
      toast('error', err.message || 'Retry failed');
    }
  });

  const handleRefreshAll = () => {
    refetchDevices();
    refetchHealth();
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
  };

  // Fleet counts
  const healthyCount = devices?.filter(d => d.status === 'HEALTHY').length || 0;
  const degradedCount = devices?.filter(d => d.status === 'DEGRADED').length || 0;
  const offlineCount = devices?.filter(d => d.status === 'OFFLINE').length || 0;
  const errorCount = devices?.filter(d => d.status === 'ERROR').length || 0;

  return (
    <div className="flex flex-col h-full gap-6 max-w-7xl mx-auto w-full pb-12 animate-in fade-in duration-200">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-ink-800 pb-4">
        <PageHeader 
          title="System Health & Infrastructure" 
          description="Hardware status, edge device diagnostics, and communication channels" 
        />
        <Button 
          variant="secondary" 
          onClick={handleRefreshAll} 
          className="text-xs flex items-center gap-1.5"
        >
          <RotateCw size={13} />
          Refresh Diagnostics
        </Button>
      </div>

      {/* Fleet Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard 
          title="Healthy Units" 
          value={healthyCount} 
          className="border-emerald-500/30 text-emerald-400"
        />
        <StatCard 
          title="Degraded Units" 
          value={degradedCount} 
          className="border-amber-500/30 text-amber-400"
        />
        <StatCard 
          title="Offline Units" 
          value={offlineCount} 
          className="border-slate-700 text-gray-400"
        />
        <StatCard 
          title="Error State" 
          value={errorCount} 
          className="border-rose-500/30 text-rose-400"
        />
      </div>

      {/* Core Backend Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* API & Backend */}
        <Card className="flex flex-col gap-3 border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between">
            <span className="font-bold text-white flex items-center gap-2 text-sm">
              <Server size={16} className="text-emerald-400" />
              API Server
            </span>
            <Badge variant={!errorHealth ? 'success' : 'error'}>
              {!errorHealth ? 'CONNECTED' : 'OFFLINE'}
            </Badge>
          </div>
          <p className="text-xs text-gray-400">
            FastAPI edge gateway processing local inference telemetry.
          </p>
          <div className="text-[11px] text-gray-500 font-mono mt-auto pt-2 border-t border-ink-800">
            Server Time: {health?.server_time ? formatDateTimeTz(health.server_time) : 'Checking...'}
          </div>
        </Card>

        {/* Database */}
        <Card className="flex flex-col gap-3 border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between">
            <span className="font-bold text-white flex items-center gap-2 text-sm">
              <Database size={16} className="text-emerald-400" />
              Database Engine
            </span>
            <Badge variant={health?.database === 'ok' ? 'success' : 'error'}>
              {health?.database === 'ok' ? 'HEALTHY' : 'ERROR'}
            </Badge>
          </div>
          <p className="text-xs text-gray-400">
            Persistent storage for audit events, model checkpoints, and telemetry.
          </p>
          <div className="text-[11px] text-gray-500 font-mono mt-auto pt-2 border-t border-ink-800">
            Connection Pool: Normal
          </div>
        </Card>

        {/* Inference Worker */}
        <Card className="flex flex-col gap-3 border-l-4 border-l-cyan-500">
          <div className="flex items-center justify-between">
            <span className="font-bold text-white flex items-center gap-2 text-sm">
              <Cpu size={16} className="text-cyan-400" />
              Inference Worker
            </span>
            <Badge variant="info">ACTIVE</Badge>
          </div>
          <p className="text-xs text-gray-400">
            MediaPipe pose estimation & spatial feature extraction worker.
          </p>
          <div className="text-[11px] text-gray-500 font-mono mt-auto pt-2 border-t border-ink-800">
            Last Heartbeat: {health?.worker_last_tick ? formatRelativeTime(health.worker_last_tick) : 'Just now'}
          </div>
        </Card>

      </div>

      {/* Grid: Device Fleet Cards & Failed Dispatch Notifications */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        
        {/* Device Fleet Cards */}
        <Card className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-ink-800 pb-3">
            <h3 className="font-bold text-white flex items-center gap-2">
              <HardDrive size={18} className="text-cyan-400" />
              Edge Device Fleet Status
            </h3>
            <span className="text-xs text-gray-400 font-mono">{devices?.length || 0} units monitored</span>
          </div>

          <div className="space-y-3 max-h-[440px] overflow-y-auto pr-1">
            {loadingDevices ? (
              <div className="space-y-3">
                <Skeleton className="h-20 rounded-xl" />
                <Skeleton className="h-20 rounded-xl" />
              </div>
            ) : devices && devices.length > 0 ? (
              devices.map(device => {
                const isOnline = device.status === 'HEALTHY' || device.status === 'DEGRADED';
                const statusVariant = device.status === 'HEALTHY' ? 'success' : device.status === 'DEGRADED' ? 'warning' : 'error';

                return (
                  <div key={device.id} className="bg-ink-950 p-3.5 rounded-xl border border-ink-800 flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-white text-sm">{device.name}</div>
                        <div className="text-xs text-gray-400">
                          {device.location || 'Unassigned'} • Firmware {device.software_version || 'v1.0.0'}
                        </div>
                      </div>
                      <Badge variant={statusVariant}>
                        {device.status}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs pt-2 border-t border-ink-800/80 text-gray-400">
                      <div>
                        <span className="text-[10px] text-gray-500 block">Model Version</span>
                        <span className="text-gray-200 font-mono text-[11px]">{device.model_version || 'RF-v1.0'}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-gray-500 block">Last Ping</span>
                        <span className="text-gray-200 text-[11px]">{device.last_seen ? formatRelativeTime(device.last_seen) : 'Never'}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-gray-500 block">Edge Storage</span>
                        <span className="text-emerald-400 text-[11px]">RAM only (0B video)</span>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-sm text-gray-500 py-8 text-center">No edge devices registered yet.</p>
            )}
          </div>
        </Card>

        {/* Failed Notifications Log (Admin / Operator) */}
        {(role === 'admin' || role === 'operator') && (
          <Card className="flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-ink-800 pb-3">
              <h3 className="font-bold text-white flex items-center gap-2">
                <BellOff size={18} className="text-rose-400" />
                Dispatch Failure Log
              </h3>
              <Badge variant={failedNotifications && failedNotifications.length > 0 ? 'error' : 'default'}>
                {failedNotifications?.length || 0} Undelivered
              </Badge>
            </div>

            <div className="space-y-3 max-h-[440px] overflow-y-auto pr-1">
              {failedNotifications && failedNotifications.length > 0 ? (
                failedNotifications.map(n => (
                  <div key={n.id} className="bg-ink-950 p-3.5 rounded-xl border border-rose-900/30 flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-white text-sm">
                          {n.channel} Alert Notification
                        </div>
                        <div className="text-xs text-rose-400/90 font-mono mt-0.5">
                          Error Code: {n.error_code || 'SMTP_DISPATCH_TIMEOUT'}
                        </div>
                      </div>
                      {isAdmin && (
                        <Button 
                          variant="secondary" 
                          className="text-xs py-1 px-3"
                          onClick={() => retryMut.mutate(n.id)}
                          disabled={retryMut.isPending}
                        >
                          Retry Dispatch
                        </Button>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-ink-800/80">
                      <span>Delivery Attempts: {n.attempts}</span>
                      <span>{n.last_attempt_at ? formatDateTimeTz(n.last_attempt_at) : 'Recent'}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-16 text-center text-gray-500 text-sm flex flex-col items-center gap-2">
                  <CheckCircle2 size={36} className="text-emerald-500/70" />
                  <span>All emergency notification dispatches delivered successfully.</span>
                </div>
              )}
            </div>
          </Card>
        )}

      </div>

    </div>
  );
}
