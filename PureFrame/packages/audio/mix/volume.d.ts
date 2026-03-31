/**
 * Volume control utilities
 */
import type { AudioData, VolumeFunction, VolumeEnvelope } from '../core/types';
/**
 * Apply a static volume to audio data
 */
export declare function applyVolume(audioData: AudioData, volume: number): AudioData;
/**
 * Apply a volume function that varies over time
 */
export declare function applyVolumeEnvelope(audioData: AudioData, envelope: VolumeEnvelope): AudioData;
/**
 * Apply a volume function to audio data
 */
export declare function applyVolumeFunction(audioData: AudioData, volumeFn: VolumeFunction, fps?: number): AudioData;
/**
 * Normalize audio to a target peak level
 */
export declare function normalize(audioData: AudioData, targetPeak?: number): AudioData;
/**
 * Apply gain in decibels
 */
export declare function applyGainDb(audioData: AudioData, gainDb: number): AudioData;
/**
 * Create a fade-in envelope
 */
export declare function createFadeIn(durationFrames: number, type?: 'linear' | 'exponential' | 'logarithmic'): VolumeEnvelope;
/**
 * Create a fade-out envelope
 */
export declare function createFadeOut(startFrame: number, durationFrames: number, type?: 'linear' | 'exponential' | 'logarithmic'): VolumeEnvelope;
//# sourceMappingURL=volume.d.ts.map