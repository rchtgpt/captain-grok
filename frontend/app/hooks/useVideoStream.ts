/**
 * Custom hook for managing MJPEG video stream
 */

'use client';

import { useState, useCallback } from 'react';
import type { VideoStreamState } from '@/app/types';

export function useVideoStream(): VideoStreamState {
  const [streamUrl, setStreamUrlState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [hasError, setHasError] = useState<boolean>(false);

  const setStreamUrl = useCallback((url: string | null): void => {
    if (url) {
      setIsLoading(true);
      setHasError(false);
      
      // Add cache-busting parameter
      const separator = url.includes('?') ? '&' : '?';
      const urlWithCache = `${url}${separator}_t=${Date.now()}`;
      setStreamUrlState(urlWithCache);
    } else {
      setStreamUrlState(null);
      setIsLoading(false);
      setHasError(false);
    }
  }, []);

  const clearStream = useCallback((): void => {
    setStreamUrlState(null);
    setIsLoading(false);
    setHasError(false);
  }, []);

  const handleLoadSuccess = useCallback((): void => {
    setIsLoading(false);
    setHasError(false);
  }, []);

  const handleLoadError = useCallback((): void => {
    setIsLoading(false);
    setHasError(true);
  }, []);

  return {
    streamUrl,
    isLoading,
    hasError,
    setStreamUrl,
    clearStream,
  };
}
