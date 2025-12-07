/**
 * Recording button component
 */

'use client';

import { Button } from '@/components/ui/button';
import { Mic } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RecordButtonProps {
  isRecording: boolean;
  isProcessing: boolean;
  onClick: () => void;
  className?: string;
}

export function RecordButton({ 
  isRecording, 
  isProcessing, 
  onClick, 
  className 
}: RecordButtonProps): React.ReactElement {
  return (
    <Button
      onClick={onClick}
      disabled={isProcessing}
      className={cn(
        'relative h-56 w-56 md:h-64 md:w-64 lg:h-72 lg:w-72 rounded-full transition-all duration-500',
        'flex flex-col items-center justify-center gap-4',
        'text-white font-bold text-lg',
        'shadow-2xl hover:shadow-[0_0_80px_rgba(99,102,241,0.6)]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'border-4 border-white/10',
        !isRecording && !isProcessing && [
          'bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500',
          'hover:scale-110 hover:from-indigo-600 hover:via-purple-600 hover:to-pink-600',
          'active:scale-100',
          'hover:border-white/20',
          'shadow-[0_0_60px_rgba(99,102,241,0.4)]',
        ],
        isRecording && [
          'bg-gradient-to-br from-red-500 via-pink-500 to-rose-500',
          'animate-pulse',
          'before:absolute before:inset-0 before:rounded-full',
          'before:bg-white/20 before:animate-ping',
          'shadow-[0_0_80px_rgba(239,68,68,0.6)]',
          'border-red-300/30',
        ],
        isProcessing && 'bg-gradient-to-br from-slate-600 to-slate-700 opacity-60',
        className
      )}
      aria-label={isRecording ? 'Stop Recording' : 'Start Recording'}
    >
      <Mic className="h-20 w-20 md:h-24 md:w-24 stroke-[2.5] drop-shadow-lg" />
      <span className="text-lg font-bold drop-shadow-md">
        {isRecording ? 'Stop Recording' : 'Start Recording'}
      </span>
    </Button>
  );
}
