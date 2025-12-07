/**
 * Type definitions for Voice Task Assistant
 */

export type RecordingState = 'idle' | 'recording' | 'processing' | 'complete' | 'error';

export interface TranscriptionResponse {
  text: string;
}

export interface TranscriptionError {
  error: string;
  details?: string;
}

export interface BackendTaskResponse {
  stream_url?: string;
  mjpeg_url?: string;
  streamUrl?: string;
  [key: string]: unknown;
}

export interface AudioRecorderState {
  isRecording: boolean;
  recordingState: RecordingState;
  transcript: string;
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
}

export interface VideoStreamState {
  streamUrl: string | null;
  isLoading: boolean;
  hasError: boolean;
  setStreamUrl: (url: string | null) => void;
  clearStream: () => void;
}

export interface StatusMessage {
  text: string;
  type: 'idle' | 'recording' | 'processing' | 'success' | 'error';
}

// ============================================================================
// SSE Streaming Types for Real-Time Command Execution
// ============================================================================

/** SSE event types emitted by the backend */
export type SSEEventType = 
  | 'command_received' 
  | 'ai_response' 
  | 'tool_start' 
  | 'tool_complete' 
  | 'found' 
  | 'error' 
  | 'done';

/** A tool call planned by Grok */
export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
}

/** Status of a tool during execution */
export type ToolStatus = 'pending' | 'executing' | 'success' | 'error';

/** Live execution state for a single tool */
export interface ToolExecution {
  index: number;
  total: number;
  tool: string;
  arguments: Record<string, unknown>;
  status: ToolStatus;
  message?: string;
  data?: Record<string, unknown>;
}

/** Found target information from search operations */
export interface FoundTarget {
  target: string;
  imageUrl: string | null;
  description: string;
  confidence: string;
  angle?: number;
}

/** Complete state for a command execution (current or historical) */
export interface CommandExecution {
  id: string;
  timestamp: Date;
  command: string;
  aiResponse?: string;
  toolCalls: ToolCall[];
  toolExecutions: ToolExecution[];
  foundTarget?: FoundTarget;
  status: 'processing' | 'complete' | 'error';
  error?: string;
}

/** SSE Event Payloads */
export interface SSECommandReceivedPayload {
  command: string;
}

export interface SSEAiResponsePayload {
  response: string;
  tool_calls: ToolCall[];
}

export interface SSEToolStartPayload {
  index: number;
  total: number;
  tool: string;
  arguments: Record<string, unknown>;
}

export interface SSEToolCompletePayload {
  index: number;
  tool: string;
  success: boolean;
  message: string;
  data: Record<string, unknown> | null;
}

export interface SSEFoundPayload {
  target: string;
  imageUrl: string | null;
  description: string;
  confidence: string;
  angle?: number;
}

export interface SSEErrorPayload {
  message: string;
}

export interface SSEDonePayload {
  status: 'success' | 'error';
  total_tools?: number;
  successful?: number;
  error?: string;
}

/** Hook return type for command streaming */
export interface CommandStreamState {
  history: CommandExecution[];
  currentExecution: CommandExecution | null;
  foundTarget: FoundTarget | null;
  showFoundModal: boolean;
  setShowFoundModal: (show: boolean) => void;
  executeCommand: (text: string) => Promise<void>;
  isExecuting: boolean;
  viewFoundTarget: (target: FoundTarget) => void;
}
