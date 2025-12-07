/**
 * EmergencyControls - Compact emergency button panel for header bar
 * Shows drone status and provides immediate emergency actions
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import type { SystemStatus } from '@/app/types';
import { getDroneStatus, takeoff, land, emergencyStop, returnHome } from '@/lib/api-client';
import { cn } from '@/lib/utils';

interface EmergencyControlsProps {
  className?: string;
  pollInterval?: number; // ms, default 4000
}

/** Battery color based on level */
function getBatteryColor(level: number): string {
  if (level > 50) return 'text-emerald-400';
  if (level > 20) return 'text-yellow-400';
  return 'text-red-400';
}

/** Battery icon based on level */
function BatteryIcon({ level, className }: { level: number; className?: string }) {
  const bars = level > 75 ? 4 : level > 50 ? 3 : level > 25 ? 2 : level > 10 ? 1 : 0;
  
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="7" width="18" height="10" rx="2" />
      <path d="M22 11v2" strokeLinecap="round" />
      {/* Battery bars */}
      {bars >= 1 && <rect x="4" y="9" width="3" height="6" fill="currentColor" stroke="none" />}
      {bars >= 2 && <rect x="8" y="9" width="3" height="6" fill="currentColor" stroke="none" />}
      {bars >= 3 && <rect x="12" y="9" width="3" height="6" fill="currentColor" stroke="none" />}
      {bars >= 4 && <rect x="16" y="9" width="2" height="6" fill="currentColor" stroke="none" />}
    </svg>
  );
}

export function EmergencyControls({ 
  className,
  pollInterval = 4000 
}: EmergencyControlsProps) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState<string | null>(null); // Which action is loading
  const [error, setError] = useState<string | null>(null);

  // Fetch drone status
  const fetchStatus = useCallback(async () => {
    try {
      const newStatus = await getDroneStatus();
      setStatus(newStatus);
      setError(null);
    } catch (err) {
      // Don't show error, just mark as disconnected
      setStatus(prev => prev ? { ...prev, drone: { ...prev.drone, connected: false } } : null);
    }
  }, []);

  // Poll status
  useEffect(() => {
    fetchStatus(); // Initial fetch
    
    const interval = setInterval(fetchStatus, pollInterval);
    return () => clearInterval(interval);
  }, [fetchStatus, pollInterval]);

  // Control handlers - IMMEDIATE, no confirmation
  const handleTakeoff = async () => {
    setIsLoading('takeoff');
    setError(null);
    try {
      await takeoff();
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Takeoff failed');
    } finally {
      setIsLoading(null);
    }
  };

  const handleLand = async () => {
    setIsLoading('land');
    setError(null);
    try {
      await land();
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Land failed');
    } finally {
      setIsLoading(null);
    }
  };

  const handleEmergencyStop = async () => {
    setIsLoading('stop');
    setError(null);
    try {
      await emergencyStop();
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stop failed');
    } finally {
      setIsLoading(null);
    }
  };

  const handleReturnHome = async () => {
    setIsLoading('home');
    setError(null);
    try {
      await returnHome();
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Return home failed');
    } finally {
      setIsLoading(null);
    }
  };

  const isFlying = status?.drone.flying ?? false;
  const isConnected = status?.drone.connected ?? false;
  const battery = status?.drone.battery ?? 0;
  const height = status?.drone.height ?? 0;

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Status indicators */}
      <div className="flex items-center gap-3 pr-3 border-r border-zinc-700/50">
        {/* Connection/Flying status */}
        <div className="flex items-center gap-1.5">
          <div className={cn(
            'w-2 h-2 rounded-full',
            !isConnected ? 'bg-zinc-600' :
            isFlying ? 'bg-emerald-400 animate-pulse' : 'bg-emerald-400'
          )} />
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider">
            {!isConnected ? 'Offline' : isFlying ? 'Flying' : 'Ready'}
          </span>
        </div>

        {/* Battery */}
        {isConnected && (
          <div className={cn('flex items-center gap-1', getBatteryColor(battery))}>
            <BatteryIcon level={battery} className="w-5 h-5" />
            <span className="text-xs font-mono">{battery}%</span>
          </div>
        )}

        {/* Height when flying */}
        {isFlying && height > 0 && (
          <div className="flex items-center gap-1 text-zinc-400">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M7 11l5-5m0 0l5 5m-5-5v12" />
            </svg>
            <span className="text-xs font-mono">{height}cm</span>
          </div>
        )}
      </div>

      {/* TAKEOFF button - show when connected but not flying */}
      {isConnected && !isFlying && (
        <button
          onClick={handleTakeoff}
          disabled={isLoading !== null}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-bold transition-all',
            'bg-emerald-600 text-white border-2 border-emerald-400 shadow-lg shadow-emerald-500/30 hover:bg-emerald-500',
            'disabled:opacity-30 disabled:cursor-not-allowed',
            isLoading === 'takeoff' && 'animate-pulse'
          )}
          title="TAKEOFF!"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" 
              d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
          <span>TAKEOFF</span>
        </button>
      )}

      {/* EMERGENCY LAND button - ALWAYS visible, NEVER disabled */}
      <button
        onClick={handleLand}
        disabled={isLoading === 'land'}
        className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-bold transition-all',
          'bg-red-600 text-white border-2 border-red-400 shadow-lg shadow-red-500/30 hover:bg-red-500',
          isLoading === 'land' && 'animate-pulse'
        )}
        title="EMERGENCY LAND NOW!"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" 
            d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
        <span>LAND</span>
      </button>

      {/* Other emergency buttons - only show when connected */}
      {isConnected && (
        <div className="flex items-center gap-1.5">
          {/* Return Home */}
          <button
            onClick={handleReturnHome}
            disabled={!isFlying || isLoading !== null}
            className={cn(
              'flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-all',
              'bg-blue-600/20 text-blue-400 border border-blue-500/30',
              'hover:bg-blue-600/30 hover:border-blue-500/50',
              'disabled:opacity-40 disabled:cursor-not-allowed',
              isLoading === 'home' && 'animate-pulse'
            )}
            title="Return to takeoff point and land"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            <span className="hidden sm:inline">HOME</span>
          </button>

          {/* Emergency Stop */}
          <button
            onClick={handleEmergencyStop}
            disabled={!isFlying || isLoading !== null}
            className={cn(
              'flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-all',
              'bg-orange-600/20 text-orange-400 border border-orange-500/30',
              'hover:bg-orange-600/30 hover:border-orange-500/50',
              'disabled:opacity-40 disabled:cursor-not-allowed',
              isLoading === 'stop' && 'animate-pulse'
            )}
            title="Stop all movement and hover"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
            <span className="hidden sm:inline">STOP</span>
          </button>
        </div>
      )}

      {/* Error toast */}
      {error && (
        <div className="absolute top-full right-0 mt-2 px-3 py-2 bg-red-900/90 border border-red-500/50 rounded-lg text-xs text-red-200 whitespace-nowrap">
          {error}
        </div>
      )}
    </div>
  );
}

export default EmergencyControls;
