/**
 * Status indicator component
 */

'use client';

import { Badge } from '@/components/ui/badge';
import { CheckCircle2, AlertCircle, Loader2, Mic } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { StatusMessage } from '@/app/types';

interface StatusIndicatorProps {
  status: StatusMessage;
  className?: string;
}

export function StatusIndicator({ status, className }: StatusIndicatorProps): React.ReactElement {
  const getIcon = (): React.ReactElement | null => {
    switch (status.type) {
      case 'recording':
        return <Mic className="h-5 w-5 animate-pulse" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 animate-spin" />;
      case 'success':
        return <CheckCircle2 className="h-5 w-5" />;
      case 'error':
        return <AlertCircle className="h-5 w-5" />;
      default:
        return null;
    }
  };

  const getVariant = (): 'default' | 'secondary' | 'destructive' | 'outline' => {
    switch (status.type) {
      case 'success':
        return 'default';
      case 'error':
        return 'destructive';
      case 'recording':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  return (
    <Badge
      variant={getVariant()}
      className={cn(
        'flex items-center gap-3 px-6 py-3 text-base font-semibold rounded-full transition-all duration-300 backdrop-blur-sm',
        status.type === 'recording' && 'bg-red-500/20 text-red-400 border-red-500/60 hover:bg-red-500/30 shadow-lg shadow-red-500/20',
        status.type === 'success' && 'bg-emerald-500/20 text-emerald-400 border-emerald-500/60 hover:bg-emerald-500/30 shadow-lg shadow-emerald-500/20',
        status.type === 'processing' && 'bg-indigo-500/20 text-indigo-400 border-indigo-500/60 shadow-lg shadow-indigo-500/20',
        status.type === 'idle' && 'bg-slate-500/20 text-slate-400 border-slate-500/60',
        status.type === 'error' && 'bg-red-500/20 text-red-400 border-red-500/60',
        className
      )}
    >
      {getIcon()}
      <span className="drop-shadow-sm">{status.text}</span>
    </Badge>
  );
}
