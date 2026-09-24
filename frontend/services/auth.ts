import { apiFetch } from './api';
import type { User, LoginRequest, ChangePasswordRequest } from '@/types';

// The new backend's /auth/me returns this shape (MeResponse in schemas.py)
interface BackendMeResponse {
  id: string;
  name: string;
  email: string;
  role: string;
  must_change_password: boolean;
  assigned_subject_ids: string[];
}

/** Normalize the raw backend MeResponse into our frontend User type. */
function normalizeMeResponse(raw: BackendMeResponse): User {
  return {
    id: raw.id,
    name: raw.name,
    email: raw.email,
    role: raw.role as User['role'],
    must_change_password: raw.must_change_password,
    assigned_subject_ids: raw.assigned_subject_ids ?? [],
    assigned_subjects: raw.assigned_subject_ids ?? [],
    is_active: true, // if we got a 200 the account is active
    created_at: undefined,
    updated_at: undefined,
  };
}

export async function login(credentials: LoginRequest): Promise<User> {
  // POST /api/v1/auth/login — backend sets httpOnly cookies + csrf_token cookie
  const raw = await apiFetch<BackendMeResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });

  // After login the backend returns the same shape as MeResponse, so normalize.
  // Then call /auth/me to also pick up assigned_subject_ids (login doesn't include it).
  try {
    return await getMe();
  } catch {
    // Fallback: use the login response directly if /me fails somehow
    return normalizeMeResponse(raw);
  }
}

export async function getMe(): Promise<User> {
  const raw = await apiFetch<BackendMeResponse>('/auth/me');
  return normalizeMeResponse(raw);
}

export async function refreshSession(): Promise<void> {
  await apiFetch<void>('/auth/refresh', { method: 'POST' });
}

export async function logout(): Promise<void> {
  await apiFetch<void>('/auth/logout', { method: 'POST' });
}

export async function changePassword(data: ChangePasswordRequest): Promise<void> {
  await apiFetch<void>('/auth/change-password', { method: 'POST', body: JSON.stringify(data) });
}

export function isDevBypass(): boolean {
  if (process.env.NODE_ENV === 'production') return false;
  return process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === 'true';
}

export function devBypassUser(): User {
  return {
    id: 'dev-1',
    name: 'Dev Admin',
    email: 'dev@fallguard.local',
    role: 'admin',
    must_change_password: false,
    is_active: true,
    assigned_subject_ids: [],
    assigned_subjects: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}