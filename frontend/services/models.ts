import { apiFetch } from './api';
import type { ModelRecord, PromoteModelRequest } from '@/types';

export async function getModels(): Promise<ModelRecord[]> {
  return apiFetch<ModelRecord[]>('/models');
}

export async function getModel(id: string): Promise<ModelRecord> {
  return apiFetch<ModelRecord>(`/models/${id}`);
}

export async function promoteModel(id: string, data: PromoteModelRequest): Promise<ModelRecord> {
  return apiFetch<ModelRecord>(`/models/${id}/promote`, { method: 'POST', body: JSON.stringify(data) });
}