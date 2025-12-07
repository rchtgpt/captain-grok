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
} from '@/app/types';
import { useDroneVoice } from './useDroneVoice';

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

export function useCommandStream(): CommandStreamState & {
  voiceEnabled: boolean;
  setVoiceEnabled: (enabled: boolean) => void;
  voiceAvailable: boolean;
} {
  const [history, setHistory] = useState<CommandExecution[]>([]);
  const [currentExecution, setCurrentExecution] = useState<CommandExecution | null>(null);
  const [foundTarget, setFoundTarget] = useState<FoundTarget | null>(null);
  const [showFoundModal, setShowFoundModal] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  
  // Ref to track the current execution for updates
  const executionRef = useRef<CommandExecution | null>(null);
  
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
      
      // Update execution with error
      if (executionRef.current) {
        const errorExecution = {
          ...executionRef.current,
          status: 'error' as const,
          error: error instanceof Error ? error.message : 'Unknown error'
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
    }
  }, [isExecuting]);
  
  const handleSSEEvent = (eventType: string, data: unknown) => {
    if (!executionRef.current) return;
    
    switch (eventType) {
      case 'command_received':
        // Command acknowledged - already set
        break;
        
      case 'ai_response': {
        const payload = data as SSEAiResponsePayload;
        executionRef.current = {
          ...executionRef.current,
          aiResponse: payload.response,
          toolCalls: payload.tool_calls,
          // Initialize tool executions as pending
          toolExecutions: payload.tool_calls.map((tc: ToolCall, i: number) => ({
            index: i + 1,
            total: payload.tool_calls.length,
            tool: tc.name,
            arguments: tc.arguments,
            status: 'pending' as const
          }))
        };
        setCurrentExecution({ ...executionRef.current });
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
        
        // Set found target and open modal
        setFoundTarget(found);
        setShowFoundModal(true);
        
        // Play chime!
        playFoundChime();
        
        // 🔊 Voice narration for found target
        droneVoice.speakFound(payload.target);
        break;
      }
        
      case 'error': {
        const payload = data as { message: string };
        executionRef.current = {
          ...executionRef.current,
          error: payload.message
        };
        setCurrentExecution({ ...executionRef.current });
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
        break;
      }
    }
  };

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
    voiceAvailable
  };
}
