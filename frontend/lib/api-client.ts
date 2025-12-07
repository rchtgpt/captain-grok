/**
 * API client for audio transcription and backend drone commands
 */

import type { TranscriptionResponse, BackendTaskResponse } from '@/app/types';

// Backend server URL - the drone command API runs on port 8080
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';

/**
 * Transcribes audio using the local Next.js API route
 * which proxies to the xAI speech-to-text API
 * 
 * @param audioBlob - The recorded audio blob
 * @returns The transcribed text
 */
export async function transcribeAudio(audioBlob: Blob): Promise<string> {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');

  const response = await fetch('/api/transcribe', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Transcription failed');
  }

  const data: TranscriptionResponse = await response.json();
  return data.text;
}

/**
 * Sends the transcribed text to the backend drone command endpoint
 * 
 * @param text - The transcribed command text
 * @returns The backend response with potential stream URLs
 */
export async function sendToBackend(text: string): Promise<BackendTaskResponse> {
  const response = await fetch(`${BACKEND_URL}/command/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Backend command failed');
  }

  return response.json();
}

