/**
 * Video stream component - Minimalist design
 */

'use client';

import { Video } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';

interface VideoStreamProps {
  streamUrl: string | null;
  className?: string;
}

export function VideoStream({ streamUrl, className }: VideoStreamProps): React.ReactElement {
  const [hasError, setHasError] = useState<boolean>(false);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);

  const handleLoad = (): void => {
    setIsLoaded(true);
    setHasError(false);
  };

  const handleError = (): void => {
    setHasError(true);
    setIsLoaded(false);
  };

  return (
    <div className={cn('w-full h-full', className)}>
      <div className="relative w-full h-full bg-zinc-900 overflow-hidden">
        {/* Stream Image */}
        {streamUrl && !hasError && (
          <img
            src={streamUrl}
            alt="Drone Feed"
            className={cn(
              'w-full h-full object-contain transition-opacity duration-200',
              isLoaded ? 'opacity-100' : 'opacity-0'
            )}
            onLoad={handleLoad}
            onError={handleError}
          />
        )}

        {/* Placeholder */}
        {!streamUrl && !hasError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-700">
            <Video className="h-12 w-12 mb-3" />
            <p className="text-sm">No video feed</p>
            <p className="text-xs text-zinc-600 mt-1">Waiting for drone connection...</p>
          </div>
        )}

        {/* Error State */}
        {hasError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-600">
            <Video className="h-12 w-12 mb-3" />
            <p className="text-sm">Connection failed</p>
            <p className="text-xs text-zinc-700 mt-1">Check drone is powered on</p>
          </div>
        )}

        {/* Loading State */}
        {streamUrl && !isLoaded && !hasError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <div className="h-8 w-8 border-2 border-zinc-700 border-t-zinc-400 rounded-full animate-spin mb-3" />
            <p className="text-xs text-zinc-600">Connecting to drone...</p>
          </div>
        )}
        
        {/* Overlay gradient for readability */}
        <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-zinc-950/80 to-transparent pointer-events-none" />
      </div>
    </div>
  );
}
