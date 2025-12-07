/**
 * Recording button component - Minimalist design
 */

'use client';

import { Mic, MicOff } from 'lucide-react';
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
    <button
      onClick={onClick}
      disabled={isProcessing}
      className={cn(
        'relative h-32 w-32 rounded-full transition-all duration-300',
        'flex items-center justify-center',
        'border border-zinc-800',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        'focus:outline-none focus:ring-2 focus:ring-zinc-700 focus:ring-offset-2 focus:ring-offset-zinc-950',
        // Default state
        !isRecording && !isProcessing && [
          'bg-zinc-900 hover:bg-zinc-800',
          'hover:border-zinc-700',
          'active:scale-95',
        ],
        // Recording state
        isRecording && [
          'bg-zinc-100',
          'border-zinc-100',
        ],
        // Processing state
        isProcessing && 'bg-zinc-900',
        className
      )}
      aria-label={isRecording ? 'Stop Recording' : 'Start Recording'}
    >
      {/* Pulse ring when recording */}
      {isRecording && (
        <span className="absolute inset-0 rounded-full bg-zinc-100 animate-ping opacity-20" />
      )}
      
      <Mic 
        className={cn(
          'h-10 w-10 transition-colors duration-300',
          isRecording ? 'text-zinc-900' : 'text-zinc-400',
          isProcessing && 'animate-pulse'
        )} 
      />
    </button>
  );
}
