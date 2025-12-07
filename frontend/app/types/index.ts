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
