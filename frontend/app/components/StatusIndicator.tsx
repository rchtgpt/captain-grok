/**
 * Status indicator component - Minimalist design
 */

'use client';

import { cn } from '@/lib/utils';
import type { StatusMessage } from '@/app/types';

interface StatusIndicatorProps {
  status: StatusMessage;
  className?: string;
}

export function StatusIndicator({ status, className }: StatusIndicatorProps): React.ReactElement {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Status dot */}
      <span
        className={cn(
          'h-2 w-2 rounded-full transition-colors duration-300',
          status.type === 'recording' && 'bg-zinc-100 animate-pulse',
          status.type === 'processing' && 'bg-zinc-400 animate-pulse',
          status.type === 'success' && 'bg-zinc-500',
          status.type === 'error' && 'bg-red-500',
          status.type === 'idle' && 'bg-zinc-700'
        )}
      />
      <span className="text-sm text-zinc-500">{status.text}</span>
    </div>
  );
}
