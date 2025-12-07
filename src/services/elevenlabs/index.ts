/**
 * ElevenLabs Voice Services
 * 
 * Exports:
 * - VoiceService: Main service for TTS and STT
 * - getVoiceService: Singleton getter
 * - resetVoiceService: Reset singleton (for testing)
 */

export { 
  VoiceService, 
  getVoiceService, 
  resetVoiceService,
  type SpeakOptions,
  type VoiceServiceConfig,
} from './VoiceService';
