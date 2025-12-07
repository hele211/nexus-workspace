/**
 * VoiceService Manual Testing Guide
 * ==================================
 * 
 * This file documents how to manually test the VoiceService functionality.
 * 
 * SECURITY NOTE:
 * The ElevenLabs API key is stored ONLY on the backend.
 * TTS requests are proxied through POST /api/voice/tts.
 * The frontend never sees the API key.
 * 
 * 
 * MANUAL TESTING INSTRUCTIONS
 * ===========================
 * 
 * ## Prerequisites
 * 
 * 1. Get an ElevenLabs API key from https://elevenlabs.io/
 * 2. Add to your BACKEND .env file (NOT frontend):
 *    ```
 *    ELEVENLABS_API_KEY=your_api_key_here
 *    ```
 * 3. Start the backend: `uvicorn backend.main:app --reload --port 8000`
 * 4. Start the frontend: `npm run dev`
 * 5. Open http://localhost:3000 in Chrome (best Web Speech API support)
 * 
 * 
 * ## Test 1: TTS (Text-to-Speech)
 * 
 * Steps:
 * 1. Open the Dashboard page with the AI Assistant chat
 * 2. Click the speaker icon (🔊) in the chat header to enable voice
 * 3. Send a message like "Hello, how are you?"
 * 4. Verify: Agent response should be spoken aloud
 * 5. Click the stop button (⏹) while speaking to interrupt
 * 6. Verify: Audio stops immediately
 * 
 * Expected behavior:
 * - Voice toggle shows Volume2 icon when enabled
 * - "Speaking..." indicator appears during playback
 * - Stop button appears only while speaking
 * - Different agents may have different voices
 * 
 * 
 * ## Test 2: STT (Speech-to-Text)
 * 
 * Steps:
 * 1. Click the microphone button (🎤) in the chat input area
 * 2. Allow microphone access when browser prompts
 * 3. Speak clearly: "What experiments are running?"
 * 4. Wait for recognition to complete
 * 5. Verify: Transcript appears in the input field
 * 6. Edit if needed, then press Enter or Send to submit
 * 
 * Expected behavior:
 * - Mic button pulses/animates while listening
 * - Input placeholder shows "Listening..."
 * - Transcript is inserted into input (not auto-sent)
 * - Input is focused after transcript appears
 * 
 * 
 * ## Test 3: Error Handling
 * 
 * ### No API Key (Backend)
 * 1. Remove ELEVENLABS_API_KEY from backend .env
 * 2. Restart the backend server
 * 3. Click voice toggle and send a message
 * 4. Verify: Error is logged, TTS fails gracefully
 * 5. Verify: Chat still works normally (text response appears)
 * 
 * ### Microphone Denied
 * 1. Click mic button
 * 2. Deny microphone permission in browser prompt
 * 3. Verify: Error is logged to console
 * 4. Verify: UI returns to normal state (not stuck in "Listening")
 * 
 * ### Network Error (TTS)
 * 1. Enable voice, then disconnect network
 * 2. Send a message
 * 3. Verify: Error is logged, but chat UI doesn't break
 * 4. Verify: Text response still appears
 * 
 * 
 * ## Test 4: Browser Compatibility
 * 
 * Test in different browsers:
 * 
 * | Browser | TTS | STT | Notes |
 * |---------|-----|-----|-------|
 * | Chrome  | ✅  | ✅  | Full support |
 * | Edge    | ✅  | ✅  | Full support (Chromium) |
 * | Firefox | ✅  | ⚠️  | STT may require flags |
 * | Safari  | ✅  | ⚠️  | STT has limited support |
 * 
 * 
 * ## Console Commands for Testing
 * 
 * Open browser DevTools console and run:
 * 
 * ```javascript
 * // Test TTS directly (no API key needed - uses backend proxy)
 * import('@/services/elevenlabs').then(({ getVoiceService }) => {
 *   const service = getVoiceService();
 *   service.speak('Hello from the console!');
 * });
 * 
 * // Test STT support
 * console.log('STT supported:', !!window.SpeechRecognition || !!window.webkitSpeechRecognition);
 * 
 * // Test STT directly
 * import('@/services/elevenlabs').then(({ VoiceService }) => {
 *   const service = new VoiceService();
 *   service.listen().then(t => console.log('Transcript:', t));
 * });
 * ```
 * 
 * 
 * ## Sanity Check Assertions
 * 
 * The following should always be true:
 * 
 * 1. VoiceService.speak() can be called without throwing (even with invalid key)
 * 2. VoiceService.interrupt() can be called anytime without throwing
 * 3. VoiceService.listen() resolves with a string (or rejects with clear error)
 * 4. VoiceService.getVoiceIdForAgent() always returns a non-empty string
 * 5. VoiceService.isSTTSupported() returns a boolean
 * 6. Chat UI never breaks due to voice errors
 */

// =============================================================================
// Unit Tests (uncomment after installing vitest)
// =============================================================================

/*
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VoiceService, getVoiceService, resetVoiceService } from './VoiceService';

// Mock fetch for ElevenLabs API calls
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('VoiceService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetVoiceService();
  });

  describe('speak()', () => {
    it('should not throw with valid text', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(100)),
      });

      const service = new VoiceService({ elevenLabsApiKey: 'test-key' });
      await expect(service.speak('Hello world')).resolves.not.toThrow();
    });

    it('should handle empty text gracefully', async () => {
      const service = new VoiceService({ elevenLabsApiKey: 'test-key' });
      await service.speak('');
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('interrupt()', () => {
    it('should not throw if no audio is playing', () => {
      const service = new VoiceService({ elevenLabsApiKey: 'test-key' });
      expect(() => service.interrupt()).not.toThrow();
    });
  });

  describe('getVoiceIdForAgent()', () => {
    it('should return voice ID for known agents', () => {
      const service = new VoiceService({ elevenLabsApiKey: 'test-key' });
      expect(service.getVoiceIdForAgent('experiment_agent')).toBeTruthy();
    });

    it('should return default voice for unknown agents', () => {
      const service = new VoiceService({ elevenLabsApiKey: 'test-key' });
      const unknown = service.getVoiceIdForAgent('unknown');
      const defaultV = service.getVoiceIdForAgent('default');
      expect(unknown).toBe(defaultV);
    });
  });
});
*/

export {};
