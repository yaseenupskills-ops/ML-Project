import React from 'react';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import type { EventTier } from '@/types';

export function TierPill({ tier, className = '' }: { tier: EventTier; className?: string }) {
  const config = {
    HIGH: { bg: 'bg-rose-500/20 text-rose-400 border-rose-500/30', Icon: AlertTriangle },
    MEDIUM: { bg: 'bg-amber-500/20 text-amber-400 border-amber-500/30', Icon: AlertCircle },
    LOW: { bg: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30', Icon: Info }
  };
  
  const { bg, Icon } = config[tier] || config.LOW;
  
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded-full border ${bg} ${className}`}>
      <Icon size={12} />
      {tier}
    </span>
  );
}