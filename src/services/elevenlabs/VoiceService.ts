/**
 * VoiceService - TTS via Backend Proxy + Browser STT
 * 
 * Phase 3: Basic voice output + simple voice input for chat/agent UI.
 * 
 * Features:
 * - TTS via backend proxy endpoint (ElevenLabs key stays server-side)
 * - Browser-based STT (Web Speech API) for voice input
 * - Simple playback controls (speak, interrupt)
 * 
 * Security:
 * - ElevenLabs API key is NEVER exposed to the browser
 * - TTS requests go through POST /api/voice/tts on the backend
 * - Backend handles ElevenLabs authentication
 * 
 * NOT implemented in this phase:
 * - Full VAD (Voice Activity Detection)
 * - Continuous/streaming STT
 * - Complex concurrency between overlapping speak/listen calls
 * - ElevenLabs STT (TODO for future)
 */

// =============================================================================
// Types
// =============================================================================

export interface SpeakOptions {
  /** Agent name for voice selection (backend handles voice ID mapping) */
  agentName?: string;
  /** Override voice ID (optional, backend has defaults) */
  voiceId?: string;
  onStart?: () => void;
  onEnd?: () => void;
}

export interface VoiceServiceConfig {
  /** Backend API URL (default: http://localhost:8000) */
  backendUrl?: string;
}

// Extend Window interface for Web Speech API
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: Event & { error: string }) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

// =============================================================================
// Constants
// =============================================================================

/** Default backend API URL */
const DEFAULT_BACKEND_URL = 'http://localhost:8000';

/** TTS endpoint path */
const TTS_ENDPOINT = '/api/voice/tts';

// =============================================================================
// VoiceService Class
// =============================================================================

export class VoiceService {
  private backendUrl: string;
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;
  private isPlaying: boolean = false;

  constructor(config: VoiceServiceConfig = {}) {
    this.backendUrl = config.backendUrl || DEFAULT_BACKEND_URL;
  }

  // ===========================================================================
  // TTS Methods (via Backend Proxy)
  // ===========================================================================

  /**
   * Speak text using backend TTS proxy.
   * 
   * The backend handles ElevenLabs authentication - no API key needed here.
   * 
   * @param text - The text to speak
   * @param options - Optional configuration (agentName, callbacks)
   */
  async speak(text: string, options?: SpeakOptions): Promise<void> {
    if (!text.trim()) {
      console.warn('[VoiceService] Empty text provided to speak()');
      return;
    }

    // Interrupt any current playback
    this.interrupt();

    try {
      // Initialize AudioContext if needed (must be done after user interaction)
      if (!this.audioContext) {
        this.audioContext = new AudioContext();
      }

      // Resume AudioContext if suspended (browser autoplay policy)
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // Call backend TTS proxy endpoint
      const response = await fetch(
        `${this.backendUrl}${TTS_ENDPOINT}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            text,
            agent_name: options?.agentName,
            voice_id: options?.voiceId,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(`TTS error: ${response.status} - ${errorData.detail || 'Unknown error'}`);
      }

      // Get audio data as ArrayBuffer
      const audioData = await response.arrayBuffer();

      // Decode audio data
      const audioBuffer = await this.audioContext.decodeAudioData(audioData);

      // Create and configure audio source
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);

      // Store reference for interrupt()
      this.currentSource = source;
      this.isPlaying = true;

      // Set up end callback
      source.onended = () => {
        this.isPlaying = false;
        this.currentSource = null;
        options?.onEnd?.();
      };

      // Call onStart callback and start playback
      options?.onStart?.();
      source.start(0);

    } catch (error) {
      console.error('[VoiceService] TTS error:', error);
      this.isPlaying = false;
      this.currentSource = null;
      // Call onEnd even on error so UI can reset
      options?.onEnd?.();
      // Don't throw - fail gracefully to not break chat UI
    }
  }

  /**
   * Interrupt current audio playback.
   */
  interrupt(): void {
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch {
        // Ignore errors if already stopped
      }
      this.currentSource = null;
    }
    this.isPlaying = false;
  }

  /**
   * Check if audio is currently playing.
   */
  isSpeaking(): boolean {
    return this.isPlaying;
  }

  // ===========================================================================
  // STT Methods (Browser Web Speech API)
  // ===========================================================================

  /**
   * Listen for voice input using browser Web Speech API.
   * 
   * Returns a promise that resolves with the final transcript.
   * 
   * NOTE: This is a simple implementation using browser's built-in STT.
   * TODO: Consider ElevenLabs STT integration for better accuracy in future.
   * 
   * @returns Promise resolving to the transcribed text
   * @throws Error if Web Speech API is not available
   */
  async listen(): Promise<string> {
    return new Promise((resolve, reject) => {
      // Check for Web Speech API support
      const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
      
      if (!SpeechRecognitionClass) {
        const error = new Error('Web Speech API is not supported in this browser');
        console.error('[VoiceService] STT error:', error.message);
        reject(error);
        return;
      }

      const recognition = new SpeechRecognitionClass();
      
      // Configure recognition
      recognition.continuous = false;      // Stop after first result
      recognition.interimResults = false;  // Only final results
      recognition.lang = 'en-US';          // TODO: Make configurable

      let hasResult = false;

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        hasResult = true;
        const results = event.results;
        if (results.length > 0) {
          const transcript = results[0][0].transcript;
          console.log('[VoiceService] STT result:', transcript);
          resolve(transcript);
        } else {
          resolve('');
        }
      };

      recognition.onerror = (event: Event & { error: string }) => {
        console.error('[VoiceService] STT error:', event.error);
        
        // Handle specific error types
        switch (event.error) {
          case 'no-speech':
            // No speech detected - resolve with empty string
            resolve('');
            break;
          case 'audio-capture':
            reject(new Error('No microphone found. Please check your audio settings.'));
            break;
          case 'not-allowed':
            reject(new Error('Microphone access denied. Please allow microphone access.'));
            break;
          case 'network':
            reject(new Error('Network error during speech recognition.'));
            break;
          default:
            reject(new Error(`Speech recognition error: ${event.error}`));
        }
      };

      recognition.onend = () => {
        // If no result was received, resolve with empty string
        if (!hasResult) {
          resolve('');
        }
      };

      recognition.onstart = () => {
        console.log('[VoiceService] STT started listening...');
      };

      // Start recognition
      try {
        recognition.start();
      } catch (error) {
        console.error('[VoiceService] Failed to start STT:', error);
        reject(error);
      }
    });
  }

  /**
   * Check if Web Speech API is available in the current browser.
   */
  static isSTTSupported(): boolean {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  // ===========================================================================
  // Cleanup
  // ===========================================================================

  /**
   * Clean up resources.
   */
  dispose(): void {
    this.interrupt();
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}

// =============================================================================
// Singleton Instance
// =============================================================================

let voiceServiceInstance: VoiceService | null = null;

/**
 * Get or create the VoiceService singleton.
 * 
 * No API key needed - TTS is proxied through the backend.
 * 
 * @param backendUrl - Optional backend URL override
 * @returns VoiceService instance
 */
export function getVoiceService(backendUrl?: string): VoiceService {
  if (voiceServiceInstance) {
    return voiceServiceInstance;
  }

  voiceServiceInstance = new VoiceService({ backendUrl });
  return voiceServiceInstance;
}

/**
 * Reset the singleton (useful for testing or config changes).
 */
export function resetVoiceService(): void {
  if (voiceServiceInstance) {
    voiceServiceInstance.dispose();
    voiceServiceInstance = null;
  }
}

export default VoiceService;
