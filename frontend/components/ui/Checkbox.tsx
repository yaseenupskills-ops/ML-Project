'use client';

import React from 'react';
import { Check } from 'lucide-react';

interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
}

export function Checkbox({ checked, onChange, label, disabled }: CheckboxProps) {
  return (
    <label className={`flex items-center gap-2 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
      <div className={`
        w-4 h-4 rounded border flex items-center justify-center transition-colors
        ${checked ? 'bg-cyan-500 border-cyan-500' : 'bg-ink-900 border-ink-700 hover:border-ink-500'}
      `}>
        {checked && <Check size={12} className="text-white" />}
      </div>
      {label && <span className="text-sm text-gray-300">{label}</span>}
      <input 
        type="checkbox" 
        className="sr-only" 
        checked={checked} 
        onChange={(e) => onChange(e.target.checked)} 
        disabled={disabled}
      />
    </label>
  );
}