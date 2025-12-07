/**
 * Transcript display component
 */

'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TranscriptDisplayProps {
  transcript: string;
  className?: string;
}

export function TranscriptDisplay({ transcript, className }: TranscriptDisplayProps): React.ReactElement {
  return (
    <Card className={cn('bg-gradient-to-br from-slate-900/70 to-slate-950/70 border-slate-600/50 backdrop-blur-md shadow-xl animate-in fade-in duration-700', className)}>
      <CardHeader>
        <CardTitle className="text-xl font-bold text-slate-200 flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-emerald-400" />
          Transcription
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="bg-gradient-to-br from-slate-950 to-slate-900 border-2 border-slate-700/50 rounded-xl p-6 min-h-[120px] shadow-inner">
          <p className="text-slate-100 text-lg leading-relaxed whitespace-pre-wrap break-words">
            {transcript}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
