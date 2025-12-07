/**
 * Main page - Voice Task Assistant
 */

'use client';

import { Card } from '@/components/ui/card';
import { RecordButton } from './components/RecordButton';
import { StatusIndicator } from './components/StatusIndicator';
import { VideoStream } from './components/VideoStream';
import { TranscriptDisplay } from './components/TranscriptDisplay';
import { LoadingSpinner } from './components/LoadingSpinner';
import { useAudioRecorder } from './hooks/useAudioRecorder';
import { useVideoStream } from './hooks/useVideoStream';
import type { StatusMessage } from './types';

export default function Home(): React.ReactElement {
  const { streamUrl, setStreamUrl } = useVideoStream();
  
  const {
    isRecording,
    recordingState,
    transcript,
    error,
    startRecording,
    stopRecording,
  } = useAudioRecorder(setStreamUrl);

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
    
    switch (recordingState) {
      case 'recording':
        return { text: 'Recording...', type: 'recording' };
      case 'processing':
        return { text: 'Processing...', type: 'processing' };
      case 'complete':
        return { text: 'Transcription complete', type: 'success' };
      case 'error':
        return { text: 'Error occurred', type: 'error' };
      default:
        return { text: 'Ready to record', type: 'idle' };
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 py-8 px-4 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-48 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-700" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-pink-500/5 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto max-w-7xl relative z-10">
        <Card className="bg-slate-900/80 border-slate-700/50 backdrop-blur-xl shadow-2xl shadow-indigo-900/20 overflow-hidden">
          {/* Gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-purple-500/5 pointer-events-none" />
          
          <div className="p-8 md:p-12 relative z-10">
            {/* Header */}
            <div className="text-center mb-12">
              <h1 className="text-5xl md:text-7xl font-extrabold mb-4 bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent drop-shadow-2xl animate-in fade-in duration-1000">
                Voice Task Assistant
              </h1>
              <p className="text-slate-300 text-xl font-medium">
                Describe your task in natural language
              </p>
              <div className="mt-4 flex items-center justify-center gap-2">
                <div className="h-1 w-12 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full" />
                <div className="h-1 w-1 bg-purple-500 rounded-full" />
                <div className="h-1 w-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full" />
              </div>
            </div>

            {/* Loading Section */}
            {recordingState === 'processing' && (
              <div className="border-t border-slate-700 pt-8">
                <LoadingSpinner />
              </div>
            )}

            {/* Main Content: Recording + Stream */}
            <div className="flex flex-col lg:flex-row gap-8 items-center border-t border-slate-700 pt-8">
              {/* Recording Section */}
              <div className="flex flex-col items-center justify-center gap-6 lg:min-h-[400px]">
                <RecordButton
                  isRecording={isRecording}
                  isProcessing={recordingState === 'processing'}
                  onClick={handleRecordClick}
                />
                <StatusIndicator status={getStatusMessage()} />
              </div>

              {/* Stream Section */}
              <VideoStream streamUrl={streamUrl} className="w-full lg:flex-1" />
            </div>

            {/* Transcript Section */}
            {transcript && (
              <div className="mt-8 pt-8 border-t border-slate-700">
                <TranscriptDisplay transcript={transcript} />
              </div>
            )}
          </div>
        </Card>
      </div>
    </main>
  );
}
