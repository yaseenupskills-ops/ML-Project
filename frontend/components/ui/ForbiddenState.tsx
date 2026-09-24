import React from 'react';
import { ShieldX } from 'lucide-react';
import Link from 'next/link';

export function ForbiddenState() {
  return (
    <div className="flex flex-col items-center justify-center w-full h-64 gap-4 text-gray-400">
      <ShieldX size={48} className="text-amber-500/50" />
      <h2 className="text-xl font-bold text-white">Access Denied</h2>
      <p>You do not have permission to view this page.</p>
      <Link href="/app" className="mt-2 text-cyan-500 hover:underline">Return to Dashboard</Link>
    </div>
  );
}