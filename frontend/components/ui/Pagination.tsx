'use client';

import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between border-t border-ink-800 pt-4 mt-4">
      <span className="text-sm text-gray-400">
        Page {page} of {totalPages}
      </span>
      <div className="flex gap-2">
        <button 
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="p-2 rounded-lg border border-ink-800 text-white disabled:text-gray-600 disabled:bg-ink-900/50 hover:bg-ink-800 transition-colors"
        >
          <ChevronLeft size={16} />
        </button>
        <button 
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="p-2 rounded-lg border border-ink-800 text-white disabled:text-gray-600 disabled:bg-ink-900/50 hover:bg-ink-800 transition-colors"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}