import React from 'react';
import { NotFoundState } from '@/components/ui';
import { APP_NAME } from '@/lib/constants';
import Link from 'next/link';

export default function GlobalNotFound() {
  return (
    <div className="min-h-screen bg-ink-950 flex flex-col items-center justify-center p-4 text-white">
      <div className="mb-8 flex items-center gap-2">
        <span className="text-cyan-500 font-mono text-2xl font-bold">F.</span>
        <span className="text-xl font-bold">{APP_NAME}</span>
      </div>
      <div className="w-full max-w-lg bg-ink-900 border border-ink-800 rounded-2xl p-8 shadow-2xl">
        <NotFoundState />
      </div>
    </div>
  );
}