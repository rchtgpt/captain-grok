/**
 * ChatMessage - Individual message in the chat feed
 * Different styles based on message type (command, response, action, etc.)
 */

'use client';

import { memo } from 'react';
import type { ChatMessage as ChatMessageType } from '@/app/types';
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  message: ChatMessageType;
}

/** Icons for different message types */
const MessageIcon = ({ type, success }: { type: string; success?: boolean }) => {
  switch (type) {
    case 'command':
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
      );
    case 'thinking':
      return (
        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" 
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      );
    case 'action':
      return success === false ? (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      );
    case 'response':
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      );
    case 'found':
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      );
    case 'error':
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      );
    case 'memory':
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      );
    case 'navigation':
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
      );
    default:
      return null;
  }
};

/** Format timestamp */
function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  });
}

export const ChatMessageComponent = memo(function ChatMessage({ 
  message 
}: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  
  // Style mappings based on type
  const typeStyles: Record<string, { bg: string; text: string; border: string; icon: string }> = {
    command: {
      bg: 'bg-blue-500/10',
      text: 'text-blue-300',
      border: 'border-blue-500/30',
      icon: 'text-blue-400'
    },
    thinking: {
      bg: 'bg-zinc-800/50',
      text: 'text-zinc-400',
      border: 'border-zinc-700/50',
      icon: 'text-zinc-500'
    },
    action: {
      bg: message.toolSuccess === false ? 'bg-red-500/10' : 'bg-amber-500/10',
      text: message.toolSuccess === false ? 'text-red-300' : 'text-amber-300',
      border: message.toolSuccess === false ? 'border-red-500/30' : 'border-amber-500/30',
      icon: message.toolSuccess === false ? 'text-red-400' : 'text-amber-400'
    },
    response: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-300',
      border: 'border-emerald-500/30',
      icon: 'text-emerald-400'
    },
    found: {
      bg: 'bg-green-500/15',
      text: 'text-green-300',
      border: 'border-green-500/40',
      icon: 'text-green-400'
    },
    error: {
      bg: 'bg-red-500/10',
      text: 'text-red-300',
      border: 'border-red-500/30',
      icon: 'text-red-400'
    },
    memory: {
      bg: 'bg-purple-500/10',
      text: 'text-purple-300',
      border: 'border-purple-500/30',
      icon: 'text-purple-400'
    },
    navigation: {
      bg: 'bg-cyan-500/10',
      text: 'text-cyan-300',
      border: 'border-cyan-500/30',
      icon: 'text-cyan-400'
    },
    system: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-300',
      border: 'border-emerald-500/30',
      icon: 'text-emerald-400'
    },
    observation: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-300',
      border: 'border-emerald-500/30',
      icon: 'text-emerald-400'
    },
    success: {
      bg: 'bg-green-500/10',
      text: 'text-green-300',
      border: 'border-green-500/30',
      icon: 'text-green-400'
    }
  };
  
  const style = typeStyles[message.type] || typeStyles.response;

  return (
    <div 
      className={cn(
        'flex gap-3 p-3 rounded-lg border transition-all',
        style.bg,
        style.border,
        isUser && 'ml-4',
        !isUser && !isSystem && 'mr-4'
      )}
    >
      {/* Icon */}
      <div className={cn('flex-shrink-0 mt-0.5', style.icon)}>
        <MessageIcon type={message.type} success={message.toolSuccess} />
      </div>
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Tool name badge */}
        {message.toolName && (
          <span className="inline-block px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-zinc-800 text-zinc-400 mb-1">
            {message.toolName}
          </span>
        )}
        
        {/* Message content */}
        <p className={cn('text-sm leading-relaxed', style.text)}>
          {message.content}
        </p>
        
        {/* Image preview if found */}
        {message.imageUrl && (
          <div className="mt-2">
            <img 
              src={message.imageUrl} 
              alt="Captured" 
              className="w-16 h-16 rounded-lg object-cover border border-zinc-700/50"
            />
          </div>
        )}
      </div>
      
      {/* Timestamp */}
      <div className="flex-shrink-0 text-[10px] text-zinc-600">
        {formatTime(message.timestamp)}
      </div>
    </div>
  );
});

export default ChatMessageComponent;
