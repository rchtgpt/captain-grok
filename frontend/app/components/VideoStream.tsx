/**
 * Video stream component for MJPEG display
 */

'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Monitor, AlertCircle } from 'lucide-react';
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
    <Card className={cn('flex-1 bg-gradient-to-br from-slate-900/70 to-slate-950/70 border-slate-600/50 backdrop-blur-md shadow-xl', className)}>
      <CardHeader>
        <CardTitle className="text-xl font-bold text-slate-200 flex items-center gap-2">
          <Monitor className="h-5 w-5 text-indigo-400" />
          Live Stream
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative w-full aspect-video bg-gradient-to-br from-slate-950 to-slate-900 rounded-xl border-2 border-slate-700/50 overflow-hidden flex items-center justify-center shadow-inner">
          {/* Stream Image */}
          {streamUrl && !hasError && (
            <img
              src={streamUrl}
              alt="MJPEG Stream"
              className={cn(
                'w-full h-full object-contain transition-opacity duration-300',
                isLoaded ? 'opacity-100' : 'opacity-0'
              )}
              onLoad={handleLoad}
              onError={handleError}
            />
          )}

          {/* Placeholder */}
          {!streamUrl && !hasError && (
            <div className="flex flex-col items-center gap-4 text-slate-400">
              <div className="relative">
                <Monitor className="h-16 w-16 text-indigo-400/50" />
                <div className="absolute inset-0 h-16 w-16 bg-indigo-500/20 rounded-lg blur-xl" />
              </div>
              <p className="text-sm font-medium">Stream will appear here when available</p>
            </div>
          )}

          {/* Error State */}
          {hasError && (
            <div className="flex flex-col items-center gap-4 text-slate-500">
              <AlertCircle className="h-12 w-12 opacity-50 text-red-500" />
              <p className="text-sm text-red-400">Unable to load stream</p>
            </div>
          )}

          {/* Loading State */}
          {streamUrl && !isLoaded && !hasError && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/50 backdrop-blur-sm">
              <div className="relative">
                <div className="h-12 w-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                <div className="absolute inset-0 h-12 w-12 border-4 border-purple-500/30 border-t-transparent rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1s' }} />
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
