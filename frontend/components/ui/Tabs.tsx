'use client';

import React from 'react';

interface Tab {
  label: string;
  value: string;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (value: string) => void;
}

export function Tabs({ tabs, activeTab, onTabChange }: TabsProps) {
  return (
    <div className="flex overflow-x-auto border-b border-ink-800 hide-scrollbar bg-ink-950">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.value;
        return (
          <button
            key={tab.value}
            onClick={() => onTabChange(tab.value)}
            className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${
              isActive 
                ? 'border-cyan-500 text-white' 
                : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-ink-700'
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}