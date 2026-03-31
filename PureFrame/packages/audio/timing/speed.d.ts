/**
 * Audio playback speed utilities
 */
import type { AudioData, AudioClipConfig } from '../core/types';
/**
 * Apply playback rate to audio data (time stretching)
 */
export declare function applyPlaybackRate(audioData: AudioData, rate: number): AudioData;
/**
 * Reverse audio playback
 */
export declare function reverseAudio(audioData: AudioData): AudioData;
/**
 * Speed up audio (shorthand for rate > 1)
 */
export declare function speedUp(audioData: AudioData, factor: number): AudioData;
/**
 * Slow down audio (shorthand for rate < 1)
 */
export declare function slowDown(audioData: AudioData, factor: number): AudioData;
/**
 * Calculate new duration after applying playback rate
 */
export declare function calculateSpeedDuration(originalDurationMs: number, rate: number): number;
/**
 * Calculate playback rate from target duration
 */
export declare function calculateRateForDuration(originalDurationMs: number, targetDurationMs: number): number;
/**
 * Change audio duration while maintaining pitch (simple time stretching)
 */
export declare function changeDuration(audioData: AudioData, targetDurationMs: number): AudioData;
/**
 * Apply playback rate config from clip config
 */
export declare function applySpeedConfig(audioData: AudioData, config: AudioClipConfig): AudioData;
/**
 * Calculate effective rate considering trim
 */
export declare function calculateEffectiveRate(config: AudioClipConfig, assetDurationMs: number): number;
/**
 * Get the output duration after all timing operations
 */
export declare function getOutputDuration(config: AudioClipConfig, assetDurationMs: number, fps: number): number;
/**
 * Change pitch without affecting speed (basic implementation)
 */
export declare function changePitch(audioData: AudioData, semitones: number): AudioData;
/**
 * Create a speed ramp (gradually change speed)
 */
export declare function speedRamp(audioData: AudioData, startRate: number, endRate: number): AudioData;
//# sourceMappingURL=speed.d.ts.map