/**
 * Custom hook for audio recording and transcription
 */

'use client';

import { useState, useRef, useCallback } from 'react';
import { transcribeAudio, sendToBackend } from '@/lib/api-client';
import type { RecordingState, AudioRecorderState } from '@/app/types';

export function useAudioRecorder(onStreamUrlReceived?: (url: string) => void): AudioRecorderState {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [transcript, setTranscript] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async (): Promise<void> => {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });
      mediaRecorderRef.current = mediaRecorder;

      audioChunksRef.current = [];

      // Handle data available
      mediaRecorder.ondataavailable = (event: BlobEvent): void => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // Handle stop
      mediaRecorder.onstop = async (): Promise<void> => {
        await processAudio();
      };

      // Start recording
      mediaRecorder.start();
      setIsRecording(true);
      setRecordingState('recording');
      setError(null);
      setTranscript('');
    } catch (err) {
      console.error('Error starting recording:', err);
      setError('Could not access microphone. Please allow microphone access.');
      setRecordingState('error');
    }
  }, []);

  const stopRecording = useCallback(async (): Promise<void> => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      
      // Stop all tracks
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }

      setIsRecording(false);
      setRecordingState('processing');
    }
  }, [isRecording]);

  const processAudio = async (): Promise<void> => {
    try {
      setRecordingState('processing');

      // Create audio blob
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

      // Transcribe audio
      const transcriptionText = await transcribeAudio(audioBlob);
      setTranscript(transcriptionText);
      setRecordingState('complete');

      // Send to backend
      const response = await sendToBackend(transcriptionText);
      
      // Check for stream URL
      if (response && onStreamUrlReceived) {
        const streamUrl = response.stream_url || response.mjpeg_url || response.streamUrl;
        if (streamUrl) {
          onStreamUrlReceived(streamUrl);
        }
      }
    } catch (err) {
      console.error('Error processing audio:', err);
      setError(err instanceof Error ? err.message : 'Failed to process audio');
      setRecordingState('error');
    }
  };

  return {
    isRecording,
    recordingState,
    transcript,
    error,
    startRecording,
    stopRecording,
  };
}
