'use client';

import React, { useEffect, useRef } from 'react';
import { useCountdown } from '@/lib/hooks';
import { formatCountdown } from '@/lib/date';

interface CountdownProps {
  deadline?: string;
  serverTimeOffsetMs?: number;
  onExpired?: () => void;
}

export function Countdown({ deadline, serverTimeOffsetMs = 0, onExpired }: CountdownProps) {
  const remaining = useCountdown(deadline, serverTimeOffsetMs);
  const wasNotified = useRef(false);

  useEffect(() => {
    if (remaining === 0 && deadline && !wasNotified.current) {
      wasNotified.current = true;
      onExpired?.();
    }
    if (remaining > 0) {
      wasNotified.current = false;
    }
  }, [remaining, deadline, onExpired]);

  if (!deadline || remaining <= 0) return null;

  const isUrgent = remaining <= 10;

  return (
    <div className={`font-mono font-bold flex items-center gap-2 ${isUrgent ? 'text-rose-500' : 'text-white'}`}>
      {isUrgent && <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping absolute" />}
      {isUrgent && <span className="w-2 h-2 rounded-full bg-rose-500" />}
      <span>{formatCountdown(remaining)}</span>
    </div>
  );
}