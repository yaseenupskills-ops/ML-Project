'use client';

import React, { useState } from 'react';
import { Modal } from './Modal';
import { Button } from './index';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (note?: string) => void | Promise<void>;
  title: string;
  message: string;
  confirmLabel?: string;
  variant?: 'danger' | 'primary';
  loading?: boolean;
  showNote?: boolean;
}

export function ConfirmDialog({ isOpen, onClose, onConfirm, title, message, confirmLabel = 'Confirm', variant = 'primary', loading = false, showNote = false }: ConfirmDialogProps) {
  const [note, setNote] = useState('');
  
  const handleConfirm = () => {
    onConfirm(showNote ? note : undefined);
  };

  const confirmBtnClass = variant === 'danger' 
    ? 'bg-rose-600 hover:bg-rose-700 text-white' 
    : 'bg-cyan-500 hover:bg-cyan-600 text-white';

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <div className="flex flex-col gap-4">
        <p className="text-gray-300 text-sm">{message}</p>
        
        {showNote && (
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-400">Note (optional)</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="w-full bg-ink-900 border border-ink-800 rounded-xl p-2 text-white text-sm focus:outline-none focus:border-cyan-500 resize-none h-20"
              placeholder="Add details..."
            />
          </div>
        )}

        <div className="flex justify-end gap-2 mt-2">
          <Button variant="secondary" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button className={confirmBtnClass} onClick={handleConfirm} disabled={loading}>
            {loading ? 'Working...' : confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
}