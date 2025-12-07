/**
 * Main page - Captain Grok
 * Minimalist voice-controlled drone interface
 */

'use client';

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
    viewFoundTarget,
    voiceEnabled,
    setVoiceEnabled,
    voiceAvailable
  } = useCommandStream();
  
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
      return { text: 'Executing...', type: 'processing' };
    }
    switch (recordingState) {
      case 'recording':
        return { text: 'Listening...', type: 'recording' };
      case 'processing':
        return { text: 'Processing...', type: 'processing' };
      case 'complete':
        return { text: 'Ready', type: 'success' };
      case 'error':
        return { text: 'Error', type: 'error' };
      default:
        return { text: 'Tap to speak', type: 'idle' };
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <header className="text-center space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-100">
            Captain Grok
          </h1>
          <p className="text-sm text-zinc-500">
            Voice-controlled drone pilot
          </p>
        </header>

        {/* Main Interface */}
        <div className="grid lg:grid-cols-[320px_1fr] gap-8 items-start">
          {/* Control Panel */}
          <div className="flex flex-col items-center space-y-6">
            <RecordButton
              isRecording={isRecording}
              isProcessing={recordingState === 'processing' || isExecuting}
              onClick={handleRecordClick}
            />
            <StatusIndicator status={getStatusMessage()} />
            
            {transcript && !isExecuting && recordingState === 'complete' && (
              <p className="text-xs text-zinc-600 text-center max-w-[240px]">
                &ldquo;{transcript}&rdquo;
              </p>
            )}
            
            {/* Voice Narration Toggle */}
            {voiceAvailable && (
              <button
                onClick={() => setVoiceEnabled(!voiceEnabled)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  voiceEnabled
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-zinc-800/50 text-zinc-500 border border-zinc-700/50'
                }`}
                title={voiceEnabled ? 'Voice narration ON' : 'Voice narration OFF'}
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  {voiceEnabled ? (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
                    />
                  ) : (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15zm7.414-9l6 6m0-6l-6 6"
                    />
                  )}
                </svg>
                {voiceEnabled ? 'Voice ON' : 'Voice OFF'}
              </button>
            )}
          </div>

          {/* Video Feed */}
          <VideoStream streamUrl={streamUrl} />
        </div>

        {/* Loading State */}
        {recordingState === 'processing' && !currentExecution && (
          <LoadingSpinner text="Transcribing..." />
        )}

        {/* Live Execution */}
        {currentExecution && (
          <LiveExecution execution={currentExecution} />
        )}

        {/* History */}
        <CommandTimeline 
          history={history} 
          onViewFound={viewFoundTarget}
        />
      </div>

      {/* Found Modal */}
      <FoundModal
        target={foundTarget}
        open={showFoundModal}
        onOpenChange={setShowFoundModal}
      />
    </main>
  );
}
