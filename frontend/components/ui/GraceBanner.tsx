import React from 'react';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { Clock } from 'lucide-react';
import { Button } from './index';
import { Countdown } from './Countdown';
import { cancelEvent } from '@/services/events';
import { queryKeys } from '@/lib/constants';
import { useStore } from '@/lib/store';
import type { FallEvent } from '@/types';

interface GraceBannerProps {
  event: FallEvent;
}

export function GraceBanner({ event }: GraceBannerProps) {
  const queryClient = useQueryClient();
  const { serverTimeOffset, user } = useStore();
  const canCancel = user?.role === 'caregiver' || user?.role === 'admin';

  const cancelMut = useMutation({
    mutationFn: () => cancelEvent(event.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.events.all });
    }
  });

  if (event.state === 'PENDING') {
    return (
      <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 flex flex-col sm:flex-row items-center justify-between gap-4 w-full mb-4 animate-in slide-in-from-top-2">
        <div className="flex items-center gap-3 text-rose-400">
          <div className="relative flex items-center justify-center">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping absolute" />
            <Clock size={16} className="text-rose-500 relative z-10" />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="font-bold">Possible Fall</span>
            <span className="text-rose-500/50">•</span>
            <span className="font-medium text-white">{event.subject_display_name || 'Unknown Subject'}</span>
            <span className="text-rose-500/50 hidden sm:inline">•</span>
            <span className="text-gray-300 hidden sm:inline">{event.device_name || 'Unknown Device'}</span>
          </div>
        </div>

        <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
          <Countdown deadline={event.grace_deadline} serverTimeOffsetMs={serverTimeOffset} />
          {canCancel && (
            <Button 
              variant="secondary" 
              className="bg-rose-950/50 hover:bg-rose-900 border-rose-900/50 text-rose-400 px-3 py-1.5 text-xs whitespace-nowrap"
              onClick={() => cancelMut.mutate()}
              disabled={cancelMut.isPending}
            >
              {cancelMut.isPending ? 'Cancelling...' : 'Cancel event'}
            </Button>
          )}
        </div>
      </div>
    );
  }

  // Brief outcome banner for 10s (controlled by parent unmounting usually)
  const isConfirmed = event.state === 'CONFIRMED' || event.grace_outcome === 'confirmed';
  return (
    <div className={`border rounded-xl p-3 flex items-center gap-3 w-full mb-4 animate-in slide-in-from-top-2 fade-in ${
      isConfirmed ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-slate-500/10 border-slate-500/30 text-slate-400'
    }`}>
      <span className="text-sm font-medium">
        {isConfirmed ? 'Event confirmed. Alert escalated.' : 'Event cancelled.'}
      </span>
    </div>
  );
}
