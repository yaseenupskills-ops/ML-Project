import { apiFetch } from './api';
import type { PaginatedResponse, FallEvent, EventFilters } from '@/types';

export async function getEvents(filters: EventFilters): Promise<PaginatedResponse<FallEvent>> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => { if (v !== undefined && v !== '') params.append(k, String(v)); });
  const qs = params.toString();
  return apiFetch<PaginatedResponse<FallEvent>>(`/events${qs ? '?' + qs : ''}`);
}

export async function getEvent(id: string): Promise<FallEvent> {
  return apiFetch<FallEvent>(`/events/${id}`);
}

export async function cancelEvent(id: string): Promise<void> {
  await apiFetch<void>(`/events/${id}/cancel`, { method: 'POST' });
}