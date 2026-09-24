import React from 'react';
import { AlertTriangle, RotateCw } from 'lucide-react';

interface StaleBannerProps {
  isStale?: boolean;
  lastUpdatedLabel?: string;
  onRetry?: () => void;
}

export function StaleBanner({ isStale = true, lastUpdatedLabel, onRetry }: StaleBannerProps) {
  if (!isStale) return null;
  
  return (
    <div className="bg-amber-500/20 border border-amber-500/30 text-amber-400 px-4 py-2.5 rounded-xl flex items-center justify-between text-sm w-full animate-in fade-in">
      <div className="flex items-center gap-2">
        <AlertTriangle size={16} />
        <span className="font-medium">Connection problem. Data may be out of date.</span>
      </div>
      <div className="flex items-center gap-3">
        {lastUpdatedLabel && <span className="opacity-80 text-xs font-mono">{lastUpdatedLabel}</span>}
        {onRetry && (
          <button 
            onClick={onRetry}
            className="flex items-center gap-1 text-xs font-medium underline hover:text-amber-300 transition-colors"
          >
            <RotateCw size={12} />
            Retry
          </button>
        )}
      </div>
    </div>
  );
}