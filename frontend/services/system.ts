import { apiFetch } from './api';
import type { SystemHealth } from '@/types';

export async function getSystemHealth(): Promise<SystemHealth> {
  return apiFetch<SystemHealth>('/system/health');
}