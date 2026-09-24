import { apiFetch } from './api';
import type { Subject, CreateSubjectRequest } from '@/types';

export async function getSubjects(): Promise<Subject[]> {
  return apiFetch<Subject[]>('/subjects');
}

export async function getSubject(id: string): Promise<Subject> {
  return apiFetch<Subject>(`/subjects/${id}`);
}

export async function createSubject(data: CreateSubjectRequest): Promise<Subject> {
  return apiFetch<Subject>('/subjects', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateSubject(id: string, data: Partial<Subject>): Promise<Subject> {
  return apiFetch<Subject>(`/subjects/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}