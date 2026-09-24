import React from 'react';
import { Search } from 'lucide-react';
import Link from 'next/link';

export function NotFoundState() {
  return (
    <div className="flex flex-col items-center justify-center w-full h-64 gap-4 text-gray-400">
      <Search size={48} className="text-ink-700" />
      <h2 className="text-xl font-bold text-white">Not Found</h2>
      <p>The requested resource could not be found.</p>
      <Link href="/app" className="mt-2 text-cyan-500 hover:underline">Return to Dashboard</Link>
    </div>
  );
}