/**
 * Command Timeline - Minimalist design
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  ChevronDown,
  ChevronRight,
  Check,
  X,
  Target,
  Image,
} from 'lucide-react';
import type { CommandExecution, FoundTarget } from '@/app/types';

interface CommandTimelineProps {
  history: CommandExecution[];
  onViewFound?: (target: FoundTarget) => void;
  className?: string;
}

interface HistoryItemProps {
  execution: CommandExecution;
  onViewFound?: (target: FoundTarget) => void;
}

function formatTime(date: Date): string {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  }).format(date);
}

function HistoryItem({ execution, onViewFound }: HistoryItemProps): React.ReactElement {
  const [expanded, setExpanded] = useState(false);
  
  const successfulTools = execution.toolExecutions.filter(t => t.status === 'success').length;
  const totalTools = execution.toolExecutions.length;
  const hasFound = !!execution.foundTarget;
  const isError = execution.status === 'error';
  
  return (
    <div className={cn(
      'border-b border-zinc-800/50 last:border-0',
      isError && 'bg-red-950/10'
    )}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full py-3 flex items-start gap-3 text-left hover:bg-zinc-900/50 transition-colors"
      >
        <div className="flex-shrink-0 mt-0.5 text-zinc-600">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-zinc-600 tabular-nums">{formatTime(execution.timestamp)}</span>
            {hasFound && (
              <span className="flex items-center gap-1 text-xs text-zinc-300">
                <Target className="h-3 w-3" /> Found
              </span>
            )}
            {isError && (
              <span className="text-xs text-red-500">Error</span>
            )}
          </div>
          
          <p className="text-sm text-zinc-300 line-clamp-1">{execution.command}</p>
          
          {totalTools > 0 && (
            <p className="text-xs text-zinc-600 mt-1">
              {successfulTools}/{totalTools} completed
            </p>
          )}
        </div>
      </button>
      
      {expanded && (
        <div className="pl-7 pb-3 space-y-3">
          {execution.aiResponse && (
            <p className="text-xs text-zinc-500">{execution.aiResponse}</p>
          )}
          
          {execution.toolExecutions.length > 0 && (
            <div className="space-y-1">
              {execution.toolExecutions.map((tool, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  {tool.status === 'success' ? (
                    <Check className="h-3 w-3 text-zinc-500" />
                  ) : tool.status === 'error' ? (
                    <X className="h-3 w-3 text-red-500" />
                  ) : (
                    <div className="h-3 w-3 rounded-full border border-zinc-700" />
                  )}
                  <span className="font-mono text-zinc-400">{tool.tool}</span>
                </div>
              ))}
            </div>
          )}
          
          {hasFound && execution.foundTarget && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onViewFound?.(execution.foundTarget!);
              }}
              className="flex items-center gap-2 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              <Image className="h-3 w-3" />
              View capture
            </button>
          )}
          
          {execution.error && (
            <p className="text-xs text-red-500">{execution.error}</p>
          )}
        </div>
      )}
    </div>
  );
}

export function CommandTimeline({ history, onViewFound, className }: CommandTimelineProps): React.ReactElement {
  if (history.length === 0) {
    return (
      <div className={cn('py-8 text-center', className)}>
        <p className="text-xs text-zinc-700">No commands yet</p>
      </div>
    );
  }
  
  return (
    <div className={cn('bg-zinc-900/30 border border-zinc-800 rounded-lg', className)}>
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="text-sm font-medium text-zinc-400">History</h3>
        <span className="text-xs text-zinc-600">{history.length}</span>
      </div>
      
      <div className="max-h-[320px] overflow-y-auto px-4">
        {history.map((execution) => (
          <HistoryItem
            key={execution.id}
            execution={execution}
            onViewFound={onViewFound}
          />
        ))}
      </div>
    </div>
  );
}
