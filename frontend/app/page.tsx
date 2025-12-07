/**
 * Main page - Captain Grok
 * Simplified: Voice-controlled drone interface focused on person search
 */

'use client';

import { RecordButton } from './components/RecordButton';
import { StatusIndicator } from './components/StatusIndicator';
import { VideoStream } from './components/VideoStream';
import { LiveExecution } from './components/LiveExecution';
import { FoundModal } from './components/FoundModal';
import { LoadingSpinner } from './components/LoadingSpinner';
import { ChatPanel } from './components/ChatPanel';
import { EmergencyControls } from './components/EmergencyControls';
import { TargetsPanel } from './components/TargetsPanel';
import { useAudioRecorder } from './hooks/useAudioRecorder';
import { useVideoStream } from './hooks/useVideoStream';
import { useCommandStream } from './hooks/useCommandStream';
import { useTargets } from './hooks/useTargets';
import { useTailing } from './hooks/useTailing';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';
import type { StatusMessage } from './types';
import { useEffect, useCallback, useState } from 'react';
import { StopCircle, UserRoundSearch, X } from 'lucide-react';
import { emergencyStop } from '@/lib/api-client';

export default function Home(): React.ReactElement {
  const { streamUrl, setStreamUrl } = useVideoStream();
  
  const {
    currentExecution,
    foundTarget,
    showFoundModal,
    setShowFoundModal,
    executeCommand,
    isExecuting,
    voiceEnabled,
    setVoiceEnabled,
    voiceAvailable,
    chatMessages,
    isThinking
  } = useCommandStream();
  
  // Targets state for facial recognition search
  const targetsState = useTargets();
  
  // Tailing state
  const tailing = useTailing();
  
  // Track target ID from found results for tailing
  const [foundTargetId, setFoundTargetId] = useState<string | null>(null);
  
  // Handle sending a command (from chat input or voice)
  const handleSendCommand = useCallback(async (text: string) => {
    await executeCommand(text);
  }, [executeCommand]);
  
  const {
    isRecording,
    recordingState,
    transcript,
    error,
    startRecording,
    stopRecording,
  } = useAudioRecorder(undefined, handleSendCommand);

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
  
  // Handle tailing from found modal
  const handleTailTarget = useCallback(async (targetId: string) => {
    try {
      await tailing.startTailing(targetId);
      toast.success(`Now following ${tailing.targetName || 'target'}`);
    } catch (err) {
      toast.error('Failed to start following');
    }
  }, [tailing]);
  
  // Stop tailing
  const handleStopTailing = useCallback(async () => {
    try {
      await tailing.stopTailing();
      toast.info('Stopped following');
    } catch (err) {
      toast.error('Failed to stop');
    }
  }, [tailing]);
  
  // Emergency stop handler
  const handleEmergencyStop = useCallback(async () => {
    try {
      await emergencyStop();
      if (tailing.active) {
        await tailing.stopTailing();
      }
      toast.warning('STOPPED');
    } catch (err) {
      toast.error('Stop failed');
    }
  }, [tailing]);
  
  // Update found target ID when a target is found
  useEffect(() => {
    if (foundTarget && currentExecution?.foundTarget) {
      // Try to get target ID from execution data
      const execData = currentExecution.toolExecutions.find(
        t => t.data?.target_id
      );
      if (execData?.data?.target_id) {
        setFoundTargetId(execData.data.target_id as string);
      }
    }
  }, [foundTarget, currentExecution]);

  const getStatusMessage = (): StatusMessage => {
    if (error) {
      return { text: error, type: 'error' };
    }
    if (tailing.active) {
      return { text: `Following ${tailing.targetName}`, type: 'success' };
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
    <main className="h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      <div className="h-full flex flex-col">
        {/* Header */}
        <header className="flex-shrink-0 px-4 py-2 border-b border-zinc-800/50 bg-zinc-900/50">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-100">
                Captain Grok
              </h1>
              <span className="text-xs text-zinc-600 hidden md:inline">
                Search & Rescue Drone
              </span>
            </div>
            
            {/* Emergency Controls + Voice toggle */}
            <div className="flex items-center gap-3 relative">
              {/* Emergency Controls */}
              <EmergencyControls pollInterval={4000} />
              
              {/* Voice toggle */}
              {voiceAvailable && (
                <button
                  onClick={() => setVoiceEnabled(!voiceEnabled)}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium transition-all ${
                    voiceEnabled
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-zinc-800/50 text-zinc-500 border border-zinc-700/50'
                  }`}
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    {voiceEnabled ? (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                    ) : (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15zm7.414-9l6 6m0-6l-6 6" />
                    )}
                  </svg>
                  <span className="hidden sm:inline">{voiceEnabled ? 'ON' : 'OFF'}</span>
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex-1 min-h-0 flex overflow-hidden">
          {/* Left Panel - Chat Feed */}
          <div className="w-80 max-w-80 flex-shrink-0 border-r border-zinc-800/50 hidden lg:flex flex-col overflow-hidden">
            <ChatPanel 
              messages={chatMessages}
              isThinking={isThinking}
              onSendMessage={handleSendCommand}
              className="h-full"
            />
          </div>

          {/* Center - Video + Controls */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {/* Video Feed */}
            <div className="flex-1 min-h-0 relative bg-black">
              <VideoStream streamUrl={streamUrl} className="h-full" />
              
              {/* Tailing indicator overlay */}
              {tailing.active && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20">
                  <div className="flex items-center gap-2 px-4 py-2 bg-green-500/90 rounded-full text-white text-sm font-medium shadow-lg">
                    <UserRoundSearch className="h-4 w-4" />
                    <span>Following: {tailing.targetName}</span>
                    <button
                      onClick={handleStopTailing}
                      className="ml-2 p-1 hover:bg-white/20 rounded-full transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
              
              {/* Overlay: Live Execution */}
              {currentExecution && (
                <div className="absolute bottom-4 left-4 right-4 z-10">
                  <LiveExecution execution={currentExecution} />
                </div>
              )}
              
              {/* Overlay: Loading */}
              {recordingState === 'processing' && !currentExecution && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
                  <LoadingSpinner text="Transcribing..." />
                </div>
              )}
              
              {/* Big STOP button - always visible when executing or tailing */}
              {(isExecuting || tailing.active) && (
                <button
                  onClick={handleEmergencyStop}
                  className="absolute bottom-20 right-4 z-30 p-4 bg-red-600 hover:bg-red-500 rounded-full shadow-lg transition-all hover:scale-105 active:scale-95"
                  title="Emergency Stop"
                >
                  <StopCircle className="h-8 w-8 text-white" />
                </button>
              )}
            </div>

            {/* Control Bar */}
            <div className="flex-shrink-0 px-4 py-3 border-t border-zinc-800/50 bg-zinc-900/80">
              <div className="max-w-xl mx-auto flex items-center justify-center gap-4">
                <StatusIndicator status={getStatusMessage()} />
                
                <RecordButton
                  isRecording={isRecording}
                  isProcessing={recordingState === 'processing' || isExecuting}
                  onClick={handleRecordClick}
                  size="md"
                />
                
                {transcript && !isExecuting && recordingState === 'complete' && (
                  <p className="text-xs text-zinc-600 max-w-[180px] truncate">
                    &ldquo;{transcript}&rdquo;
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Right Panel - Targets Only */}
          <div className="w-80 max-w-80 flex-shrink-0 border-l border-zinc-800/50 hidden lg:flex flex-col overflow-hidden">
            <div className="flex-shrink-0 px-4 py-2 border-b border-zinc-800 bg-zinc-900">
              <h2 className="text-sm font-medium text-zinc-300">
                Search Targets ({targetsState.stats?.total || 0})
              </h2>
            </div>
            <TargetsPanel 
              targetsState={targetsState}
              onTail={handleTailTarget}
              tailingTargetId={tailing.targetId}
            />
          </div>
        </div>
        
        {/* Mobile: Bottom tabs for Chat/Targets */}
        <div className="lg:hidden flex-shrink-0 border-t border-zinc-800/50">
          <MobileBottomTabs
            chatMessages={chatMessages}
            isThinking={isThinking}
            onSendMessage={handleSendCommand}
            targetsState={targetsState}
            onTail={handleTailTarget}
            tailingTargetId={tailing.targetId}
          />
        </div>
      </div>

      {/* Found Modal */}
      <FoundModal
        target={foundTarget}
        open={showFoundModal}
        onOpenChange={setShowFoundModal}
        onTail={handleTailTarget}
        targetId={foundTargetId || undefined}
      />
      
      {/* Toast notifications */}
      <Toaster position="top-right" richColors />
    </main>
  );
}

/** Mobile bottom tabs for Chat and Targets */
function MobileBottomTabs({
  chatMessages,
  isThinking,
  onSendMessage,
  targetsState,
  onTail,
  tailingTargetId
}: {
  chatMessages: ReturnType<typeof useCommandStream>['chatMessages'];
  isThinking: boolean;
  onSendMessage: (message: string) => void;
  targetsState: ReturnType<typeof useTargets>;
  onTail: (targetId: string) => void;
  tailingTargetId: string | null;
}) {
  const [activeTab, setActiveTab] = useState<'chat' | 'targets'>('chat');
  
  return (
    <div className="h-72">
      {/* Tab buttons */}
      <div className="flex border-b border-zinc-800/50 flex-shrink-0">
        <button
          onClick={() => setActiveTab('chat')}
          className={`flex-1 px-4 py-2 text-xs font-medium transition-colors ${
            activeTab === 'chat'
              ? 'text-emerald-400 border-b-2 border-emerald-400'
              : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Feed ({chatMessages.length})
        </button>
        <button
          onClick={() => setActiveTab('targets')}
          className={`flex-1 px-4 py-2 text-xs font-medium transition-colors ${
            activeTab === 'targets'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Targets ({targetsState.stats?.total || 0})
        </button>
      </div>
      
      {/* Tab content */}
      <div className="h-[calc(100%-37px)] overflow-hidden">
        {activeTab === 'chat' ? (
          <ChatPanel
            messages={chatMessages}
            isThinking={isThinking}
            onSendMessage={onSendMessage}
            className="h-full"
          />
        ) : (
          <TargetsPanel 
            targetsState={targetsState}
            onTail={onTail}
            tailingTargetId={tailingTargetId}
          />
        )}
      </div>
    </div>
  );
}
