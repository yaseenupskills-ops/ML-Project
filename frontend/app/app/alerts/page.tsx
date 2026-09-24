'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader, DataTable, Button, FilterBar, DateRangePicker, Checkbox, TierPill, StateBadge, Pagination, GraceBanner, ConfirmDialog, Loading } from '@/components/ui';
import { RoleGuard } from '@/components/layout/RoleGuard';
import { getEvents } from '@/services/events';
import { getSubjects } from '@/services/subjects';
import { getDevices } from '@/services/devices';
import { bulkAlertAction, exportAlertsCsv } from '@/services/alerts';
import { formatDateTimeTz, formatRelativeTime } from '@/lib/date';
import { queryKeys, POLL_ALERTS_LIST, POLL_EVENT_PENDING } from '@/lib/constants';
import { useToast } from '@/components/ui/Toast';
import { useStore } from '@/lib/store';
import { formatSubjectName } from '@/lib/subject-display';
import type { EventFilters, AlertStatus, EventState, EventTier, BulkAlertAction, FallEvent } from '@/types';

export default function AlertsPage() {
  return (
    <RoleGuard allowedRoles={['caregiver', 'admin']}>
      <React.Suspense fallback={<div className="p-8"><Loading /></div>}>
        <AlertsContent />
      </React.Suspense>
    </RoleGuard>
  );
}

function AlertsContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const user = useStore(state => state.user);

  // Filters state from URL
  const [filters, setFilters] = useState<EventFilters>({
    state: (searchParams.get('state') as EventState) || undefined,
    alert_status: (searchParams.get('alert_status') as AlertStatus) || undefined,
    tier: (searchParams.get('tier') as EventTier) || undefined,
    subject_id: searchParams.get('subject_id') || undefined,
    device_id: searchParams.get('device_id') || undefined,
    date_from: searchParams.get('date_from') || undefined,
    date_to: searchParams.get('date_to') || undefined,
    page: parseInt(searchParams.get('page') || '1', 10),
    page_size: 25,
  });

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkAction, setBulkAction] = useState<BulkAlertAction['action'] | null>(null);
  const [bulkNote, setBulkNote] = useState('');

  // Sinc URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== '') params.append(k, String(v));
    });
    router.replace(`${pathname}?${params.toString()}`);
  }, [filters, pathname, router]);

  // Data fetching
  const { data: eventsData, isLoading } = useQuery({
    queryKey: queryKeys.events.list(filters as unknown as Record<string, unknown>),
    queryFn: () => getEvents(filters),
    refetchInterval: POLL_ALERTS_LIST,
  });

  // Fetch pending events for the grace banner (unfiltered by page/status)
  const { data: pendingData } = useQuery({
    queryKey: ['events', 'pending_grace'],
    queryFn: () => getEvents({ state: 'PENDING', page_size: 10 }),
    refetchInterval: POLL_EVENT_PENDING,
  });

  const { data: subjects } = useQuery({ queryKey: queryKeys.subjects.list(), queryFn: getSubjects });
  const { data: devices } = useQuery({ queryKey: queryKeys.devices.list(), queryFn: getDevices });

  const bulkMut = useMutation({
    mutationFn: (action: BulkAlertAction) => bulkAlertAction(action),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.events.all });
      toast('success', `Action completed. Success: ${result.succeeded.length}, Failed: ${result.failed.length}`);
      setSelectedIds(new Set());
      setBulkAction(null);
    }
  });

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value, page: 1 }));
  };

  const toggleSelectAll = (checked: boolean) => {
    if (!eventsData) return;
    if (checked) {
      // Only select rows that actually have alerts
      setSelectedIds(new Set(eventsData.items.filter(e => e.alert).map(e => e.alert!.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const toggleSelect = (alertId: string, checked: boolean) => {
    const next = new Set(selectedIds);
    if (checked) next.add(alertId);
    else next.delete(alertId);
    setSelectedIds(next);
  };

  const doBulkAction = (action: BulkAlertAction['action'], requireConfirm: boolean) => {
    if (requireConfirm) {
      setBulkAction(action);
    } else {
      bulkMut.mutate({ alert_ids: Array.from(selectedIds), action });
    }
  };

  const confirmBulkAction = () => {
    if (bulkAction) {
      bulkMut.mutate({ alert_ids: Array.from(selectedIds), action: bulkAction, note: bulkNote });
    }
  };

  const filterDefs = [
    { key: 'state', label: 'State', type: 'select' as const, options: [
      { label: 'Pending', value: 'PENDING' },
      { label: 'Confirmed', value: 'CONFIRMED' },
      { label: 'Cancelled', value: 'CANCELLED' }
    ]},
    { key: 'alert_status', label: 'Alert Status', type: 'select' as const, options: [
      { label: 'Open', value: 'OPEN' },
      { label: 'Acknowledged', value: 'ACKNOWLEDGED' },
      { label: 'Dismissed', value: 'DISMISSED' },
      { label: 'Escalated', value: 'ESCALATED' }
    ]},
    { key: 'tier', label: 'Tier', type: 'select' as const, options: [
      { label: 'High', value: 'HIGH' },
      { label: 'Medium', value: 'MEDIUM' },
      { label: 'Low', value: 'LOW' }
    ]},
    { key: 'subject_id', label: 'Subject', type: 'select' as const, options: subjects?.map(s => ({ label: formatSubjectName(s.display_name, s.id), value: s.id })) || [] },
    { key: 'device_id', label: 'Device', type: 'select' as const, options: devices?.map(d => ({ label: d.name, value: d.id })) || [] },
  ];

  const filterValues = {
    state: filters.state || '',
    alert_status: filters.alert_status || '',
    tier: filters.tier || '',
    subject_id: filters.subject_id || '',
    device_id: filters.device_id || '',
  };

  const columns = [
    <Checkbox 
      key="all" 
      checked={eventsData?.items.length! > 0 && selectedIds.size === eventsData?.items.filter(e => e.alert).length}
      onChange={toggleSelectAll} 
    />,
    'Timestamp', 'Tier', 'Subject', 'Device', 'State', 'Status', 'Response'
  ];

  const data = (eventsData?.items || []).map(event => {
    return [
      <div key="chk" onClick={e => e.stopPropagation()}>
        {event.alert ? (
          <Checkbox 
            checked={selectedIds.has(event.alert.id)} 
            onChange={(c) => toggleSelect(event.alert!.id, c)} 
          />
        ) : null}
      </div>,
      <span key="time" className="font-mono text-cyan-400 cursor-pointer" onClick={() => router.push(`/app/alerts/${event.id}`)}>
        {formatDateTimeTz(event.created_at)}
      </span>,
      <TierPill key="tier" tier={event.tier} />,
      <span key="sub" className="text-white font-medium">{formatSubjectName(event.subject_display_name, event.subject_id)}</span>,
      <span key="dev" className="text-gray-300">{event.device_name || '—'}</span>,
      <StateBadge key="state" state={event.state} />,
      event.alert ? <StateBadge key="astatus" status={event.alert.status} /> : <span key="none" className="text-gray-500">—</span>,
      <span key="resp" className="text-gray-400">
        {event.alert?.response_time_seconds ? `${event.alert.response_time_seconds}s` : '—'}
      </span>
    ];
  });

  return (
    <div className="flex flex-col h-full gap-4 max-w-[1600px] mx-auto w-full">
      {/* Grace Banners */}
      <div className="flex flex-col gap-2">
        {pendingData?.items.map(e => <GraceBanner key={e.id} event={e} />)}
      </div>

      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <PageHeader title="Alerts" description="Review and respond to fall events." />
        <div className="flex items-center gap-4 mb-6">
          <DateRangePicker 
            value={filters.date_from ? { from: filters.date_from, to: filters.date_to || '' } : null}
            onChange={(r) => setFilters(p => ({ ...p, date_from: r?.from, date_to: r?.to, page: 1 }))}
          />
          <Button variant="secondary" onClick={() => exportAlertsCsv(filters)} className="shrink-0">
            Export CSV
          </Button>
        </div>
      </div>

      <FilterBar 
        filters={filterDefs} 
        values={filterValues} 
        onChange={handleFilterChange}
        onClearAll={() => setFilters({ page: 1, page_size: 25 })}
      />

      {/* Bulk Action Bar */}
      {selectedIds.size > 0 && (
        <div className="bg-ink-900 border border-cyan-500/50 rounded-xl p-3 flex items-center justify-between animate-in slide-in-from-bottom-2">
          <span className="text-sm font-medium text-white">{selectedIds.size} alert(s) selected</span>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={() => doBulkAction('acknowledge', false)} className="text-xs py-1.5 border-emerald-900/50 hover:bg-emerald-950 text-emerald-400">
              Acknowledge
            </Button>
            <Button variant="secondary" onClick={() => doBulkAction('dismiss', true)} className="text-xs py-1.5">
              Dismiss
            </Button>
            <Button variant="secondary" onClick={() => doBulkAction('escalate', true)} className="text-xs py-1.5 border-orange-900/50 hover:bg-orange-950 text-orange-400">
              Escalate
            </Button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-10 bg-ink-900 rounded-xl" />
          <div className="h-64 bg-ink-900 rounded-xl" />
        </div>
      ) : (
        <>
          <DataTable columns={columns} data={data} />
          {eventsData && (
            <Pagination 
              page={eventsData.page} 
              totalPages={eventsData.total_pages} 
              onPageChange={(p) => setFilters(prev => ({ ...prev, page: p }))} 
            />
          )}
        </>
      )}

      <ConfirmDialog
        isOpen={bulkAction !== null}
        onClose={() => setBulkAction(null)}
        onConfirm={confirmBulkAction}
        title={`${bulkAction === 'dismiss' ? 'Dismiss' : 'Escalate'} ${selectedIds.size} Alert(s)`}
        message={`Are you sure you want to ${bulkAction} the selected alerts?`}
        variant={bulkAction === 'escalate' ? 'danger' : 'primary'}
        showNote={true}
        loading={bulkMut.isPending}
      />
    </div>
  );
}
