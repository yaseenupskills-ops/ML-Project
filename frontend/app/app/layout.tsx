"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from '../../components/layout/Sidebar';
import { PersonaHeaderBar } from '../../components/layout/PersonaHeaderBar';
import { useAppStore } from '../../lib/store';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isLoggedIn } = useAppStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (!isLoggedIn) {
      router.push('/login');
    }
  }, [isLoggedIn, router]);

  if (!mounted || !isLoggedIn) {
    return <div className="h-screen w-full bg-[#010613] flex items-center justify-center text-cyan-500 tech-mono text-sm tracking-widest">AUTHENTICATING...</div>;
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-space-950">
      {/* 1. Sidebar (Fixed left on desktop, bottom bar on mobile) */}
      <Sidebar />
      
      {/* 2 & 3. Main Workspace Area with Top Persona Header */}
      <div className="flex-1 flex flex-col w-full h-full overflow-hidden relative pb-16 md:pb-0">
        <PersonaHeaderBar />
        <main className="flex-1 flex w-full h-full relative overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
