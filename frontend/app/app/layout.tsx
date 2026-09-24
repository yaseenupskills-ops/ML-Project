'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '../../lib/store';
import { Sidebar, MobileBar } from '../../components/layout/Sidebar';
import { TopHeaderBar } from '../../components/layout/TopHeaderBar';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isLoggedIn, user } = useStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && !isLoggedIn) {
      router.push('/login');
    }
  }, [isLoggedIn, mounted, router]);

  if (!mounted || !isLoggedIn || !user) {
    return null;
  }

  return (
    <div className="flex h-screen bg-ink-950 text-white overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopHeaderBar />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 pb-20 md:pb-6">
          {children}
        </main>
      </div>
      <MobileBar />
    </div>
  );
}
