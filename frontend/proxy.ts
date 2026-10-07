import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Same origin as the Next rewrite in next.config.mjs
const API_ORIGIN = 'http://127.0.0.1:8000';

/**
 * Optimistic session check for page routes: ask the FastAPI backend whether
 * the request's session cookie is valid. Full enforcement happens on every
 * API call via the backend's auth guard — this only keeps unauthenticated
 * users off page routes.
 *
 * When auth is disabled in config.yaml, /api/auth/me returns a guest profile
 * (200), so access stays open.
 */
async function hasValidSession(request: NextRequest): Promise<boolean> {
  try {
    const cookie = request.headers.get('cookie');
    const res = await fetch(`${API_ORIGIN}/api/auth/me`, {
      headers: cookie ? { cookie } : {},
      cache: 'no-store',
    });
    if (res.ok) return true;
    return res.status !== 401; // non-401 (e.g. 500) → don't block the app
  } catch {
    // Backend unreachable → let the request through; API calls will surface it
    return true;
  }
}

export async function proxy(request: NextRequest) {
  if (await hasValidSession(request)) {
    return NextResponse.next();
  }
  const loginUrl = new URL('/login', request.url);
  const { pathname, search } = request.nextUrl;
  loginUrl.searchParams.set('next', `${pathname}${search}`);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ['/', '/history/:path*', '/contacts/:path*'],
};
