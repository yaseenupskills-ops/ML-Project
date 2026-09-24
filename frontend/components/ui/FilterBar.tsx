'use client';

import React from 'react';
import { Select, Input } from './index';

export interface FilterOption {
  label: string;
  value: string;
}

export interface FilterDef {
  key: string;
  label: string;
  type: 'select' | 'text';
  options?: FilterOption[];
}

interface FilterBarProps {
  filters: FilterDef[];
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  onClearAll: () => void;
}

export function FilterBar({ filters, values, onChange, onClearAll }: FilterBarProps) {
  const hasValues = Object.values(values).some(v => v !== '');

  return (
    <div className="flex flex-wrap items-center gap-3 p-3 bg-ink-900 border border-ink-800 rounded-2xl mb-4">
      {filters.map(filter => (
        <div key={filter.key} className="flex items-center gap-2">
          <span className="text-xs text-gray-400 font-medium">{filter.label}</span>
          {filter.type === 'select' ? (
            <Select 
              value={values[filter.key] || ''} 
              onChange={(e) => onChange(filter.key, e.target.value)}
              className="py-1 px-2 text-sm min-w-[120px]"
            >
              <option value="">All</option>
              {filter.options?.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </Select>
          ) : (
            <Input 
              type="text" 
              value={values[filter.key] || ''} 
              onChange={(e) => onChange(filter.key, e.target.value)}
              className="py-1 px-2 text-sm w-32"
              placeholder={`Filter...`}
            />
          )}
        </div>
      ))}
      
      {hasValues && (
        <button onClick={onClearAll} className="text-xs text-cyan-500 hover:text-cyan-400 ml-auto">
          Clear all
        </button>
      )}
    </div>
  );
}