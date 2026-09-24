import { apiFetch } from './api';
import type { User, CreateUserRequest, CreateUserResponse, ResetPasswordResponse } from '@/types';

export async function getUsers(): Promise<User[]> {
  return apiFetch<User[]>('/users');
}

export async function getUser(id: string): Promise<User> {
  return apiFetch<User>(`/users/${id}`);
}

export async function createUser(data: CreateUserRequest): Promise<CreateUserResponse> {
  return apiFetch<CreateUserResponse>('/users', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateUser(id: string, data: Partial<User>): Promise<User> {
  return apiFetch<User>(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function resetPassword(userId: string): Promise<ResetPasswordResponse> {
  return apiFetch<ResetPasswordResponse>(`/users/${userId}/reset-password`, { method: 'POST' });
}

export async function assignSubjects(userId: string, subjectIds: string[]): Promise<void> {
  await apiFetch<void>(`/users/${userId}/subjects`, { method: 'PUT', body: JSON.stringify({ subject_ids: subjectIds }) });
}