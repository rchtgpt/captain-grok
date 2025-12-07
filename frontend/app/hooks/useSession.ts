'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  getSessionStatus,
  startSession as apiStartSession,
  stopSession as apiStopSession,
  listSessions,
  deleteSession as apiDeleteSession,
  deleteAllSessions as apiDeleteAllSessions,
  getSessionVideoUrl,
  type SessionStatus,
  type SessionMetadata
} from '@/lib/api-client';

export interface SessionState {
  // Current session status
  isRecording: boolean;
  sessionId: string | null;
  duration: number;
  frameCount: number;
  targetsFoundCount: number;
  
  // Session history
  sessions: SessionMetadata[];
  
  // Loading states
  isLoading: boolean;
  error: string | null;
  
  // Actions
  startRecording: (manual?: boolean) => Promise<void>;
  stopRecording: () => Promise<SessionMetadata | null>;
  refreshStatus: () => Promise<void>;
  refreshSessions: () => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  deleteAllSessions: () => Promise<void>;
  getVideoUrl: (sessionId: string) => string;
}

/**
 * Hook for managing video recording sessions
 */
export function useSession(): SessionState {
  const [isRecording, setIsRecording] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const [targetsFoundCount, setTargetsFoundCount] = useState(0);
  const [sessions, setSessions] = useState<SessionMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Refresh current session status
  const refreshStatus = useCallback(async () => {
    try {
      const status = await getSessionStatus();
      setIsRecording(status.recording);
      setSessionId(status.sessionId);
      setDuration(status.durationSeconds);
      setFrameCount(status.frameCount);
      setTargetsFoundCount(status.targetsFoundCount);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get session status');
    }
  }, []);

  // Refresh session history
  const refreshSessions = useCallback(async () => {
    try {
      const sessionList = await listSessions();
      setSessions(sessionList);
    } catch (err) {
      console.error('Failed to list sessions:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      await Promise.all([refreshStatus(), refreshSessions()]);
      setIsLoading(false);
    };
    init();
  }, [refreshStatus, refreshSessions]);

  // Poll status while recording
  useEffect(() => {
    if (!isRecording) return;
    
    const interval = setInterval(refreshStatus, 1000);
    return () => clearInterval(interval);
  }, [isRecording, refreshStatus]);

  // Start recording
  const startRecording = useCallback(async (manual: boolean = false) => {
    try {
      setError(null);
      const newSessionId = await apiStartSession(manual);
      setSessionId(newSessionId);
      setIsRecording(true);
      setDuration(0);
      setFrameCount(0);
      setTargetsFoundCount(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start recording');
      throw err;
    }
  }, []);

  // Stop recording
  const stopRecording = useCallback(async (): Promise<SessionMetadata | null> => {
    try {
      setError(null);
      const metadata = await apiStopSession();
      setIsRecording(false);
      setSessionId(null);
      
      // Refresh session list to include the new recording
      await refreshSessions();
      
      return metadata;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop recording');
      throw err;
    }
  }, [refreshSessions]);

  // Delete a session
  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await apiDeleteSession(sessionId);
      await refreshSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session');
      throw err;
    }
  }, [refreshSessions]);

  // Delete all sessions
  const deleteAllSessions = useCallback(async () => {
    try {
      await apiDeleteAllSessions();
      setSessions([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete sessions');
      throw err;
    }
  }, []);

  // Get video URL for a session
  const getVideoUrl = useCallback((sessionId: string): string => {
    return getSessionVideoUrl(sessionId);
  }, []);

  return {
    isRecording,
    sessionId,
    duration,
    frameCount,
    targetsFoundCount,
    sessions,
    isLoading,
    error,
    startRecording,
    stopRecording,
    refreshStatus,
    refreshSessions,
    deleteSession,
    deleteAllSessions,
    getVideoUrl
  };
}
