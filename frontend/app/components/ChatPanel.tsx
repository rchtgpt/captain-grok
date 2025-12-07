/**
 * ChatPanel - Real-time chat feed with the drone
 * Shows conversation history with auto-scroll and text input
 */

'use client';

import { useRef, useEffect, useState } from 'react';
import { ChatMessageComponent } from './ChatMessage';
import type { ChatMessage } from '@/app/types';
import { cn } from '@/lib/utils';

interface ChatPanelProps {
  messages: ChatMessage[];
  isThinking: boolean;
  onSendMessage?: (message: string) => void;
  className?: string;
}

export function ChatPanel({ 
  messages, 
  isThinking,
  onSendMessage,
  className 
}: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [inputValue, setInputValue] = useState('');

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && onSendMessage) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-zinc-800/50">
        <div className="flex items-center gap-2">
          <div className={cn(
            'w-2 h-2 rounded-full',
            isThinking ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'
          )} />
          <h2 className="text-sm font-medium text-zinc-300">Live Feed</h2>
        </div>
        <span className="text-xs text-zinc-600">
          {messages.filter(m => m.content?.trim() && m.type !== 'thinking').length} messages
        </span>
      </div>

      {/* Messages - scrollable area */}
      <div 
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-3 space-y-3"
        style={{ minHeight: 0 }}
      >
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-8 text-center">
            <div className="w-10 h-10 mb-3 rounded-full bg-zinc-800/50 flex items-center justify-center">
              <svg className="w-5 h-5 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-xs text-zinc-500 mb-1">No activity yet</p>
            <p className="text-[10px] text-zinc-600">
              Type below or use the mic
            </p>
          </div>
        ) : (
          <>
            {messages
              .filter(message => 
                message.content && 
                message.content.trim() && 
                message.type !== 'thinking'  // Don't show thinking messages, use indicator instead
              )
              .map(message => (
                <ChatMessageComponent
                  key={message.id}
                  message={message}
                />
              ))}
            
            {/* Thinking indicator */}
            {isThinking && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-zinc-800/30 border border-zinc-700/30">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-xs text-zinc-500">Thinking...</span>
              </div>
            )}
            
            {/* Scroll anchor */}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* Input area */}
      {onSendMessage && (
        <div className="flex-shrink-0 p-3 border-t border-zinc-800/50">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a command..."
              disabled={isThinking}
              className={cn(
                'flex-1 px-3 py-2 text-sm rounded-lg',
                'bg-zinc-800/50 border border-zinc-700/50',
                'text-zinc-200 placeholder-zinc-500',
                'focus:outline-none focus:border-zinc-600 focus:ring-1 focus:ring-zinc-600',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isThinking}
              className={cn(
                'px-3 py-2 rounded-lg text-sm font-medium',
                'bg-emerald-600 hover:bg-emerald-500 text-white',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-colors'
              )}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

export default ChatPanel;
