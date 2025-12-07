'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  getTailingStatus,
  startTailing as apiStartTailing,
  stopTailing as apiStopTailing,
  type TailingStatus
} from '@/lib/api-client';

export interface TailingState {
  // Status
  active: boolean;
  targetId: string | null;
  targetName: string | null;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;
  confidence: number;
  framesTracked: number;
  framesLost: number;
  
  // Loading/error
  isLoading: boolean;
  error: string | null;
  
  // Actions
  startTailing: (targetId: string) => Promise<void>;
  stopTailing: () => Promise<void>;
  refresh: () => Promise<void>;
}

/**
 * Hook for managing real-time person tailing
 */
export function useTailing(): TailingState {
  const [active, setActive] = useState(false);
  const [targetId, setTargetId] = useState<string | null>(null);
  const [targetName, setTargetName] = useState<string | null>(null);
  const [bbox, setBbox] = useState<TailingStatus['bbox']>(null);
  const [confidence, setConfidence] = useState(0);
  const [framesTracked, setFramesTracked] = useState(0);
  const [framesLost, setFramesLost] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Refresh status from server
  const refresh = useCallback(async () => {
    try {
      const status = await getTailingStatus();
      setActive(status.active);
      setTargetId(status.targetId);
      setTargetName(status.targetName);
      setBbox(status.bbox);
      setConfidence(status.confidence);
      setFramesTracked(status.framesTracked);
      setFramesLost(status.framesLost);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get tailing status');
    }
  }, []);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      await refresh();
      setIsLoading(false);
    };
    init();
  }, [refresh]);

  // Poll status while active
  useEffect(() => {
    if (!active) return;
    
    // Poll faster when tailing (200ms for near real-time bbox updates)
    const interval = setInterval(refresh, 200);
    return () => clearInterval(interval);
  }, [active, refresh]);

  // Start tailing
  const startTailing = useCallback(async (targetId: string) => {
    try {
      setError(null);
      const { targetName } = await apiStartTailing(targetId);
      setTargetId(targetId);
      setTargetName(targetName);
      setActive(true);
      setFramesTracked(0);
      setFramesLost(0);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start tailing';
      setError(message);
      throw err;
    }
  }, []);

  // Stop tailing
  const stopTailing = useCallback(async () => {
    try {
      setError(null);
      await apiStopTailing();
      setActive(false);
      setTargetId(null);
      setTargetName(null);
      setBbox(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to stop tailing';
      setError(message);
      throw err;
    }
  }, []);

  return {
    active,
    targetId,
    targetName,
    bbox,
    confidence,
    framesTracked,
    framesLost,
    isLoading,
    error,
    startTailing,
    stopTailing,
    refresh
  };
}
