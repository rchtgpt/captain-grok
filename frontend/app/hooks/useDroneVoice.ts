/**
 * Hook for Grok-style voice narration of drone commands
 * Uses Web Speech API for text-to-speech
 */

'use client';

import { useCallback, useRef, useState, useEffect } from 'react';

// Tool-to-speech mapping for natural narration
const TOOL_NARRATIONS: Record<string, (args: Record<string, unknown>) => string> = {
  takeoff: () => "Initiating liftoff. Engines engaged.",
  land: () => "Beginning landing sequence. Descending now.",
  move: (args) => {
    const direction = args.direction as string;
    const distance = args.distance as number;
    const directionMap: Record<string, string> = {
      forward: 'forward',
      back: 'backward',
      left: 'to the left',
      right: 'to the right',
      up: 'ascending',
      down: 'descending'
    };
    return `Moving ${directionMap[direction] || direction}, ${distance} centimeters.`;
  },
  rotate: (args) => {
    const degrees = args.degrees as number;
    const direction = degrees > 0 ? 'clockwise' : 'counter-clockwise';
    return `Rotating ${Math.abs(degrees)} degrees ${direction}.`;
  },
  flip: (args) => {
    const direction = args.direction as string;
    return `Executing ${direction} flip. Hang on!`;
  },
  hover: () => "Holding position. Hovering in place.",
  look: (args) => {
    const target = args.target as string || args.prompt as string;
    return target ? `Scanning for ${target}.` : "Analyzing surroundings.";
  },
  search: (args) => {
    const target = args.target as string;
    return `Searching area for ${target}.`;
  },
  analyze: () => "Analyzing current view.",
  get_battery: () => "Checking battery status.",
  get_status: () => "Running system diagnostics.",
  emergency_stop: () => "Emergency stop activated!",
  check_clearance: () => "Checking obstacle clearance.",
};

// Success/failure responses
const SUCCESS_PHRASES = [
  "Complete.",
  "Done.",
  "Executed successfully.",
  "Mission accomplished.",
];

const FAILURE_PHRASES = [
  "Unable to comply.",
  "Action blocked.",
  "Safety override engaged.",
  "Cannot execute.",
];

interface DroneVoiceOptions {
  enabled?: boolean;
  pitch?: number;      // 0-2, default 1
  rate?: number;       // 0.1-10, default 1
  volume?: number;     // 0-1, default 1
  voiceName?: string;  // Preferred voice name
}

interface DroneVoiceState {
  enabled: boolean;
  setEnabled: (enabled: boolean) => void;
  isSpeaking: boolean;
  speak: (text: string) => void;
  speakToolStart: (toolName: string, args: Record<string, unknown>) => void;
  speakToolComplete: (toolName: string, success: boolean, message?: string) => void;
  speakFound: (target: string) => void;
  cancel: () => void;
  availableVoices: SpeechSynthesisVoice[];
  selectedVoice: string;
  setSelectedVoice: (voiceName: string) => void;
}

export function useDroneVoice(options: DroneVoiceOptions = {}): DroneVoiceState {
  const {
    enabled: initialEnabled = true,
    pitch = 0.9,
    rate = 1.05,
    volume = 1,
    voiceName = ''
  } = options;

  const [enabled, setEnabled] = useState(initialEnabled);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState(voiceName);
  
  const speechSynthRef = useRef<SpeechSynthesis | null>(null);
  const utteranceQueue = useRef<string[]>([]);
  const isProcessingQueue = useRef(false);

  // Initialize speech synthesis
  useEffect(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      speechSynthRef.current = window.speechSynthesis;
      
      // Load voices
      const loadVoices = () => {
        const voices = speechSynthRef.current?.getVoices() || [];
        setAvailableVoices(voices);
        
        // Auto-select a good voice for "robot/AI" feel
        if (!selectedVoice && voices.length > 0) {
          // Prefer: Google UK English Male, Alex, Daniel, or any English voice
          const preferredVoices = [
            'Google UK English Male',
            'Google US English',
            'Alex',
            'Daniel',
            'Samantha',
            'Karen',
          ];
          
          const foundVoice = voices.find(v => 
            preferredVoices.some(pv => v.name.includes(pv))
          ) || voices.find(v => v.lang.startsWith('en')) || voices[0];
          
          if (foundVoice) {
            setSelectedVoice(foundVoice.name);
          }
        }
      };
      
      loadVoices();
      speechSynthRef.current.onvoiceschanged = loadVoices;
    }
  }, [selectedVoice]);

  // Process the speech queue
  const processQueue = useCallback(() => {
    if (isProcessingQueue.current || utteranceQueue.current.length === 0) return;
    if (!speechSynthRef.current || !enabled) return;
    
    isProcessingQueue.current = true;
    const text = utteranceQueue.current.shift()!;
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.pitch = pitch;
    utterance.rate = rate;
    utterance.volume = volume;
    
    // Set voice
    if (selectedVoice) {
      const voice = availableVoices.find(v => v.name === selectedVoice);
      if (voice) utterance.voice = voice;
    }
    
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => {
      setIsSpeaking(false);
      isProcessingQueue.current = false;
      // Process next item in queue
      setTimeout(processQueue, 150);
    };
    utterance.onerror = () => {
      setIsSpeaking(false);
      isProcessingQueue.current = false;
      setTimeout(processQueue, 150);
    };
    
    speechSynthRef.current.speak(utterance);
  }, [enabled, pitch, rate, volume, selectedVoice, availableVoices]);

  // Queue speech
  const speak = useCallback((text: string) => {
    if (!enabled) return;
    utteranceQueue.current.push(text);
    processQueue();
  }, [enabled, processQueue]);

  // Narrate tool start
  const speakToolStart = useCallback((toolName: string, args: Record<string, unknown>) => {
    if (!enabled) return;
    
    const narration = TOOL_NARRATIONS[toolName];
    if (narration) {
      speak(narration(args));
    } else {
      // Generic fallback
      speak(`Executing ${toolName.replace(/_/g, ' ')}.`);
    }
  }, [enabled, speak]);

  // Narrate tool completion
  const speakToolComplete = useCallback((toolName: string, success: boolean, message?: string) => {
    if (!enabled) return;
    
    // Only speak completion for major actions
    const majorTools = ['takeoff', 'land', 'flip', 'search', 'emergency_stop'];
    if (!majorTools.includes(toolName)) return;
    
    if (success) {
      const phrase = SUCCESS_PHRASES[Math.floor(Math.random() * SUCCESS_PHRASES.length)];
      speak(phrase);
    } else {
      const phrase = FAILURE_PHRASES[Math.floor(Math.random() * FAILURE_PHRASES.length)];
      // Include brief reason if available
      if (message && message.length < 50) {
        speak(`${phrase} ${message}`);
      } else {
        speak(phrase);
      }
    }
  }, [enabled, speak]);

  // Special narration for found target
  const speakFound = useCallback((target: string) => {
    if (!enabled) return;
    speak(`Target acquired! I found the ${target}.`);
  }, [enabled, speak]);

  // Cancel all speech
  const cancel = useCallback(() => {
    if (speechSynthRef.current) {
      speechSynthRef.current.cancel();
      utteranceQueue.current = [];
      isProcessingQueue.current = false;
      setIsSpeaking(false);
    }
  }, []);

  return {
    enabled,
    setEnabled,
    isSpeaking,
    speak,
    speakToolStart,
    speakToolComplete,
    speakFound,
    cancel,
    availableVoices,
    selectedVoice,
    setSelectedVoice
  };
}

