/**
 * Hook for streaming command execution via SSE
 * Provides real-time updates as tools execute
 */

'use client';

import { useState, useCallback, useRef } from 'react';
import type {
  CommandExecution,
  CommandStreamState,
  FoundTarget,
  ToolCall,
  ToolExecution,
  SSEAiResponsePayload,
  SSEToolStartPayload,
  SSEToolCompletePayload,
  SSEFoundPayload,
  SSEDonePayload,
  SSETargetFoundPayload,
  ChatMessage,
} from '@/app/types';
import { useDroneVoice } from './useDroneVoice';
import { toast } from 'sonner';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';

// Sound effect for found target
const playFoundChime = () => {
  try {
    // Create an audio context for a pleasant chime
    const audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    
    // Create oscillator for the chime
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    // Pleasant chime frequencies (C major arpeggio)
    const frequencies = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
    
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(frequencies[0], audioContext.currentTime);
    
    // Quick arpeggio
    frequencies.forEach((freq, i) => {
      oscillator.frequency.setValueAtTime(freq, audioContext.currentTime + i * 0.1);
    });
    
    // Envelope
    gainNode.gain.setValueAtTime(0, audioContext.currentTime);
    gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.05);
    gainNode.gain.linearRampToValueAtTime(0.2, audioContext.currentTime + 0.3);
    gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.8);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.8);
  } catch (e) {
    console.log('Could not play chime:', e);
  }
};

