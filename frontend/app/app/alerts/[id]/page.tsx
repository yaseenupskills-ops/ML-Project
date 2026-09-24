'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader, Card, Button, TierPill, StateBadge, EvidenceList, Timeline, ConfirmDialog, Select, Input } from '@/components/ui';
import { RoleGuard } from '@/components/layout/RoleGuard';
import { getEvent, cancelEvent } from '@/services/events';
import { acknowledgeAlert, dismissAlert, escalateAlert } from '@/services/alerts';
import { submitFeedback } from '@/services/feedback';
import { formatDateTimeTz } from '@/lib/date';
import { queryKeys, POLL_EVENT_PENDING, POLL_EVENT_DEFAULT } from '@/lib/constants';
import { useToast } from '@/components/ui/Toast';
import { useStore } from '@/lib/store';
import { formatSubjectName } from '@/lib/subject-display';
import { Clock, Info } from 'lucide-react';
import type { FeedbackType } from '@/types';

export default function EventDetailPage() {
  return (
    <RoleGuard allowedRoles={['caregiver', 'admin']}>
      <EventDetailContent />
    </RoleGuard>
  );
}

function EventDetailContent() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const user = useStore(state => state.user);

  const [confirmAction, setConfirmAction] = useState<'dismiss' | 'escalate' | null>(null);

  const { data: event, isLoading, error } = useQuery({
    queryKey: queryKeys.events.detail(id),
    queryFn: () => getEvent(id),
    refetchInterval: (q) => (q.state.data?.state === 'PENDING' ? POLL_EVENT_PENDING : POLL_EVENT_DEFAULT),
  });

  const actMut = useMutation({
    mutationFn: async ({ action, note }: { action: 'ack' | 'dismiss' | 'escalate' | 'cancel', note?: string }) => {
      if (action === 'cancel') {
        await cancelEvent(id);
        return;
      }
      if (!event?.alert?.id) throw new Error('No alert ID');
      if (action === 'ack') {
        await acknowledgeAlert(event.alert.id);
        return;
      }
      if (action === 'dismiss') {
        await dismissAlert(event.alert.id, note);
        return;
      }
      await escalateAlert(event.alert.id, note);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.events.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.events.all });
      toast('success', 'Action recorded');
      setConfirmAction(null);
    }
  });

  const feedbackMut = useMutation({
    mutationFn: (data: { feedback_type: FeedbackType, comment?: string }) => submitFeedback({ event_id: id, ...data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.events.detail(id) });
      toast('success', 'Feedback submitted');
    }
  });

  const handleFeedbackSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    feedbackMut.mutate({
      feedback_type: formData.get('type') as FeedbackType,
      comment: formData.get('comment') as string
    });
  };

  if (isLoading) return <div className="animate-pulse h-screen bg-ink-950 p-6"><div className="h-20 bg-ink-900 rounded-xl mb-4"/><div className="h-96 bg-ink-900 rounded-xl"/></div>;
  if (error || !event) return <div className="p-6 text-rose-400">Failed to load event or not found.</div>;

  const subjectName = formatSubjectName(event.subject_display_name, event.subject_id);
  const isPending = event.state === 'PENDING';
  const hasAlert = !!event.alert;
  const alertStatus = event.alert?.status;

  // Determine allowed actions based on alert status rules
  const canAck = hasAlert && alertStatus === 'OPEN';
  const canDismiss = hasAlert && (alertStatus === 'OPEN' || alertStatus === 'ACKNOWLEDGED');
  const canEscalate = hasAlert && alertStatus !== 'ESCALATED' && alertStatus !== 'DISMISSED';

  return (
    <div className="flex flex-col h-full gap-6 max-w-5xl mx-auto w-full pb-10">
      
      {/* Header section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-ink-800 pb-6">
        <div>
          <button onClick={() => router.back()} className="text-sm text-cyan-500 hover:underline mb-2">← Back to Alerts</button>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold text-white">{subjectName}</h1>
            <TierPill tier={event.tier} />
          </div>
          <p className="text-sm text-gray-400 font-mono">
            {formatDateTimeTz(event.created_at)} • {event.device_name || 'Unknown Device'} {event.device_location ? `(${event.device_location})` : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StateBadge state={event.state} />
          {event.alert && <StateBadge status={event.alert.status} />}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Details & Evidence */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          
          <Card className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-lg">Detection Analysis</h3>
              <div className="flex items-center gap-2 group relative">
                <span className="text-2xl font-bold font-mono text-cyan-400">{(event.confidence * 100).toFixed(0)}%</span>
                <span className="text-xs text-gray-400 uppercase tracking-widest">{event.confidence_calibrated ? 'Confidence' : 'Model Score'}</span>
                {!event.confidence_calibrated && (
                  <Info size={14} className="text-gray-500 ml-1" />
                )}
                {!event.confidence_calibrated && (
                  <div className="absolute right-0 top-full mt-2 w-48 bg-ink-800 text-xs text-gray-300 p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 shadow-xl border border-ink-700">
                    Uncalibrated model score, not a probability.
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex flex-wrap gap-4 text-sm text-gray-400 border-b border-ink-800 pb-4">
              <div><span className="block text-xs uppercase text-ink-500">Model Version</span> <span className="font-mono">{event.model_version || '—'}</span></div>
              <div><span className="block text-xs uppercase text-ink-500">Feature Version</span> <span className="font-mono">{event.feature_version || '—'}</span></div>
              <div><span className="block text-xs uppercase text-ink-500">Track ID</span> <span className="font-mono">{event.track_id || '—'}</span></div>
            </div>

            <h4 className="text-sm font-bold uppercase text-gray-500 tracking-wider">Evidence</h4>
            <EvidenceList evidence={event.evidence} poseQuality={event.pose_quality} summary={event.evidence_summary} />
          </Card>

          {/* Feedback Form */}
          {(event.state === 'CONFIRMED' || event.state === 'CANCELLED') && (
            <Card>
              <h3 className="font-bold text-lg mb-4">Caregiver Feedback</h3>
              {event.feedback ? (
                <div className="bg-ink-950 p-4 rounded-xl border border-ink-800">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-sm font-bold text-white">{event.feedback.feedback_type.replace('_', ' ')}</span>
                    <span className="text-xs text-gray-500">{formatDateTimeTz(event.feedback.created_at)}</span>
                  </div>
                  {event.feedback.comment && <p className="text-sm text-gray-300 mt-2 italic">"{event.feedback.comment}"</p>}
                </div>
              ) : (
                <form onSubmit={handleFeedbackSubmit} className="flex flex-col gap-4">
                  <div className="grid grid-cols-2 gap-2">
                    <label className="flex items-center gap-2 p-3 bg-ink-950 border border-ink-800 rounded-xl cursor-pointer hover:bg-ink-800">
                      <input type="radio" name="type" value="TRUE_FALL" required className="accent-cyan-500" />
                      <span className="text-sm font-medium">True Fall</span>
                    </label>
                    <label className="flex items-center gap-2 p-3 bg-ink-950 border border-ink-800 rounded-xl cursor-pointer hover:bg-ink-800">
                      <input type="radio" name="type" value="FALSE_POSITIVE" required className="accent-cyan-500" />
                      <span className="text-sm font-medium">False Positive</span>
                    </label>
                    <label className="flex items-center gap-2 p-3 bg-ink-950 border border-ink-800 rounded-xl cursor-pointer hover:bg-ink-800">
                      <input type="radio" name="type" value="UNCERTAIN" required className="accent-cyan-500" />
                      <span className="text-sm font-medium">Uncertain</span>
                    </label>
                    <label className="flex items-center gap-2 p-3 bg-ink-950 border border-ink-800 rounded-xl cursor-pointer hover:bg-ink-800">
                      <input type="radio" name="type" value="SYSTEM_FAILURE" required className="accent-cyan-500" />
                      <span className="text-sm font-medium">System Failure</span>
                    </label>
                  </div>
                  <Input name="comment" placeholder="Additional details (optional)..." />
                  <Button type="submit" disabled={feedbackMut.isPending} className="self-end">Submit Feedback</Button>
                </form>
              )}
            </Card>
          )}
        </div>

        {/* Right Column: Actions & Timeline */}
        <div className="flex flex-col gap-6">
          
          <Card className="flex flex-col gap-4">
            <h3 className="font-bold text-lg border-b border-ink-800 pb-2">Response Actions</h3>
            
            {isPending ? (
              <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 flex flex-col gap-3">
                <div className="flex items-center gap-2 text-rose-400 font-bold">
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                  Grace Period Active
                </div>
                <p className="text-xs text-rose-400/80">If this is a false alarm, you can cancel it before it escalates to an alert.</p>
                <Button 
                  variant="secondary" 
                  className="bg-rose-950 hover:bg-rose-900 border-rose-900 text-rose-400"
                  onClick={() => actMut.mutate({ action: 'cancel' })}
                  disabled={actMut.isPending}
                >
                  Cancel Event
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <Button 
                  className="w-full justify-center" 
                  onClick={() => actMut.mutate({ action: 'ack' })} 
                  disabled={!canAck || actMut.isPending}
                >
                  Acknowledge
                </Button>
                <div className="flex gap-2">
                  <Button 
                    variant="secondary" 
                    className="flex-1 justify-center" 
                    onClick={() => setConfirmAction('dismiss')}
                    disabled={!canDismiss || actMut.isPending}
                  >
                    Dismiss
                  </Button>
                  <Button 
                    variant="secondary" 
                    className="flex-1 justify-center border-orange-900/50 hover:bg-orange-950 text-orange-400" 
                    onClick={() => setConfirmAction('escalate')}
                    disabled={!canEscalate || actMut.isPending}
                  >
                    Escalate
                  </Button>
                </div>
                {event.alert?.response_time_seconds !== undefined && (
                  <p className="text-xs text-center text-gray-500 mt-2">
                    Response time: {event.alert.response_time_seconds}s
                  </p>
                )}
              </div>
            )}
          </Card>

          {/* Notifications Status (Admin) */}
          {user?.role === 'admin' && event.notifications && event.notifications.length > 0 && (
            <Card>
              <h3 className="font-bold text-sm text-gray-400 uppercase tracking-wider mb-4">Notifications</h3>
              <div className="flex flex-col gap-3">
                {event.notifications.map(n => (
                  <div key={n.id} className="flex flex-col bg-ink-950 p-2 rounded-lg border border-ink-800 text-xs gap-1">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-gray-300">{n.channel} - {n.kind}</span>
                      <span className={`font-mono ${n.status === 'FAILED' ? 'text-rose-500' : 'text-emerald-500'}`}>{n.status}</span>
                    </div>
                    {n.error_code && <span className="text-rose-400 font-mono">Error: {n.error_code}</span>}
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card>
            <h3 className="font-bold text-sm text-gray-400 uppercase tracking-wider mb-4">Timeline</h3>
            <Timeline entries={event.timeline} />
          </Card>

        </div>
      </div>

      <ConfirmDialog
        isOpen={confirmAction !== null}
        onClose={() => setConfirmAction(null)}
        onConfirm={(note) => {
          if (confirmAction) actMut.mutate({ action: confirmAction, note });
        }}
        title={`${confirmAction === 'dismiss' ? 'Dismiss' : 'Escalate'} Alert`}
        message={`Are you sure you want to ${confirmAction} this alert?`}
        variant={confirmAction === 'escalate' ? 'danger' : 'primary'}
        showNote={true}
        loading={actMut.isPending}
      />
    </div>
  );
}
