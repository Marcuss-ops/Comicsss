/**
 * Audio trim utilities
 */
import type { AudioData, AudioClipConfig } from '../core/types';
/**
 * Trim audio data to a specific time range
 */
export declare function trimAudio(audioData: AudioData, startTimeMs: number, endTimeMs?: number): AudioData;
/**
 * Trim audio from the beginning
 */
export declare function trimStart(audioData: AudioData, durationMs: number): AudioData;
/**
 * Trim audio from the end
 */
export declare function trimEnd(audioData: AudioData, durationMs: number): AudioData;
/**
 * Keep only a specific duration from the start
 */
export declare function keepDuration(audioData: AudioData, durationMs: number): AudioData;
/**
 * Extract a segment from audio
 */
export declare function extractSegment(audioData: AudioData, startTimeMs: number, endTimeMs: number): AudioData;
/**
 * Calculate effective duration after trim
 */
export declare function calculateTrimmedDuration(originalDurationMs: number, trimBefore?: number, trimAfter?: number): number;
/**
 * Apply trim config to audio
 */
export declare function applyTrimConfig(audioData: AudioData, config: AudioClipConfig): AudioData;
/**
 * Get trim boundaries as sample indices
 */
export declare function getTrimBoundaries(audioData: AudioData, trimBefore?: number, trimAfter?: number): {
    startSample: number;
    endSample: number;
};
/**
 * Check if trim config is valid
 */
export declare function isValidTrimConfig(audioData: AudioData, trimBefore?: number, trimAfter?: number): boolean;
/**
 * Split audio at a specific time
 */
export declare function splitAudio(audioData: AudioData, splitTimeMs: number): [AudioData, AudioData];
/**
 * Remove silence from the beginning and end
 */
export declare function trimSilence(audioData: AudioData, threshold?: number): AudioData;
//# sourceMappingURL=trim.d.ts.map