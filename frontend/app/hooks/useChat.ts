/**
 * useChat - Real-time chat message management
 * Tracks conversation between user and drone
 */

import { useState, useCallback } from 'react';
import type { ChatMessage, ChatRole, ChatMessageType } from '@/app/types';

/** Generate unique ID for messages */
function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  isThinking: boolean;
  addMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => string;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  addUserCommand: (command: string) => string;
  addDroneThinking: () => string;
  addDroneResponse: (content: string) => string;
  addToolAction: (toolName: string, content: string, success?: boolean) => string;
  addFoundAlert: (content: string, imageUrl?: string, entityId?: string) => string;
  addError: (content: string) => string;
  addMemoryInfo: (content: string) => string;
  addNavigation: (content: string) => string;
  setThinking: (thinking: boolean) => void;
  clearChat: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);

  const addMessage = useCallback((msg: Omit<ChatMessage, 'id' | 'timestamp'>): string => {
    const id = generateId();
    const newMessage: ChatMessage = {
      ...msg,
      id,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMessage]);
    return id;
  }, []);

  const updateMessage = useCallback((id: string, updates: Partial<ChatMessage>) => {
    setMessages(prev => prev.map(msg => 
      msg.id === id ? { ...msg, ...updates } : msg
    ));
  }, []);

  const addUserCommand = useCallback((command: string): string => {
    return addMessage({
      role: 'user',
      type: 'command',
      content: command
    });
  }, [addMessage]);

  const addDroneThinking = useCallback((): string => {
    setIsThinking(true);
    return addMessage({
      role: 'drone',
      type: 'thinking',
      content: 'Processing...'
    });
  }, [addMessage]);

  const addDroneResponse = useCallback((content: string): string => {
    setIsThinking(false);
    return addMessage({
      role: 'drone',
      type: 'response',
      content
    });
  }, [addMessage]);

  const addToolAction = useCallback((toolName: string, content: string, success?: boolean): string => {
    return addMessage({
      role: 'drone',
      type: 'action',
      content,
      toolName,
      toolSuccess: success
    });
  }, [addMessage]);

  const addFoundAlert = useCallback((content: string, imageUrl?: string, entityId?: string): string => {
    return addMessage({
      role: 'drone',
      type: 'found',
      content,
      imageUrl,
      entityId
    });
  }, [addMessage]);

  const addError = useCallback((content: string): string => {
    setIsThinking(false);
    return addMessage({
      role: 'system',
      type: 'error',
      content
    });
  }, [addMessage]);

  const addMemoryInfo = useCallback((content: string): string => {
    return addMessage({
      role: 'drone',
      type: 'memory',
      content
    });
  }, [addMessage]);

  const addNavigation = useCallback((content: string): string => {
    return addMessage({
      role: 'drone',
      type: 'navigation',
      content
    });
  }, [addMessage]);

  const setThinking = useCallback((thinking: boolean) => {
    setIsThinking(thinking);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setIsThinking(false);
  }, []);

  return {
    messages,
    isThinking,
    addMessage,
    updateMessage,
    addUserCommand,
    addDroneThinking,
    addDroneResponse,
    addToolAction,
    addFoundAlert,
    addError,
    addMemoryInfo,
    addNavigation,
    setThinking,
    clearChat
  };
}
