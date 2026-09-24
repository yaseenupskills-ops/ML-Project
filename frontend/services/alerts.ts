import { apiFetch } from './api';
import type { Alert, BulkAlertAction, BulkActionResult, EventFilters, PaginatedResponse, FallEvent } from '@/types';

export async function getAlerts(filters?: { status?: string; limit?: number; [key: string]: any }): Promise<PaginatedResponse<FallEvent>> {
  const params = new URLSearchParams();
  if (filters) {
    Object.entries(filters).forEach(([k, v]) => { if (v !== undefined && v !== '') params.append(k, String(v)); });
  }
  const qs = params.toString();
  return apiFetch<PaginatedResponse<FallEvent>>(`/alerts${qs ? '?' + qs : ''}`);
}

export async function acknowledgeAlert(id: string): Promise<Alert> {
  return apiFetch<Alert>(`/alerts/${id}/acknowledge`, { method: 'POST' });
}

export async function dismissAlert(id: string, note?: string): Promise<Alert> {
  return apiFetch<Alert>(`/alerts/${id}/dismiss`, { method: 'POST', body: JSON.stringify({ note }) });
}

export async function escalateAlert(id: string, note?: string): Promise<Alert> {
  return apiFetch<Alert>(`/alerts/${id}/escalate`, { method: 'POST', body: JSON.stringify({ note }) });
}

export async function bulkAlertAction(action: BulkAlertAction): Promise<BulkActionResult> {
  return apiFetch<BulkActionResult>('/alerts/bulk', { method: 'POST', body: JSON.stringify(action) });
}

export async function exportAlertsCsv(filters: EventFilters): Promise<void> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => { if (v !== undefined && v !== '') params.append(k, String(v)); });
  const qs = params.toString();
  
  const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/alerts/export.csv${qs ? '?' + qs : ''}`;
  
  const headers = new Headers();
  const match = typeof document !== 'undefined' ? document.cookie.match(/(^| )csrf_token=([^;]+)/) : null;
  const csrf = match ? decodeURIComponent(match[2]) : undefined;
  if (csrf) headers.set('X-CSRF-Token', csrf);
  
  const res = await fetch(url, { credentials: 'include', headers });
  if (!res.ok) throw new Error('Export failed');
  
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `alerts_export_${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}