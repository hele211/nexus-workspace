/**
 * useVoice Hook
 * 
 * React hook for voice input/output in chat UI.
 * Wraps VoiceService with React state management.
 * 
 * TTS is proxied through the backend - no API key needed in frontend.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { VoiceService, getVoiceService } from '@/services/elevenlabs';

// =============================================================================
// Types
// =============================================================================

export interface UseVoiceOptions {
  /** Backend API URL (default: http://localhost:8000) */
  backendUrl?: string;
  /** Whether voice features are enabled by default */
  enabled?: boolean;
  /** Callback when TTS starts */
  onSpeakStart?: () => void;
  /** Callback when TTS ends */
  onSpeakEnd?: () => void;
  /** Callback when STT starts */
  onListenStart?: () => void;
  /** Callback when STT ends */
  onListenEnd?: (transcript: string) => void;
  /** Callback on any error */
  onError?: (error: Error) => void;
}

export interface UseVoiceReturn {
  /** Whether voice features are available (always true - backend handles availability) */
  isAvailable: boolean;
  /** Whether voice is enabled by user */
  isEnabled: boolean;
  /** Toggle voice enabled state */
  toggleVoice: () => void;
  /** Whether currently speaking (TTS) */
  isSpeaking: boolean;
  /** Whether currently listening (STT) */
  isListening: boolean;
  /** Speak text using TTS */
  speak: (text: string, agentName?: string) => Promise<void>;
  /** Stop current TTS playback */
  stopSpeaking: () => void;
  /** Start listening for voice input */
  listen: () => Promise<string>;
  /** Whether STT is supported in browser */
  isSTTSupported: boolean;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useVoice(options: UseVoiceOptions = {}): UseVoiceReturn {
  const {
    backendUrl,
    enabled: initialEnabled = false,
    onSpeakStart,
    onSpeakEnd,
    onListenStart,
    onListenEnd,
    onError,
  } = options;

  // State
  const [isEnabled, setIsEnabled] = useState(initialEnabled);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  
  // Refs
  const voiceServiceRef = useRef<VoiceService | null>(null);

  // Initialize VoiceService (no API key needed - backend handles it)
  useEffect(() => {
    voiceServiceRef.current = getVoiceService(backendUrl);
    
    return () => {
      // Cleanup on unmount
      if (voiceServiceRef.current) {
        voiceServiceRef.current.interrupt();
      }
    };
  }, [backendUrl]);

  // Voice is always available (backend handles ElevenLabs availability)
  const isAvailable = true;
  const isSTTSupported = VoiceService.isSTTSupported();

  // ===========================================================================
  // TTS Methods
  // ===========================================================================

  const speak = useCallback(async (text: string, agentName?: string): Promise<void> => {
    const service = voiceServiceRef.current;
    
    if (!service || !isEnabled) {
      return;
    }

    try {
      await service.speak(text, {
        agentName,  // Backend handles voice ID mapping
        onStart: () => {
          setIsSpeaking(true);
          onSpeakStart?.();
        },
        onEnd: () => {
          setIsSpeaking(false);
          onSpeakEnd?.();
        },
      });
    } catch (error) {
      setIsSpeaking(false);
      const err = error instanceof Error ? error : new Error(String(error));
      console.error('[useVoice] Speak error:', err);
      onError?.(err);
    }
  }, [isEnabled, onSpeakStart, onSpeakEnd, onError]);

  const stopSpeaking = useCallback(() => {
    const service = voiceServiceRef.current;
    if (service) {
      service.interrupt();
      setIsSpeaking(false);
    }
  }, []);

  // ===========================================================================
  // STT Methods
  // ===========================================================================

  const listen = useCallback(async (): Promise<string> => {
    const service = voiceServiceRef.current;
    
    if (!service) {
      const error = new Error('Voice service not available');
      onError?.(error);
      throw error;
    }

    if (!isSTTSupported) {
      const error = new Error('Speech recognition not supported in this browser');
      onError?.(error);
      throw error;
    }

    setIsListening(true);
    onListenStart?.();

    try {
      const transcript = await service.listen();
      setIsListening(false);
      onListenEnd?.(transcript);
      return transcript;
    } catch (error) {
      setIsListening(false);
      const err = error instanceof Error ? error : new Error(String(error));
      console.error('[useVoice] Listen error:', err);
      onError?.(err);
      throw err;
    }
  }, [isSTTSupported, onListenStart, onListenEnd, onError]);

  // ===========================================================================
  // Toggle
  // ===========================================================================

  const toggleVoice = useCallback(() => {
    setIsEnabled(prev => !prev);
  }, []);

  return {
    isAvailable,
    isEnabled,
    toggleVoice,
    isSpeaking,
    isListening,
    speak,
    stopSpeaking,
    listen,
    isSTTSupported,
  };
}

export default useVoice;