/** Generate unique ID for messages */
function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function useCommandStream(): CommandStreamState & {
  voiceEnabled: boolean;
  setVoiceEnabled: (enabled: boolean) => void;
  voiceAvailable: boolean;
  chatMessages: ChatMessage[];
  isThinking: boolean;
  clearChat: () => void;
} {
  const [history, setHistory] = useState<CommandExecution[]>([]);
  const [currentExecution, setCurrentExecution] = useState<CommandExecution | null>(null);
  const [foundTarget, setFoundTarget] = useState<FoundTarget | null>(null);
  const [showFoundModal, setShowFoundModal] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  
  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  
  // Ref to track the current execution for updates
  const executionRef = useRef<CommandExecution | null>(null);
  
  // Helper to add chat messages
  const addChatMessage = useCallback((msg: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...msg,
      id: generateMessageId(),
      timestamp: new Date()
    };
    setChatMessages(prev => [...prev, newMessage]);
    return newMessage.id;
  }, []);
  
  // Clear chat
  const clearChat = useCallback(() => {
    setChatMessages([]);
    setIsThinking(false);
  }, []);
  
  // Voice narration hook
  const droneVoice = useDroneVoice({
    enabled: true,
    pitch: 0.9,
    rate: 1.05,
  });
  
  // Check if voice is available
  const voiceAvailable = typeof window !== 'undefined' && 'speechSynthesis' in window;

  const executeCommand = useCallback(async (text: string) => {
    if (isExecuting) return;
    
    setIsExecuting(true);
    setIsThinking(true);
    
    // Add user command to chat
    addChatMessage({
      role: 'user',
      type: 'command',
      content: text
    });
    
    // Don't add thinking message - we use the isThinking indicator instead
    
    // Create new execution entry
    const id = crypto.randomUUID();
    const execution: CommandExecution = {
      id,
      timestamp: new Date(),
      command: text,
      toolCalls: [],
      toolExecutions: [],
      status: 'processing'
    };
    
    executionRef.current = execution;
    setCurrentExecution(execution);
    
    try {
      // Use fetch with streaming
      const response = await fetch(`${BACKEND_URL}/command/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }
      
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        // Parse SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer
        
        let currentEvent = '';
        let currentData = '';
        
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7);
          } else if (line.startsWith('data: ')) {
            currentData = line.slice(6);
          } else if (line === '' && currentEvent && currentData) {
            // Empty line = end of event
            try {
              const data = JSON.parse(currentData);
              handleSSEEvent(currentEvent, data);
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
            currentEvent = '';
            currentData = '';
          }
        }
      }
    } catch (error) {
      console.error('Command stream error:', error);
      
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      // Add error to chat
      addChatMessage({
        role: 'system',
        type: 'error',
        content: `Error: ${errorMessage}`
      });
      
      // Update execution with error
      if (executionRef.current) {
        const errorExecution = {
          ...executionRef.current,
          status: 'error' as const,
          error: errorMessage
        };
        executionRef.current = errorExecution;
        setCurrentExecution({ ...errorExecution });
        
        // Move to history - capture value before clearing
        setHistory(prev => [errorExecution, ...prev]);
        setCurrentExecution(null);
        executionRef.current = null;
      }
    } finally {
      setIsExecuting(false);
      setIsThinking(false);
    }
  }, [isExecuting, addChatMessage]);
  
  const handleSSEEvent = useCallback((eventType: string, data: unknown) => {
    if (!executionRef.current) return;
    
    switch (eventType) {
      case 'command_received':
        // Command acknowledged - already set
        setIsThinking(false);
        break;
        
      case 'ai_response': {
        const payload = data as SSEAiResponsePayload;
        const toolCalls = payload.tool_calls || [];
        
        executionRef.current = {
          ...executionRef.current,
          aiResponse: payload.response,
          toolCalls: toolCalls,
          // Initialize tool executions as pending
          toolExecutions: toolCalls.map((tc: ToolCall, i: number) => ({
            index: i + 1,
            total: toolCalls.length,
            tool: tc.name,
            arguments: tc.arguments,
            status: 'pending' as const
          }))
        };
        setCurrentExecution({ ...executionRef.current });
        
        // Clear thinking state since we got a response
        setIsThinking(false);
        
        // Add AI response to chat - only if not empty
        if (payload.response && payload.response.trim()) {
          addChatMessage({
            role: 'drone',
            type: 'response',
            content: payload.response
          });
        }
        break;
      }
      
      case 'chat': {
        // New chat message from backend - skip empty messages
        // Backend sends either { message, type } or { content, message_type } format
        const payload = data as { message?: string; content?: string; type?: string; message_type?: string };
        const messageContent = payload.message || payload.content || '';
        const messageType = payload.type || payload.message_type || 'response';
        
        // Skip thinking messages - we use our own indicator
        if (messageType === 'thinking') {
          break;
        }
        
        // Clear thinking state since we got a real message
        setIsThinking(false);
        
        if (messageContent && messageContent.trim()) {
          addChatMessage({
            role: 'drone',
            type: messageType as ChatMessage['type'],
            content: messageContent
          });
        }
        break;
      }
        
      case 'tool_start': {
        const payload = data as SSEToolStartPayload;
        // Update the specific tool to executing status
        executionRef.current = {
          ...executionRef.current,
          toolExecutions: executionRef.current.toolExecutions.map((te: ToolExecution) =>
            te.index === payload.index
              ? { ...te, status: 'executing' as const }
              : te
          )
        };
        setCurrentExecution({ ...executionRef.current });
        
        // Add tool start to chat
        const toolDescription = getToolDescription(payload.tool, payload.arguments);
        addChatMessage({
          role: 'drone',
          type: 'action',
          content: toolDescription,
          toolName: payload.tool
        });
        
        // 🔊 Voice narration for tool start
        droneVoice.speakToolStart(payload.tool, payload.arguments || {});
        break;
      }
        
      case 'tool_complete': {
        const payload = data as SSEToolCompletePayload;
        // Update the specific tool with result
        executionRef.current = {
          ...executionRef.current,
          toolExecutions: executionRef.current.toolExecutions.map((te: ToolExecution) =>
            te.index === payload.index
              ? {
                  ...te,
                  status: payload.success ? 'success' as const : 'error' as const,
                  message: payload.message,
                  data: payload.data || undefined
                }
              : te
          )
        };
        setCurrentExecution({ ...executionRef.current });
        
        // Add tool completion to chat (for significant results)
        if (payload.message && !isMinorTool(payload.tool)) {
          addChatMessage({
            role: 'drone',
            type: 'action',
            content: payload.message,
            toolName: payload.tool,
            toolSuccess: payload.success
          });
        }
        
        // 🔊 Voice narration for tool completion (only major tools)
        droneVoice.speakToolComplete(payload.tool, payload.success, payload.message);
        break;
      }
        
      case 'found': {
        const payload = data as SSEFoundPayload;
        const found: FoundTarget = {
          target: payload.target,
          imageUrl: payload.imageUrl,
          description: payload.description,
          confidence: payload.confidence,
          angle: payload.angle
        };
        
        executionRef.current = {
          ...executionRef.current,
          foundTarget: found
        };
        setCurrentExecution({ ...executionRef.current });
        
        // Add found alert to chat
        addChatMessage({
          role: 'drone',
          type: 'found',
          content: `Found: ${payload.target}! ${payload.description}`,
          imageUrl: payload.imageUrl || undefined
        });
        
        // Set found target and open modal
        setFoundTarget(found);
        setShowFoundModal(true);
        
        // Play chime!
        playFoundChime();
        
        // 🔊 Voice narration for found target
        droneVoice.speakFound(payload.target);
        break;
      }
      
      case 'target_found': {
        // Facial recognition match - target from pre-uploaded photos
        const payload = data as SSETargetFoundPayload;
        
        // Add to chat
        addChatMessage({
          role: 'drone',
          type: 'found',
          content: `TARGET FOUND: ${payload.target.name}! Match confidence: ${Math.round(payload.confidence * 100)}%`,
          imageUrl: payload.matchedPhotoUrl || undefined
        });
        
        // Play the chime
        playFoundChime();
        
        // Show toast notification
        toast.success(`Target Found: ${payload.target.name}`, {
          description: `${Math.round(payload.confidence * 100)}% match confidence`,
          duration: 8000,
        });
        
        // 🔊 Voice narration
        droneVoice.speakFound(payload.target.name);
        break;
      }
        
      case 'error': {
        const payload = data as { message: string };
        executionRef.current = {
          ...executionRef.current,
          error: payload.message
        };
        setCurrentExecution({ ...executionRef.current });
        
        // Add error to chat
        addChatMessage({
          role: 'system',
          type: 'error',
          content: payload.message
        });
        break;
      }
        
      case 'done': {
        const payload = data as SSEDonePayload;
        const completedExecution = {
          ...executionRef.current,
          status: payload.status === 'success' ? 'complete' as const : 'error' as const,
          error: payload.error
        };
        executionRef.current = completedExecution;
        setCurrentExecution({ ...completedExecution });
        
        // Move to history - capture the value before clearing
        setHistory(prev => [completedExecution, ...prev]);
        setCurrentExecution(null);
        executionRef.current = null;
        setIsThinking(false);
        break;
      }
    }
  }, [addChatMessage, droneVoice]);
  
  /** Get human-readable tool description */
  function getToolDescription(tool: string, args: Record<string, unknown>): string {
    switch (tool) {
      case 'takeoff':
        return 'Taking off...';
      case 'land':
        return 'Landing...';
      case 'rotate':
        return `Rotating ${args.angle || 0}°...`;
      case 'move':
        return `Moving ${args.direction || 'forward'} ${args.distance || 50}cm...`;
      case 'search_for_target':
        return `Searching for ${args.target || 'target'}...`;
      case 'scan_surroundings':
        return 'Scanning surroundings...';
      case 'recall':
        return `Recalling ${args.query || 'memory'}...`;
      case 'navigate_to':
        return `Navigating to ${args.reference || 'target'}...`;
      case 'whats_that':
        return 'Analyzing what I see...';
      default:
        return `Executing ${tool}...`;
    }
  }
  
  /** Check if tool is minor (don't spam chat) */
  function isMinorTool(tool: string): boolean {
    return ['get_battery', 'get_status'].includes(tool);
  }

  // View a found target from history
  const viewFoundTarget = useCallback((target: FoundTarget) => {
    setFoundTarget(target);
    setShowFoundModal(true);
  }, []);

  return {
    history,
    currentExecution,
    foundTarget,
    showFoundModal,
    setShowFoundModal,
    executeCommand,
    isExecuting,
    viewFoundTarget,
    // Voice controls
    voiceEnabled: droneVoice.enabled,
    setVoiceEnabled: droneVoice.setEnabled,
    voiceAvailable,
    // Chat
    chatMessages,
    isThinking,
    clearChat
  };
}
