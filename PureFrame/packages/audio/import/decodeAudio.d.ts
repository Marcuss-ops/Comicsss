/**
 * Audio decoding utilities
 */
import type { AudioData } from '../core/types';
/**
 * Get or create the audio context
 */
export declare function getAudioContext(): AudioContext;
/**
 * Decode audio data from an ArrayBuffer
 */
export declare function decodeAudio(buffer: ArrayBuffer, sampleRate?: number): Promise<AudioData>;
/**
 * Decode audio from a Blob
 */
export declare function decodeAudioFromBlob(blob: Blob, sampleRate?: number): Promise<AudioData>;
/**
 * Decode audio from a URL
 */
export declare function decodeAudioFromUrl(url: string, sampleRate?: number): Promise<AudioData>;
/**
 * Decode audio from an HTMLAudioElement
 */
export declare function decodeAudioFromElement(audio: HTMLAudioElement, sampleRate?: number): Promise<AudioData>;
/**
 * Extract AudioData from an AudioBuffer
 */
export declare function extractAudioData(audioBuffer: AudioBuffer): AudioData;
/**
 * Resample audio to a target sample rate
 */
export declare function resampleAudio(audioData: AudioData, targetSampleRate: number): Promise<AudioData>;
/**
 * Convert stereo to mono
 */
export declare function stereoToMono(audioData: AudioData): AudioData;
/**
 * Convert mono to stereo
 */
export declare function monoToStereo(audioData: AudioData): AudioData;
/**
 * Get the peak amplitude of audio data
 */
export declare function getPeakAmplitude(audioData: AudioData): number;
/**
 * Get the RMS (root mean square) of audio data
 */
export declare function getRMS(audioData: AudioData): number;
/**
 * Check if audio data contains silence
 */
export declare function isSilent(audioData: AudioData, threshold?: number): boolean;
/**
 * Dispose of the audio context (call when done)
 */
export declare function disposeAudioContext(): void;
//# sourceMappingURL=decodeAudio.d.ts.map