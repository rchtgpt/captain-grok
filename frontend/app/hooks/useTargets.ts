'use client';

import { useState, useCallback, useEffect } from 'react';
import type { Target, TargetsResponse } from '@/app/types';
import { 
  getTargets, 
  getTarget, 
  createTarget as apiCreateTarget,
  updateTarget as apiUpdateTarget,
  deleteTarget as apiDeleteTarget,
  addTargetPhotos as apiAddTargetPhotos
} from '@/lib/api-client';

export interface TargetsState {
  targets: Target[];
  stats: TargetsResponse['stats'] | null;
  isLoading: boolean;
  error: string | null;
  selectedTarget: Target | null;
  
  // Actions
  refresh: () => Promise<void>;
  selectTarget: (target: Target | null) => void;
  createTarget: (name: string, description: string, photos: File[]) => Promise<Target>;
  updateTarget: (targetId: string, updates: { name?: string; description?: string }) => Promise<Target>;
  deleteTarget: (targetId: string) => Promise<void>;
  addPhotos: (targetId: string, photos: File[]) => Promise<Target>;
  markFound: (targetId: string, confidence: number) => void;
}

/**
 * Hook for managing facial recognition targets
 */
export function useTargets(): TargetsState {
  const [targets, setTargets] = useState<Target[]>([]);
  const [stats, setStats] = useState<TargetsResponse['stats'] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTarget, setSelectedTarget] = useState<Target | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await getTargets();
      setTargets(data.targets);
      setStats(data.stats);
      
      // Update selected target if it exists
      if (selectedTarget) {
        const updated = data.targets.find(t => t.id === selectedTarget.id);
        if (updated) {
          setSelectedTarget(updated);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch targets');
    } finally {
      setIsLoading(false);
    }
  }, [selectedTarget]);

  // Initial load and polling
  useEffect(() => {
    refresh();
    
    // Poll every 3 seconds for updates
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, []);

  const selectTarget = useCallback((target: Target | null) => {
    setSelectedTarget(target);
  }, []);

  const createTarget = useCallback(async (
    name: string, 
    description: string, 
    photos: File[]
  ): Promise<Target> => {
    const newTarget = await apiCreateTarget(name, description, photos);
    await refresh();
    return newTarget;
  }, [refresh]);

  const updateTarget = useCallback(async (
    targetId: string,
    updates: { name?: string; description?: string }
  ): Promise<Target> => {
    const updated = await apiUpdateTarget(targetId, updates);
    await refresh();
    return updated;
  }, [refresh]);

  const deleteTarget = useCallback(async (targetId: string): Promise<void> => {
    await apiDeleteTarget(targetId);
    
    // Clear selection if deleted target was selected
    if (selectedTarget?.id === targetId) {
      setSelectedTarget(null);
    }
    
    await refresh();
  }, [refresh, selectedTarget]);

  const addPhotos = useCallback(async (
    targetId: string, 
    photos: File[]
  ): Promise<Target> => {
    const updated = await apiAddTargetPhotos(targetId, photos);
    await refresh();
    return updated;
  }, [refresh]);

  // Called when SSE event reports target found
  const markFound = useCallback((targetId: string, confidence: number) => {
    setTargets(prev => prev.map(t => 
      t.id === targetId 
        ? { ...t, status: 'found' as const, matchConfidence: confidence }
        : t
    ));
    
    // Refresh to get full update from server
    refresh();
  }, [refresh]);

  return {
    targets,
    stats,
    isLoading,
    error,
    selectedTarget,
    refresh,
    selectTarget,
    createTarget,
    updateTarget,
    deleteTarget,
    addPhotos,
    markFound
  };
}
