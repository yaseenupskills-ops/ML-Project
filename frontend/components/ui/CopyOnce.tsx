'use client';

import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { Button } from './index';

interface CopyOnceProps {
  value: string;
  label?: string;
  warning?: string;
}

export function CopyOnce({ value, label = 'Secret Key', warning = 'This will not be shown again.' }: CopyOnceProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col gap-2 p-4 bg-ink-900 border border-ink-800 rounded-xl">
      <span className="text-sm font-medium text-white">{label}</span>
      <div className="flex items-center gap-2">
        <code className="flex-1 bg-ink-950 border border-ink-800 rounded-lg px-3 py-2 text-sm text-cyan-400 font-mono break-all">
          {value}
        </code>
        <Button variant="secondary" onClick={handleCopy} className="shrink-0 flex items-center gap-2">
          {copied ? <Check size={16} className="text-emerald-500" /> : <Copy size={16} />}
          {copied ? 'Copied' : 'Copy'}
        </Button>
      </div>
      {warning && <p className="text-xs text-rose-400 mt-1 font-medium">{warning}</p>}
    </div>
  );
}