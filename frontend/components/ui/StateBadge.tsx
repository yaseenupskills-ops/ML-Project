import React from 'react';
import { Clock, Check, X, AlertCircle, CheckCircle, XCircle, ArrowUp, CheckCircle2, AlertTriangle, WifiOff } from 'lucide-react';
import type { EventState, AlertStatus, DeviceStatus } from '@/types';

interface StateBadgeProps {
  state?: EventState;
  status?: AlertStatus;
  deviceStatus?: DeviceStatus;
  className?: string;
}

export function StateBadge({ state, status, deviceStatus, className = '' }: StateBadgeProps) {
  let config: { bg: string; Icon: React.ComponentType<{ size?: number; className?: string }>; text: string } = {
    bg: 'bg-ink-800 text-gray-400 border-ink-700',
    Icon: Info,
    text: 'UNKNOWN'
  };

  if (state) {
    const stateMap: Record<EventState, { bg: string; Icon: React.ComponentType<{ size?: number; className?: string }>; text: string }> = {
      PENDING: { bg: 'bg-rose-500/20 text-rose-400 border-rose-500/30', Icon: Clock, text: 'PENDING' },
      CONFIRMED: { bg: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', Icon: Check, text: 'CONFIRMED' },
      CANCELLED: { bg: 'bg-slate-500/20 text-slate-400 border-slate-500/30', Icon: X, text: 'CANCELLED' }
    };
    config = stateMap[state] || config;
  } else if (status) {
    const statusMap: Record<AlertStatus, { bg: string; Icon: React.ComponentType<{ size?: number; className?: string }>; text: string }> = {
      OPEN: { bg: 'bg-amber-500/20 text-amber-400 border-amber-500/30', Icon: AlertCircle, text: 'OPEN' },
      ACKNOWLEDGED: { bg: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', Icon: CheckCircle, text: 'ACKNOWLEDGED' },
      DISMISSED: { bg: 'bg-slate-500/20 text-slate-400 border-slate-500/30', Icon: XCircle, text: 'DISMISSED' },
      ESCALATED: { bg: 'bg-orange-500/20 text-orange-400 border-orange-500/30', Icon: ArrowUp, text: 'ESCALATED' }
    };
    config = statusMap[status] || config;
  } else if (deviceStatus) {
    const devMap: Record<DeviceStatus, { bg: string; Icon: React.ComponentType<{ size?: number; className?: string }>; text: string }> = {
      HEALTHY: { bg: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', Icon: CheckCircle2, text: 'HEALTHY' },
      DEGRADED: { bg: 'bg-amber-500/20 text-amber-400 border-amber-500/30', Icon: AlertTriangle, text: 'DEGRADED' },
      OFFLINE: { bg: 'bg-slate-500/20 text-slate-400 border-slate-500/30', Icon: WifiOff, text: 'OFFLINE' },
      ERROR: { bg: 'bg-rose-500/20 text-rose-400 border-rose-500/30', Icon: XCircle, text: 'ERROR' }
    };
    config = devMap[deviceStatus] || config;
  }

  const { bg, Icon, text } = config;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded-full border ${bg} ${className}`}>
      {state === 'PENDING' && <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping absolute" />}
      <Icon size={12} className={state === 'PENDING' ? 'z-10' : ''} />
      <span>{text}</span>
    </span>
  );
}

function Info(props: { size?: number; className?: string }) { return <span className={props.className}>i</span>; }