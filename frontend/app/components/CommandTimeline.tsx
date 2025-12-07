/**
 * Command Timeline
 * Scrollable history of past commands with expandable details
 */

'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import {
  ChevronDown,
  ChevronRight,
  History,
  Mic,
  Bot,
  CheckCircle2,
  XCircle,
  Target,
  Clock,
  ImageIcon,
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
  const failedTools = execution.toolExecutions.filter(t => t.status === 'error').length;
  const totalTools = execution.toolExecutions.length;
  
  const hasFound = !!execution.foundTarget;
  const isSuccess = execution.status === 'complete';
  const isError = execution.status === 'error';
  
  return (
    <div className={cn(
      'rounded-xl border transition-all duration-200',
      isError ? 'bg-red-500/5 border-red-500/20' :
      hasFound ? 'bg-emerald-500/5 border-emerald-500/30' :
      'bg-slate-800/30 border-slate-700/50',
      'hover:border-slate-600/50'
    )}>
      {/* Header - always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-start gap-3 text-left"
      >
        {/* Expand/Collapse icon */}
        <div className="flex-shrink-0 mt-1">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-slate-500" />
          ) : (
            <ChevronRight className="h-4 w-4 text-slate-500" />
          )}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Time and status */}
          <div className="flex items-center gap-2 mb-2">
            <Clock className="h-3 w-3 text-slate-500" />
            <span className="text-xs text-slate-500">{formatTime(execution.timestamp)}</span>
            
            {/* Found badge */}
            {hasFound && (
              <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30 text-xs px-2 py-0 animate-pulse">
                <Target className="h-3 w-3 mr-1" />
                FOUND!
              </Badge>
            )}
            
            {/* Error badge */}
            {isError && (
              <Badge variant="destructive" className="text-xs px-2 py-0">
                Error
              </Badge>
            )}
          </div>
          
          {/* Command */}
          <div className="flex items-start gap-2 mb-2">
            <Mic className="h-4 w-4 text-indigo-400 flex-shrink-0 mt-0.5" />
            <p className="text-slate-200 text-sm font-medium line-clamp-2">
              {execution.command}
            </p>
          </div>
          
          {/* AI Response preview */}
          {execution.aiResponse && (
            <div className="flex items-start gap-2 mb-2">
              <Bot className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <p className="text-slate-400 text-sm italic line-clamp-1">
                {execution.aiResponse}
              </p>
            </div>
          )}
          
          {/* Tool summary */}
          {totalTools > 0 && (
            <div className="flex items-center gap-2 text-xs">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              <span className="text-slate-500">
                {successfulTools} / {totalTools} tools completed
              </span>
              {failedTools > 0 && (
                <>
                  <span className="text-slate-600">•</span>
                  <XCircle className="h-3 w-3 text-red-400" />
                  <span className="text-red-400">{failedTools} failed</span>
                </>
              )}
            </div>
          )}
        </div>
      </button>
      
      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-4 pt-0">
          <Separator className="mb-4 bg-slate-700/50" />
          
          {/* Full AI Response */}
          {execution.aiResponse && (
            <div className="mb-4 p-3 bg-slate-900/50 rounded-lg">
              <p className="text-xs text-slate-500 mb-1">AI Response</p>
              <p className="text-sm text-slate-300 italic">{execution.aiResponse}</p>
            </div>
          )}
          
          {/* Tool details */}
          {execution.toolExecutions.length > 0 && (
            <div className="space-y-2 mb-4">
              <p className="text-xs text-slate-500 mb-2">Tool Execution Details</p>
              {execution.toolExecutions.map((tool, i) => (
                <div
                  key={i}
                  className={cn(
                    'flex items-center gap-2 text-sm p-2 rounded-lg',
                    tool.status === 'success' ? 'bg-emerald-500/5' :
                    tool.status === 'error' ? 'bg-red-500/5' :
                    'bg-slate-800/30'
                  )}
                >
                  {tool.status === 'success' ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                  ) : tool.status === 'error' ? (
                    <XCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
                  ) : (
                    <div className="h-4 w-4 rounded-full bg-slate-600 flex-shrink-0" />
                  )}
                  <span className="font-mono text-slate-300">{tool.tool}</span>
                  {tool.message && (
                    <span className="text-slate-500 truncate">- {tool.message}</span>
                  )}
                </div>
              ))}
            </div>
          )}
          
          {/* Found target button */}
          {hasFound && execution.foundTarget && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onViewFound?.(execution.foundTarget!);
              }}
              className="w-full p-3 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 rounded-lg border border-emerald-500/30 flex items-center justify-center gap-2 hover:from-emerald-500/30 hover:to-teal-500/30 transition-all"
            >
              <ImageIcon className="h-4 w-4 text-emerald-400" />
              <span className="text-emerald-300 font-medium">View Found Image</span>
            </button>
          )}
          
          {/* Error details */}
          {execution.error && (
            <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/20">
              <p className="text-xs text-red-400">{execution.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function CommandTimeline({ history, onViewFound, className }: CommandTimelineProps): React.ReactElement {
  if (history.length === 0) {
    return (
      <Card className={cn(
        'bg-slate-900/50 border-slate-800/50 backdrop-blur-sm',
        className
      )}>
        <CardContent className="py-12">
          <div className="text-center">
            <History className="h-12 w-12 text-slate-700 mx-auto mb-4" />
            <p className="text-slate-500 text-sm">No commands yet</p>
            <p className="text-slate-600 text-xs mt-1">Your command history will appear here</p>
          </div>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card className={cn(
      'bg-slate-900/50 border-slate-800/50 backdrop-blur-sm',
      className
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-slate-200 flex items-center gap-2">
            <History className="h-5 w-5 text-slate-400" />
            Command History
          </CardTitle>
          <Badge variant="outline" className="text-slate-400 border-slate-700">
            {history.length} {history.length === 1 ? 'command' : 'commands'}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-3">
            {history.map((execution) => (
              <HistoryItem
                key={execution.id}
                execution={execution}
                onViewFound={onViewFound}
              />
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
