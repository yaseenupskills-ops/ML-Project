import React from 'react';
import { useStore } from '../../lib/store';
import { useRouter } from 'next/navigation';
import { Pill, Button } from '../ui';

export function TopHeaderBar() {
  const { user, logout } = useStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  if (!user) return null;

  return (
    <header className="h-16 border-b border-ink-800 bg-ink-950/80 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-300 font-medium">{user.name}</span>
        <Pill className="uppercase tracking-widest">{user.role.replace('_', ' ')}</Pill>
      </div>
      <Button variant="secondary" onClick={handleLogout} className="text-sm px-3 py-1.5">
        Logout
      </Button>
    </header>
  );
}
