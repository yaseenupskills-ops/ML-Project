'use client';

import React from 'react';

export interface DateRange {
  from: string;
  to: string;
}

interface DateRangePickerProps {
  value: DateRange | null;
  onChange: (val: DateRange | null) => void;
  presets?: number[]; // days
}

export function DateRangePicker({ value, onChange, presets = [7, 30, 90] }: DateRangePickerProps) {
  const setPreset = (days: number) => {
    const to = new Date();
    const from = new Date();
    from.setDate(to.getDate() - days);
    onChange({ from: from.toISOString().split('T')[0], to: to.toISOString().split('T')[0] });
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex bg-ink-900 rounded-xl border border-ink-800 overflow-hidden">
        {presets.map(days => (
          <button
            key={days}
            onClick={() => setPreset(days)}
            className="px-3 py-1.5 text-sm text-gray-300 hover:bg-ink-800 hover:text-white border-r border-ink-800 last:border-0 transition-colors"
          >
            {days}d
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <input 
          type="date" 
          value={value?.from || ''} 
          onChange={(e) => onChange({ from: e.target.value, to: value?.to || '' })}
          className="bg-ink-900 border border-ink-800 rounded-xl px-2 py-1.5 text-white color-scheme-dark" 
        />
        <span>to</span>
        <input 
          type="date" 
          value={value?.to || ''} 
          onChange={(e) => onChange({ from: value?.from || '', to: e.target.value })}
          className="bg-ink-900 border border-ink-800 rounded-xl px-2 py-1.5 text-white color-scheme-dark" 
        />
      </div>
      {value && (
        <button onClick={() => onChange(null)} className="text-xs text-cyan-500 hover:text-cyan-400">Clear</button>
      )}
    </div>
  );
}