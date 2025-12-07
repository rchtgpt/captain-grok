/**
 * Loading spinner component
 */

'use client';

import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  text?: string;
  className?: string;
}

export function LoadingSpinner({ text = 'Processing audio...', className }: LoadingSpinnerProps): React.ReactElement {
  return (
    <div className={cn('flex flex-col items-center gap-6 py-12', className)}>
      <div className="relative">
        <Loader2 className="h-16 w-16 animate-spin text-indigo-500" />
        <div className="absolute inset-0 h-16 w-16 bg-indigo-500/30 rounded-full blur-xl animate-pulse" />
      </div>
      <p className="text-lg font-medium text-slate-300">{text}</p>
      <div className="flex gap-2">
        <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" />
        <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce delay-100" style={{ animationDelay: '0.1s' }} />
        <div className="w-2 h-2 bg-pink-500 rounded-full animate-bounce delay-200" style={{ animationDelay: '0.2s' }} />
      </div>
    </div>
  );
}
