/**
 * Live Execution Panel - Minimalist design
 */

'use client';

import { cn } from '@/lib/utils';
import {
  Check,
  X,
  Circle,
} from 'lucide-react';
import type { CommandExecution, ToolExecution, ToolStatus } from '@/app/types';

interface LiveExecutionProps {
  execution: CommandExecution;
  className?: string;
}

function getStatusIcon(status: ToolStatus) {
  switch (status) {
    case 'pending':
      return <Circle className="h-3 w-3 text-zinc-700" />;
    case 'executing':
      return <div className="h-3 w-3 border border-zinc-500 border-t-zinc-300 rounded-full animate-spin" />;
    case 'success':
      return <Check className="h-3 w-3 text-zinc-400" />;
    case 'error':
      return <X className="h-3 w-3 text-red-500" />;
  }
}

function formatArguments(args: Record<string, unknown>): string {
  if (!args || Object.keys(args).length === 0) return '';
  return Object.entries(args)
    .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
    .join(', ');
}

function ToolRow({ tool }: { tool: ToolExecution }) {
  const argsStr = formatArguments(tool.arguments);
  
  return (
    <div
      className={cn(
        'flex items-center gap-3 py-2 transition-opacity duration-200',
        tool.status === 'pending' && 'opacity-40'
      )}
    >
      <div className="flex-shrink-0">
        {getStatusIcon(tool.status)}
      </div>
      
      <div className="flex-1 min-w-0 flex items-center gap-2">
        <span className="font-mono text-xs text-zinc-300">{tool.tool}</span>
        {argsStr && (
          <span className="text-xs text-zinc-600 truncate">({argsStr})</span>
        )}
      </div>
      
      <span className="text-xs text-zinc-700 tabular-nums">
        {tool.index}/{tool.total}
      </span>
    </div>
  );
}

export function LiveExecution({ execution, className }: LiveExecutionProps): React.ReactElement {
  const completedTools = execution.toolExecutions.filter(
    t => t.status === 'success' || t.status === 'error'
  ).length;
  const totalTools = execution.toolExecutions.length;
  const progress = totalTools > 0 ? (completedTools / totalTools) * 100 : 0;
  
  return (
    <div className={cn('bg-zinc-900/50 border border-zinc-800 rounded-lg p-4', className)}>
      {/* Command */}
      <div className="mb-4">
        <p className="text-xs text-zinc-600 mb-1">Command</p>
        <p className="text-sm text-zinc-200">{execution.command}</p>
      </div>
      
      {/* AI Response */}
      {execution.aiResponse && (
        <div className="mb-4">
          <p className="text-xs text-zinc-600 mb-1">Response</p>
          <p className="text-sm text-zinc-400">{execution.aiResponse}</p>
        </div>
      )}
      
      {/* Progress */}
      {totalTools > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-xs text-zinc-600 mb-2">
            <span>Progress</span>
            <span>{completedTools}/{totalTools}</span>
          </div>
          <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
            <div 
              className="h-full bg-zinc-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Tools */}
      {execution.toolExecutions.length > 0 && (
        <div className="border-t border-zinc-800 pt-3 space-y-1">
          {execution.toolExecutions.map((tool) => (
            <ToolRow key={`${tool.tool}-${tool.index}`} tool={tool} />
          ))}
        </div>
      )}
      
      {/* Error */}
      {execution.error && (
        <div className="mt-3 p-2 bg-red-950/30 border border-red-900/50 rounded text-xs text-red-400">
          {execution.error}
        </div>
      )}
    </div>
  );
}
