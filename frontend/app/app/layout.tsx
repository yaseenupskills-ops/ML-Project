'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';
import { getMe } from '@/services/auth';
import { getSystemHealth } from '@/services/system';
import { Sidebar, MobileBar } from '@/components/layout/Sidebar';
import { TopHeaderBar } from '@/components/layout/TopHeaderBar';
import { Loading } from '@/components/ui';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoggedIn, user, setUser, setServerTimeOffset } = useStore();
  const [mounted, setMounted] = useState(false);
  const [isInitializing, setIsInitializing] = useState(!isLoggedIn);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    async function initSession() {
      if (isLoggedIn) {
        setIsInitializing(false);
        return;
      }
      try {
        const me = await getMe();
        setUser(me);
        
        // Sync server time
        try {
          const health = await getSystemHealth();
          if (health.server_time) {
            const serverMs = new Date(health.server_time).getTime();
            setServerTimeOffset(serverMs - Date.now());
          }
        } catch { /* ignore health check failure */ }
        
      } catch {
        router.push(`/login?next=${encodeURIComponent(pathname)}`);
      } finally {
        setIsInitializing(false);
      }
    }
    
    if (mounted) {
      initSession();
    }
  }, [isLoggedIn, mounted, pathname, router, setUser, setServerTimeOffset]);

  // Force password change guard
  useEffect(() => {
    if (user?.must_change_password && pathname !== '/app/settings') {
      router.push('/app/settings');
    }
  }, [user, pathname, router]);

  if (!mounted || isInitializing || !user) {
    return <div className="h-screen w-full bg-ink-950 flex items-center justify-center"><Loading /></div>;
  }

  return (
    <div className="flex h-screen bg-ink-950 text-white overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <TopHeaderBar />
        {user.must_change_password && pathname !== '/app/settings' && (
          <div className="bg-rose-500/20 text-rose-400 p-2 text-center text-sm border-b border-rose-500/30">
            You must change your password to continue.
          </div>
        )}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 pb-20 md:pb-6 relative z-10">
          {children}
        </main>
      </div>
      <MobileBar />
    </div>
  );
}