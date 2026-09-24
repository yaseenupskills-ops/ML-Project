export class ApiError extends Error {
  status: number;
  data: unknown;
  retryAfter?: number;
  constructor(message: string, status: number, data?: unknown, retryAfter?: number) {
    super(message);
    this.status = status;
    this.data = data;
    this.retryAfter = retryAfter;
    this.name = 'ApiError';
  }
}

export function getCookie(name: string): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : undefined;
}

export function resolveUrl(endpoint: string): string {
  const base = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
  const normalized = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  if (normalized.startsWith('/api/v1')) {
    return `${base}${normalized}`;
  }
  return `${base}/api/v1${normalized}`;
}

let isRefreshing = false;
let refreshPromise: Promise<void> | null = null;

async function refreshToken(): Promise<void> {
  if (isRefreshing && refreshPromise) return refreshPromise;
  isRefreshing = true;

  const csrf = getCookie('csrf_token');
  const headers: Record<string, string> = {};
  if (csrf) headers['X-CSRF-Token'] = csrf;

  refreshPromise = fetch(resolveUrl('/auth/refresh'), {
    method: 'POST',
    headers,
    credentials: 'include',
  }).then(res => {
    if (!res.ok) throw new ApiError('Session expired', 401);
  }).finally(() => {
    isRefreshing = false;
    refreshPromise = null;
  });
  return refreshPromise;
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = resolveUrl(endpoint);
  const method = (options.method || 'GET').toUpperCase();
  
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  
  if (method !== 'GET' && method !== 'HEAD') {
    const csrf = getCookie('csrf_token');
    if (csrf) headers.set('X-CSRF-Token', csrf);
  }
  
  const config: RequestInit = { ...options, headers, credentials: 'include' };
  
  let response = await fetch(url, config);
  
  // Try refreshing token only for authenticated endpoints, not login/refresh itself
  if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    try {
      await refreshToken();
      // Update CSRF token header if a new one was issued during refresh
      if (method !== 'GET' && method !== 'HEAD') {
        const newCsrf = getCookie('csrf_token');
        if (newCsrf) headers.set('X-CSRF-Token', newCsrf);
      }
      response = await fetch(url, { ...config, headers });
    } catch {
      throw new ApiError('Session expired', 401);
    }
  }
  
  if (!response.ok) {
    let errorData: any;
    try { 
      errorData = await response.json(); 
    } catch { 
      errorData = null; 
    }

    const retryAfter = response.status === 429 
      ? parseInt(response.headers.get('Retry-After') || '0', 10) || undefined 
      : undefined;

    let errorMessage = `API Error: ${response.statusText}`;
    if (errorData) {
      if (typeof errorData.detail === 'string') {
        if (errorData.detail === 'invalid_credentials') {
          errorMessage = 'Invalid email or password';
        } else if (errorData.detail === 'account_disabled') {
          errorMessage = 'This account has been disabled';
        } else if (errorData.detail === 'csrf_failed') {
          errorMessage = 'Security token invalid or expired. Please refresh the page.';
        } else {
          errorMessage = errorData.detail;
        }
      } else if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', ');
      } else if (errorData.message) {
        errorMessage = errorData.message;
      }
    }

    throw new ApiError(errorMessage, response.status, errorData, retryAfter);
  }
  
  const text = await response.text();
  if (!text) return {} as T;
  try { 
    return JSON.parse(text) as T; 
  } catch { 
    return text as unknown as T; 
  }
}