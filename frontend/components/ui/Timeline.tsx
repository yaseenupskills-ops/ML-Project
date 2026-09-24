import React from 'react';
import { formatDateTimeTz } from '@/lib/date';
import type { TimelineEntry } from '@/types';

export function Timeline({ entries }: { entries: TimelineEntry[] }) {
  if (!entries?.length) return <p className="text-sm text-gray-500">No timeline events.</p>;

  return (
    <div className="relative border-l border-ink-800 ml-3 space-y-6">
      {entries.map((entry, i) => (
        <div key={i} className="relative pl-5">
          <div className="absolute -left-1.5 mt-1.5 w-3 h-3 rounded-full bg-ink-900 border-2 border-cyan-500" />
          <div className="flex flex-col">
            <span className="text-xs font-mono text-cyan-400">{formatDateTimeTz(entry.timestamp)}</span>
            <span className="text-sm font-medium text-white mt-0.5">
              {entry.action} {entry.actor ? <span className="text-gray-400">by {entry.actor}</span> : null}
            </span>
            {entry.detail && <span className="text-sm text-gray-400 mt-1">{entry.detail}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}