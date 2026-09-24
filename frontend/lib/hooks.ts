'use client';

import { useEffect, useRef, useState } from 'react';
import { STALE_FAILURE_THRESHOLD } from './constants';

export function useStaleTracking(failureCount: number, dataUpdatedAt: number) {
  const isStale = failureCount >= STALE_FAILURE_THRESHOLD;
  const [lastUpdatedLabel, setLastUpdatedLabel] = useState('');
  
  useEffect(() => {
    if (!dataUpdatedAt) return;
    const interval = setInterval(() => {
      const diffS = Math.floor((Date.now() - dataUpdatedAt) / 1000);
      if (diffS < 60) setLastUpdatedLabel(`Updated ${diffS} s ago`);
      else if (diffS < 3600) setLastUpdatedLabel(`Updated ${Math.floor(diffS / 60)} min ago`);
      else setLastUpdatedLabel(`Updated ${Math.floor(diffS / 3600)} h ago`);
    }, 1000);
    return () => clearInterval(interval);
  }, [dataUpdatedAt]);
  
  return { isStale, lastUpdatedLabel };
}

export function usePageVisibility(): boolean {
  const [isVisible, setIsVisible] = useState(true);
  useEffect(() => {
    const handler = () => setIsVisible(document.visibilityState === 'visible');
    document.addEventListener('visibilitychange', handler);
    return () => document.removeEventListener('visibilitychange', handler);
  }, []);
  return isVisible;
}

export function useCountdown(deadline: string | undefined, serverTimeOffsetMs: number = 0): number {
  const [remaining, setRemaining] = useState(0);
  useEffect(() => {
    if (!deadline) { setRemaining(0); return; }
    const update = () => {
      const serverNow = Date.now() + serverTimeOffsetMs;
      const deadlineMs = new Date(deadline).getTime();
      const diff = Math.max(0, Math.floor((deadlineMs - serverNow) / 1000));
      setRemaining(diff);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [deadline, serverTimeOffsetMs]);
  return remaining;
}

export function useFocusTrap<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const previousFocus = useRef<Element | null>(null);
  
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    previousFocus.current = document.activeElement;
    const focusableSelector = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const focusable = el.querySelectorAll(focusableSelector);
      if (focusable.length === 0) return;
      const first = focusable[0] as HTMLElement;
      const last = focusable[focusable.length - 1] as HTMLElement;
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    
    el.addEventListener('keydown', handleKeyDown);
    const firstFocusable = el.querySelector(focusableSelector) as HTMLElement | null;
    firstFocusable?.focus();
    
    return () => {
      el.removeEventListener('keydown', handleKeyDown);
      (previousFocus.current as HTMLElement)?.focus?.();
    };
  }, []);
  return ref;
}