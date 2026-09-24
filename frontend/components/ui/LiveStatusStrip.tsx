import React from 'react';
import Link from 'next/link';

interface LiveStatusStripProps {
  cameraStatus: 'ok' | 'error';
  modelStatus: 'ok' | 'error';
  backendStatus: 'ok' | 'error';
}

function StatusDot({ status, label }: { status: 'ok' | 'error', label: string }) {
  const isOk = status === 'ok';
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2 h-2 rounded-full ${isOk ? 'bg-emerald-500' : 'bg-rose-500'}`} />
      <span className={`text-xs font-medium uppercase ${isOk ? 'text-gray-300' : 'text-rose-400'}`}>
        {label}: {isOk ? 'ONLINE' : 'ERROR'}
      </span>
    </div>
  );
}

export function LiveStatusStrip({ cameraStatus, modelStatus, backendStatus }: LiveStatusStripProps) {
  const hasError = cameraStatus === 'error' || modelStatus === 'error' || backendStatus === 'error';
  
  return (
    <Link href="/app/system" className={`block w-full border-b px-4 py-1.5 transition-colors ${
      hasError ? 'bg-rose-950/30 border-rose-900/50 hover:bg-rose-900/30' : 'bg-ink-950 border-ink-800 hover:bg-ink-900'
    }`}>
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <span className="text-xs text-gray-500 font-medium">LIVE STATUS</span>
        <div className="flex items-center gap-6">
          <StatusDot status={backendStatus} label="Backend" />
          <StatusDot status={cameraStatus} label="Camera" />
          <StatusDot status={modelStatus} label="Model" />
        </div>
      </div>
    </Link>
  );
}