/**
 * Live Execution Panel
 * Shows real-time command execution with animated tool status
 */

'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Circle,
  Mic,
  Bot,
  Plane,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  RotateCw,
  Search,
  Eye,
  Clock,
  Zap,
  Home,
  PlaneLanding,
  Sparkles,
} from 'lucide-react';
import type { CommandExecution, ToolExecution, ToolStatus } from '@/app/types';

interface LiveExecutionProps {
  execution: CommandExecution;
  className?: string;
}

// Map tool names to icons
const toolIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  takeoff: Plane,
  land: PlaneLanding,
  move: ArrowUp,
  rotate: RotateCw,
  search: Search,
  look: Eye,
  analyze: Eye,
  look_around: Eye,
  wait: Clock,
  flip: Zap,
  return_home: Home,
};

// Get icon for tool
function getToolIcon(toolName: string) {
  return toolIcons[toolName] || Circle;
}

// Get direction icon for move tool
function getMoveIcon(direction: string) {
  switch (direction) {
    case 'up': return ArrowUp;
    case 'down': return ArrowDown;
    case 'left': return ArrowLeft;
    case 'right': return ArrowRight;
    case 'forward': return ArrowUp;
    case 'backward': return ArrowDown;
    default: return ArrowUp;
  }
}

// Status colors and icons
function getStatusIcon(status: ToolStatus) {
  switch (status) {
    case 'pending':
      return <Circle className="h-5 w-5 text-slate-500" />;
    case 'executing':
      return <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />;
    case 'success':
      return <CheckCircle2 className="h-5 w-5 text-emerald-400" />;
    case 'error':
      return <XCircle className="h-5 w-5 text-red-400" />;
  }
}

function getStatusStyles(status: ToolStatus): string {
  switch (status) {
    case 'pending':
      return 'opacity-50';
    case 'executing':
      return 'bg-blue-500/10 border-blue-500/30 shadow-blue-500/20 shadow-lg';
    case 'success':
      return 'bg-emerald-500/5 border-emerald-500/20';
    case 'error':
      return 'bg-red-500/5 border-red-500/20';
  }
}

// Format tool arguments for display
function formatArguments(args: Record<string, unknown>): string {
  if (!args || Object.keys(args).length === 0) return '';
  
  return Object.entries(args)
    .map(([key, value]) => {
      if (typeof value === 'string' && value.length > 30) {
        return `${key}: "${value.slice(0, 30)}..."`;
      }
      return `${key}: ${JSON.stringify(value)}`;
    })
    .join(', ');
}

// Single tool row component
function ToolRow({ tool }: { tool: ToolExecution }) {
  const Icon = tool.tool === 'move' && tool.arguments.direction
    ? getMoveIcon(tool.arguments.direction as string)
    : getToolIcon(tool.tool);
  
  const argsStr = formatArguments(tool.arguments);
  
  return (
    <div
      className={cn(
        'flex items-start gap-3 p-3 rounded-lg border border-slate-700/50 transition-all duration-300',
        getStatusStyles(tool.status)
      )}
    >
      {/* Status Icon */}
      <div className="flex-shrink-0 mt-0.5">
        {getStatusIcon(tool.status)}
      </div>
      
      {/* Tool Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <Icon className={cn(
            'h-4 w-4',
            tool.status === 'pending' ? 'text-slate-500' :
            tool.status === 'executing' ? 'text-blue-400' :
            tool.status === 'success' ? 'text-emerald-400' :
            'text-red-400'
          )} />
          <span className={cn(
            'font-mono text-sm font-medium',
            tool.status === 'pending' ? 'text-slate-500' :
            tool.status === 'executing' ? 'text-blue-300' :
            tool.status === 'success' ? 'text-emerald-300' :
            'text-red-300'
          )}>
            {tool.tool}
          </span>
          {argsStr && (
            <span className="text-xs text-slate-500 font-mono truncate">
              ({argsStr})
            </span>
          )}
        </div>
        
        {/* Result message */}
        {tool.message && tool.status !== 'pending' && (
          <p className={cn(
            'mt-1 text-sm',
            tool.status === 'executing' ? 'text-blue-300/70' :
            tool.status === 'success' ? 'text-slate-400' :
            'text-red-400/80'
          )}>
            {tool.message}
          </p>
        )}
      </div>
      
      {/* Index badge */}
      <Badge
        variant="outline"
        className={cn(
          'flex-shrink-0 text-xs',
          tool.status === 'pending' ? 'border-slate-600 text-slate-500' :
          tool.status === 'executing' ? 'border-blue-500/50 text-blue-400' :
          tool.status === 'success' ? 'border-emerald-500/50 text-emerald-400' :
          'border-red-500/50 text-red-400'
        )}
      >
        {tool.index}/{tool.total}
      </Badge>
    </div>
  );
}

export function LiveExecution({ execution, className }: LiveExecutionProps): React.ReactElement {
  // Calculate progress
  const completedTools = execution.toolExecutions.filter(
    t => t.status === 'success' || t.status === 'error'
  ).length;
  const totalTools = execution.toolExecutions.length;
  const progress = totalTools > 0 ? (completedTools / totalTools) * 100 : 0;
  
  return (
    <Card className={cn(
      'bg-gradient-to-br from-slate-900/90 to-slate-950/90 border-slate-700/50 backdrop-blur-xl shadow-2xl overflow-hidden',
      className
    )}>
      {/* Animated border gradient */}
      <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/20 via-purple-500/20 to-pink-500/20 opacity-50 animate-pulse" style={{ filter: 'blur(40px)' }} />
      
      <CardHeader className="relative z-10 pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-400" />
            Executing Command
          </CardTitle>
          {totalTools > 0 && (
            <Badge variant="outline" className="border-indigo-500/50 text-indigo-300">
              {completedTools} / {totalTools} tools
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="relative z-10 space-y-6">
        {/* User Command */}
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Mic className="h-4 w-4 text-white" />
          </div>
          <div className="flex-1 bg-slate-800/50 rounded-2xl rounded-tl-sm px-4 py-3 border border-slate-700/50">
            <p className="text-slate-100 font-medium">{execution.command}</p>
          </div>
        </div>
        
        {/* AI Response */}
        {execution.aiResponse && (
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div className="flex-1 bg-slate-800/30 rounded-2xl rounded-tl-sm px-4 py-3 border border-slate-700/30">
              <p className="text-slate-300 italic">{execution.aiResponse}</p>
            </div>
          </div>
        )}
        
        {/* Progress Bar */}
        {totalTools > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">Progress</span>
              <span className="text-slate-400">{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} className="h-2 bg-slate-800" />
          </div>
        )}
        
        {/* Tool Executions */}
        {execution.toolExecutions.length > 0 && (
          <div className="space-y-2">
            {execution.toolExecutions.map((tool) => (
              <ToolRow key={`${tool.tool}-${tool.index}`} tool={tool} />
            ))}
          </div>
        )}
        
        {/* Error Display */}
        {execution.error && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
            <p className="text-red-400 text-sm">{execution.error}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
