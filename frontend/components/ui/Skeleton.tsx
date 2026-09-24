import React from 'react';

export function SkeletonLine({ className = 'w-full h-4' }: { className?: string }) {
  return <div className={`bg-ink-800 animate-pulse rounded ${className}`} />;
}

export function Skeleton({ className = 'w-full h-4' }: { className?: string }) {
  return <div className={`bg-ink-800 animate-pulse rounded ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div className="bg-ink-900 border border-ink-800 rounded-2xl p-4 flex flex-col gap-3">
      <SkeletonLine className="w-1/3 h-4" />
      <SkeletonLine className="w-1/2 h-8" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="w-full overflow-hidden rounded-2xl border border-ink-800">
      <div className="bg-ink-900 h-10 border-b border-ink-800" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 p-4 border-b border-ink-800/50">
          <SkeletonLine className="w-8 h-4" />
          <SkeletonLine className="w-32 h-4" />
          <SkeletonLine className="w-24 h-4" />
          <SkeletonLine className="w-full h-4" />
        </div>
      ))}
    </div>
  );
}