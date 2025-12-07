/**
 * Main page - Voice Task Assistant
 * Real-time drone command execution with streaming updates
 */

'use client';

import { Card } from '@/components/ui/card';
import { RecordButton } from './components/RecordButton';
import { StatusIndicator } from './components/StatusIndicator';
import { VideoStream } from './components/VideoStream';
import { LiveExecution } from './components/LiveExecution';
import { CommandTimeline } from './components/CommandTimeline';
import { FoundModal } from './components/FoundModal';
import { LoadingSpinner } from './components/LoadingSpinner';
import { useAudioRecorder } from './hooks/useAudioRecorder';
import { useVideoStream } from './hooks/useVideoStream';
import { useCommandStream } from './hooks/useCommandStream';
import type { StatusMessage } from './types';
import { useEffect, useCallback } from 'react';

export default function Home(): React.ReactElement {
  const { streamUrl, setStreamUrl } = useVideoStream();
  
  const {
    history,
    currentExecution,
    foundTarget,
    showFoundModal,
    setShowFoundModal,
    executeCommand,
    isExecuting,
    viewFoundTarget
  } = useCommandStream();
  
  // Wrap executeCommand to work with audio recorder
  const handleTranscriptReady = useCallback(async (text: string) => {
    await executeCommand(text);
  }, [executeCommand]);
  
  const {
    isRecording,
    recordingState,
    transcript,
    error,
    startRecording,
    stopRecording,
  } = useAudioRecorder(undefined, handleTranscriptReady);

  // Set the video stream URL from environment variable on mount
  useEffect(() => {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (backendUrl) {
      setStreamUrl(`${backendUrl}/video/stream`);
    }
  }, [setStreamUrl]);

  const handleRecordClick = (): void => {
    if (isRecording) {
      void stopRecording();
    } else {
      void startRecording();
    }
  };

  const getStatusMessage = (): StatusMessage => {
    if (error) {
      return { text: error, type: 'error' };
    }
    
    if (isExecuting) {
      return { text: 'Executing command...', type: 'processing' };
    }
    
    switch (recordingState) {
      case 'recording':
        return { text: 'Recording...', type: 'recording' };
      case 'processing':
        return { text: 'Processing...', type: 'processing' };
      case 'complete':
        return { text: 'Ready for next command', type: 'success' };
      case 'error':
        return { text: 'Error occurred', type: 'error' };
      default:
        return { text: 'Ready to record', type: 'idle' };
    }
  };
  


  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 py-6 px-4 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-48 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-700" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-pink-500/5 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto max-w-7xl relative z-10 space-y-6">
        {/* Header Card */}
        <Card className="bg-slate-900/80 border-slate-700/50 backdrop-blur-xl shadow-2xl shadow-indigo-900/20 overflow-hidden">
          {/* Gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-purple-500/5 pointer-events-none" />
          
          <div className="p-6 md:p-8 relative z-10">
            {/* Header */}
            <div className="text-center mb-8">
              <h1 className="text-4xl md:text-5xl font-extrabold mb-3 bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent drop-shadow-2xl">
                Captain Grok
              </h1>
              <p className="text-slate-400 text-lg">
                Voice-controlled drone pilot powered by Grok AI
              </p>
              <div className="mt-3 flex items-center justify-center gap-2">
                <div className="h-1 w-12 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full" />
                <div className="h-1 w-1 bg-purple-500 rounded-full" />
                <div className="h-1 w-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full" />
              </div>
            </div>

            {/* Main Content: Recording + Stream */}
            <div className="flex flex-col lg:flex-row gap-6 items-start">
              {/* Recording Section */}
              <div className="flex flex-col items-center justify-center gap-4 lg:min-h-[300px] w-full lg:w-auto">
                <RecordButton
                  isRecording={isRecording}
                  isProcessing={recordingState === 'processing' || isExecuting}
                  onClick={handleRecordClick}
                />
                <StatusIndicator status={getStatusMessage()} />
                
                {/* Show transcript when recording is done */}
                {transcript && !isExecuting && recordingState === 'complete' && (
                  <div className="text-center max-w-xs">
                    <p className="text-xs text-slate-500 mb-1">Last command:</p>
                    <p className="text-sm text-slate-400 italic">&ldquo;{transcript}&rdquo;</p>
                  </div>
                )}
              </div>

              {/* Stream Section */}
              <VideoStream streamUrl={streamUrl} className="w-full lg:flex-1" />
            </div>
          </div>
        </Card>

        {/* Processing Spinner - shown when transcribing */}
        {recordingState === 'processing' && !currentExecution && (
          <Card className="bg-slate-900/80 border-slate-700/50 backdrop-blur-xl">
            <LoadingSpinner text="Transcribing audio..." />
          </Card>
        )}

        {/* Live Execution Panel - shown during command execution */}
        {currentExecution && (
          <LiveExecution execution={currentExecution} />
        )}

        {/* Command History */}
        <CommandTimeline 
          history={history} 
          onViewFound={viewFoundTarget}
        />
      </div>

      {/* Found Modal - auto-opens when target is found */}
      <FoundModal
        target={foundTarget}
        open={showFoundModal}
        onOpenChange={setShowFoundModal}
      />
    </main>
  );
}
