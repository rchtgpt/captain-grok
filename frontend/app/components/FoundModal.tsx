/**
 * Found Modal - Minimalist but celebratory design
 */

'use client';

import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { Target, X } from 'lucide-react';
import type { FoundTarget } from '@/app/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';

interface FoundModalProps {
  target: FoundTarget | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function FoundModal({ target, open, onOpenChange }: FoundModalProps): React.ReactElement {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  
  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
  }, [target?.imageUrl]);
  
  if (!target) return <></>;
  
  const imageUrl = target.imageUrl ? `${BACKEND_URL}${target.imageUrl}` : null;
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg bg-zinc-950 border-zinc-800 p-0 overflow-hidden">
        <DialogHeader className="p-6 pb-0">
          <DialogTitle className="flex items-center gap-2 text-lg font-medium text-zinc-100">
            <Target className="h-4 w-4" />
            Target Found
          </DialogTitle>
        </DialogHeader>
        
        <div className="p-6 space-y-4">
          {/* Image */}
          {imageUrl && !imageError ? (
            <div className="relative aspect-video bg-zinc-900 rounded-lg overflow-hidden">
              {!imageLoaded && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-5 w-5 border-2 border-zinc-700 border-t-zinc-400 rounded-full animate-spin" />
                </div>
              )}
              <img
                src={imageUrl}
                alt="Found target"
                className={cn(
                  'w-full h-full object-contain transition-opacity duration-200',
                  imageLoaded ? 'opacity-100' : 'opacity-0'
                )}
                onLoad={() => setImageLoaded(true)}
                onError={() => setImageError(true)}
              />
            </div>
          ) : (
            <div className="aspect-video bg-zinc-900 rounded-lg flex items-center justify-center">
              <Target className="h-8 w-8 text-zinc-700" />
            </div>
          )}
          
          {/* Info */}
          <div className="space-y-3">
            <div>
              <p className="text-xs text-zinc-600 mb-1">Target</p>
              <p className="text-sm text-zinc-200">{target.target}</p>
            </div>
            
            <div className="flex gap-6">
              {target.angle !== undefined && (
                <div>
                  <p className="text-xs text-zinc-600 mb-1">Angle</p>
                  <p className="text-sm text-zinc-300">{target.angle}°</p>
                </div>
              )}
              <div>
                <p className="text-xs text-zinc-600 mb-1">Confidence</p>
                <p className="text-sm text-zinc-300 capitalize">{target.confidence}</p>
              </div>
            </div>
            
            {target.description && (
              <div>
                <p className="text-xs text-zinc-600 mb-1">Description</p>
                <p className="text-sm text-zinc-400">{target.description}</p>
              </div>
            )}
          </div>
          
          {/* Close button */}
          <button
            onClick={() => onOpenChange(false)}
            className="w-full py-2.5 bg-zinc-100 hover:bg-white text-zinc-900 text-sm font-medium rounded-lg transition-colors"
          >
            Done
          </button>
        </div>
        
        {/* Close X */}
        <button
          onClick={() => onOpenChange(false)}
          className="absolute top-4 right-4 p-1.5 rounded-md hover:bg-zinc-800 transition-colors"
        >
          <X className="h-4 w-4 text-zinc-500" />
        </button>
      </DialogContent>
    </Dialog>
  );
}
