'use client';

import { useEffect, useState } from 'react';

export interface SessionUser {
  username: string;
  role: string;
  display_name: string;
  assigned_subjects?: string[];
  guest?: boolean;
}

export interface Session {
  user: SessionUser | null;
  /** True for admins and for guest mode (auth disabled). Defaults to true
   *  while loading so admin controls never flash off. */
  isAdmin: boolean;
  loading: boolean;
}

/**
 * Fetch the current session from /api/auth/me on mount.
 *
 * Every page fetches once per mount (cheap, local API) so role changes take
 * effect immediately after login/logout navigation without stale caches.
 */
export function useSession(): Session {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/api/auth/me', { cache: 'no-store' });
        if (!cancelled) {
          if (res.ok) {
            setUser((await res.json()) as SessionUser);
          } else {
            setUser(null);
          }
        }
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const isAdmin =
    loading || user?.guest === true || user?.role === 'admin';

  return { user, isAdmin, loading };
}
