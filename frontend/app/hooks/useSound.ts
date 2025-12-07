'use client';

import { useCallback } from 'react';

/**
 * Hook for playing notification sounds using Web Audio API
 */
export function useSound() {
  const playDing = useCallback(() => {
    try {
      // Create an audio context for a pleasant chime
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioContext = new AudioContextClass();
      
      // Create oscillator for the chime
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      // Pleasant chime frequencies (C major arpeggio)
      const frequencies = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
      
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(frequencies[0], audioContext.currentTime);
      
      // Quick arpeggio
      frequencies.forEach((freq, i) => {
        oscillator.frequency.setValueAtTime(freq, audioContext.currentTime + i * 0.1);
      });
      
      // Envelope
      gainNode.gain.setValueAtTime(0, audioContext.currentTime);
      gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.05);
      gainNode.gain.linearRampToValueAtTime(0.2, audioContext.currentTime + 0.3);
      gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.8);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.8);
    } catch (e) {
      console.warn('Could not play sound:', e);
    }
  }, []);

  return { playDing };
}
