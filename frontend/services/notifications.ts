import { apiFetch } from './api';
import type { Notification } from '@/types';

export async function getNotifications(params?: { status?: string; event_id?: string }): Promise<Notification[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.append('status', params.status);
  if (params?.event_id) qs.append('event_id', params.event_id);
  const qsStr = qs.toString();
  return apiFetch<Notification[]>(`/notifications${qsStr ? '?' + qsStr : ''}`);
}

export async function retryNotification(id: string): Promise<void> {
  await apiFetch<void>(`/notifications/${id}/retry`, { method: 'POST' });
}