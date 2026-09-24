import React from 'react';
import { AlertCircle } from 'lucide-react';
import { Button } from './index';

export function ErrorState({ message, error, onRetry }: { message?: string; error?: string; onRetry?: () => void }) {
  const displayMessage = message || error || 'An error occurred';
  return (
    <div className="flex flex-col items-center justify-center w-full h-64 border border-rose-900/30 rounded-2xl bg-rose-950/10 text-rose-400 gap-4">
      <AlertCircle size={32} />
      <p className="font-medium text-center max-w-md">{displayMessage}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry} className="mt-2 text-rose-400 border-rose-900 hover:bg-rose-900/20">
          Try Again
        </Button>
      )}
    </div>
  );
}