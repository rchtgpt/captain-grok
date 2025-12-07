/**
 * Found Modal
 * Beautiful celebratory modal when search finds target
 * Auto-opens with sparkle animations and chime sound
 */

'use client';

import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  Target,
  Compass,
  BarChart3,
  Sparkles,
  PartyPopper,
  X,
} from 'lucide-react';
import type { FoundTarget } from '@/app/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';

interface FoundModalProps {
  target: FoundTarget | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Confetti particle component
function ConfettiParticle({ delay, left }: { delay: number; left: number }) {
  const colors = ['bg-emerald-400', 'bg-teal-400', 'bg-cyan-400', 'bg-indigo-400', 'bg-purple-400', 'bg-pink-400', 'bg-yellow-400'];
  const color = colors[Math.floor(Math.random() * colors.length)];
  
  return (
    <div
      className={cn(
        'absolute w-2 h-2 rounded-full animate-confetti',
        color
      )}
      style={{
        left: `${left}%`,
        animationDelay: `${delay}ms`,
        top: '-10px'
      }}
    />
  );
}

// Sparkle animation component
function SparkleEffect() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Multiple sparkles */}
      {[...Array(12)].map((_, i) => (
        <Sparkles
          key={i}
          className={cn(
            'absolute text-yellow-400 animate-sparkle',
            i % 3 === 0 ? 'h-4 w-4' : i % 3 === 1 ? 'h-3 w-3' : 'h-5 w-5'
          )}
          style={{
            left: `${10 + (i * 7) % 80}%`,
            top: `${5 + (i * 11) % 30}%`,
            animationDelay: `${i * 150}ms`,
          }}
        />
      ))}
    </div>
  );
}

function getConfidenceColor(confidence: string): string {
  switch (confidence.toLowerCase()) {
    case 'high':
      return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50';
    case 'medium':
      return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50';
    case 'low':
      return 'bg-red-500/20 text-red-300 border-red-500/50';
    default:
      return 'bg-slate-500/20 text-slate-300 border-slate-500/50';
  }
}

export function FoundModal({ target, open, onOpenChange }: FoundModalProps): React.ReactElement {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  
  // Reset image state when target changes
  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
  }, [target?.imageUrl]);
  
  if (!target) return <></>;
  
  const imageUrl = target.imageUrl ? `${BACKEND_URL}${target.imageUrl}` : null;
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border-emerald-500/30 shadow-2xl shadow-emerald-500/20 overflow-hidden">
        {/* Animated background glow */}
        <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-cyan-500/10 animate-pulse" />
        
        {/* Sparkle effects */}
        <SparkleEffect />
        
        {/* Confetti particles */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {[...Array(20)].map((_, i) => (
            <ConfettiParticle key={i} delay={i * 100} left={5 + (i * 5) % 90} />
          ))}
        </div>
        
        <DialogHeader className="relative z-10">
          <DialogTitle className="flex items-center justify-center gap-3 text-3xl font-bold">
            <PartyPopper className="h-8 w-8 text-yellow-400 animate-bounce" />
            <span className="bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 bg-clip-text text-transparent animate-pulse">
              TARGET FOUND!
            </span>
            <PartyPopper className="h-8 w-8 text-yellow-400 animate-bounce" style={{ animationDelay: '100ms' }} />
          </DialogTitle>
        </DialogHeader>
        
        <div className="relative z-10 space-y-6 mt-4">
          {/* Image Display */}
          {imageUrl && !imageError ? (
            <div className="relative rounded-xl overflow-hidden border-2 border-emerald-500/30 shadow-lg shadow-emerald-500/10">
              {/* Loading skeleton */}
              {!imageLoaded && (
                <div className="absolute inset-0 bg-slate-800 animate-pulse flex items-center justify-center">
                  <div className="text-slate-600">Loading image...</div>
                </div>
              )}
              
              {/* Actual image */}
              <img
                src={imageUrl}
                alt="Found target"
                className={cn(
                  'w-full h-auto max-h-[400px] object-contain bg-slate-900 transition-opacity duration-300',
                  imageLoaded ? 'opacity-100' : 'opacity-0'
                )}
                onLoad={() => setImageLoaded(true)}
                onError={() => setImageError(true)}
              />
              
              {/* Image overlay gradient */}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-900/50 via-transparent to-transparent pointer-events-none" />
            </div>
          ) : imageError ? (
            <div className="rounded-xl border-2 border-dashed border-slate-700 p-8 text-center">
              <Target className="h-12 w-12 text-slate-600 mx-auto mb-2" />
              <p className="text-slate-500">Image not available</p>
            </div>
          ) : (
            <div className="rounded-xl border-2 border-dashed border-slate-700 p-8 text-center">
              <Target className="h-12 w-12 text-emerald-500 mx-auto mb-2" />
              <p className="text-slate-400">Target confirmed</p>
            </div>
          )}
          
          {/* Target Info */}
          <div className="space-y-4">
            {/* Target name */}
            <div className="flex items-start gap-3 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50">
              <Target className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs text-slate-500 mb-1">Looking for</p>
                <p className="text-lg font-semibold text-slate-100">{target.target}</p>
              </div>
            </div>
            
            {/* Stats row */}
            <div className="grid grid-cols-2 gap-4">
              {/* Angle */}
              {target.angle !== undefined && (
                <div className="flex items-center gap-3 p-3 bg-slate-800/30 rounded-lg border border-slate-700/30">
                  <Compass className="h-5 w-5 text-indigo-400" />
                  <div>
                    <p className="text-xs text-slate-500">Found at</p>
                    <p className="text-slate-200 font-medium">{target.angle}° rotation</p>
                  </div>
                </div>
              )}
              
              {/* Confidence */}
              <div className="flex items-center gap-3 p-3 bg-slate-800/30 rounded-lg border border-slate-700/30">
                <BarChart3 className="h-5 w-5 text-teal-400" />
                <div>
                  <p className="text-xs text-slate-500">Confidence</p>
                  <Badge className={cn('mt-1', getConfidenceColor(target.confidence))}>
                    {target.confidence.toUpperCase()}
                  </Badge>
                </div>
              </div>
            </div>
            
            {/* Description */}
            {target.description && (
              <div className="p-4 bg-slate-800/30 rounded-xl border border-slate-700/30">
                <p className="text-xs text-slate-500 mb-2">Description</p>
                <p className="text-slate-300 text-sm leading-relaxed italic">
                  &ldquo;{target.description}&rdquo;
                </p>
              </div>
            )}
          </div>
          
          {/* Close button */}
          <Button
            onClick={() => onOpenChange(false)}
            className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-semibold py-6 text-lg shadow-lg shadow-emerald-500/20"
          >
            <Sparkles className="h-5 w-5 mr-2" />
            Awesome!
          </Button>
        </div>
        
        {/* Close X button */}
        <button
          onClick={() => onOpenChange(false)}
          className="absolute top-4 right-4 p-1 rounded-full bg-slate-800/50 hover:bg-slate-700/50 transition-colors z-20"
        >
          <X className="h-4 w-4 text-slate-400" />
        </button>
      </DialogContent>
    </Dialog>
  );
}
