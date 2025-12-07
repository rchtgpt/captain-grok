/**
 * Loading spinner component - Minimalist design
 */

'use client';

import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  text?: string;
  className?: string;
}

export function LoadingSpinner({ text = 'Processing...', className }: LoadingSpinnerProps): React.ReactElement {
  return (
    <div className={cn('flex items-center justify-center gap-3 py-6', className)}>
      <div className="h-4 w-4 border-2 border-zinc-700 border-t-zinc-400 rounded-full animate-spin" />
      <p className="text-sm text-zinc-500">{text}</p>
    </div>
  );
}
