import React from 'react';
import { Check, Minus } from 'lucide-react';
import type { EvidenceItem } from '@/types';

interface EvidenceListProps {
  evidence: EvidenceItem[];
  poseQuality?: number;
  summary?: string;
}

export function EvidenceList({ evidence, poseQuality, summary }: EvidenceListProps) {
  return (
    <div className="flex flex-col gap-4">
      {summary && <p className="text-sm text-gray-300">{summary}</p>}
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {evidence.map((item, i) => (
          <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-ink-900/50 border border-ink-800">
            {item.detected ? <Check size={16} className="text-emerald-500" /> : <Minus size={16} className="text-gray-600" />}
            <span className={`text-sm ${item.detected ? 'text-white' : 'text-gray-500'}`}>{item.label}</span>
            {item.value && <span className="ml-auto text-xs font-mono text-gray-400">{item.value}</span>}
          </div>
        ))}
      </div>
      
      {poseQuality !== undefined && (
        <div className="flex items-center gap-3 mt-2">
          <span className="text-xs text-gray-400 w-24">Pose Quality</span>
          <div className="flex-1 h-1.5 bg-ink-800 rounded-full overflow-hidden">
            <div className="h-full bg-cyan-500" style={{ width: `${Math.min(100, Math.max(0, poseQuality))}%` }} />
          </div>
          <span className="text-xs font-mono text-gray-300 w-8">{Math.round(poseQuality)}%</span>
        </div>
      )}
    </div>
  );
}