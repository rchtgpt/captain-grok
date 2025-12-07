/**
 * Found Modal - Shows when a target is found with option to tail them
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
import { Target, X, UserRoundSearch, Check } from 'lucide-react';
import type { FoundTarget } from '@/app/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';

interface FoundModalProps {
  target: FoundTarget | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTail?: (targetId: string) => void;  // Called when user wants to tail
  targetId?: string;  // Target ID for tailing
}

export function FoundModal({ 
  target, 
  open, 
  onOpenChange, 
  onTail,
  targetId 
}: FoundModalProps): React.ReactElement {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [isTailing, setIsTailing] = useState(false);
  
  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
  }, [target?.imageUrl]);
  
  if (!target) return <></>;
  
  const imageUrl = target.imageUrl ? `${BACKEND_URL}${target.imageUrl}` : null;
  
  const handleTail = () => {
    if (onTail && targetId) {
      setIsTailing(true);
      onTail(targetId);
      // Close modal after a brief delay
      setTimeout(() => {
        onOpenChange(false);
        setIsTailing(false);
      }, 500);
    }
  };
  
  // Parse confidence - could be string like "high" or number
  const confidenceDisplay = typeof target.confidence === 'number' 
    ? `${Math.round(target.confidence * 100)}%`
    : target.confidence;
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg bg-zinc-950 border-zinc-800 p-0 overflow-hidden">
        <DialogHeader className="p-6 pb-0">
          <DialogTitle className="flex items-center gap-2 text-lg font-medium text-zinc-100">
            <Target className="h-4 w-4 text-green-500" />
            Target Found
          </DialogTitle>
        </DialogHeader>
        
        <div className="p-6 space-y-4">
          {/* Image */}
          {imageUrl && !imageError ? (
            <div className="relative aspect-video bg-zinc-900 rounded-lg overflow-hidden border border-green-500/30">
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
              {/* Found badge */}
              <div className="absolute top-2 right-2 px-2 py-1 bg-green-500/90 rounded text-xs font-medium text-white">
                FOUND
              </div>
            </div>
          ) : (
            <div className="aspect-video bg-zinc-900 rounded-lg flex items-center justify-center border border-green-500/30">
              <Target className="h-8 w-8 text-green-500/50" />
            </div>
          )}
          
          {/* Info */}
          <div className="space-y-3">
            <div>
              <p className="text-xs text-zinc-600 mb-1">Target</p>
              <p className="text-lg font-medium text-zinc-100">{target.target}</p>
            </div>
            
            <div className="flex gap-6">
              {target.angle !== undefined && (
                <div>
                  <p className="text-xs text-zinc-600 mb-1">Direction</p>
                  <p className="text-sm text-zinc-300">{target.angle}° from start</p>
                </div>
              )}
              <div>
                <p className="text-xs text-zinc-600 mb-1">Confidence</p>
                <p className={cn(
                  "text-sm font-medium",
                  target.confidence === 'high' || (typeof target.confidence === 'number' && target.confidence > 0.7) 
                    ? "text-green-400" 
                    : "text-yellow-400"
                )}>
                  {confidenceDisplay}
                </p>
              </div>
            </div>
            
            {target.description && (
              <div>
                <p className="text-xs text-zinc-600 mb-1">Description</p>
                <p className="text-sm text-zinc-400">{target.description}</p>
              </div>
            )}
          </div>
          
          {/* Action buttons */}
          <div className="flex gap-3 pt-2">
            {onTail && targetId && (
              <button
                onClick={handleTail}
                disabled={isTailing}
                className={cn(
                  "flex-1 py-2.5 flex items-center justify-center gap-2 text-sm font-medium rounded-lg transition-all",
                  isTailing 
                    ? "bg-green-600 text-white"
                    : "bg-green-500 hover:bg-green-400 text-white"
                )}
              >
                {isTailing ? (
                  <>
                    <Check className="h-4 w-4" />
                    Starting...
                  </>
                ) : (
                  <>
                    <UserRoundSearch className="h-4 w-4" />
                    Tail
                  </>
                )}
              </button>
            )}
            <button
              onClick={() => onOpenChange(false)}
              className={cn(
                "py-2.5 text-sm font-medium rounded-lg transition-colors",
                onTail && targetId 
                  ? "flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
                  : "w-full bg-zinc-100 hover:bg-white text-zinc-900"
              )}
            >
              Done
            </button>
          </div>
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
