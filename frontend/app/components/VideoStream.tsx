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
    <div className={cn('w-full', className)}>
      <div className="relative aspect-video bg-zinc-900 rounded-lg overflow-hidden border border-zinc-800">
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
            <Video className="h-8 w-8 mb-2" />
            <p className="text-xs">No video feed</p>
          </div>
        )}

        {/* Error State */}
        {hasError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-600">
            <Video className="h-8 w-8 mb-2" />
            <p className="text-xs">Connection failed</p>
          </div>
        )}

        {/* Loading State */}
        {streamUrl && !isLoaded && !hasError && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="h-6 w-6 border-2 border-zinc-700 border-t-zinc-400 rounded-full animate-spin" />
          </div>
        )}
      </div>
    </div>
  );
}
