/**
 * Silence detection utilities
 */
import type { AudioData, SilenceRegion, SilenceDetectionOptions } from '../core/types';
/**
 * Detect silence regions in audio data
 */
export declare function detectSilence(audioData: AudioData, options?: SilenceDetectionOptions): SilenceRegion[];
/**
 * Detect leading silence
 */
export declare function detectLeadingSilence(audioData: AudioData, threshold?: number): number;
/**
 * Detect trailing silence
 */
export declare function detectTrailingSilence(audioData: AudioData, threshold?: number): number;
/**
 * Check if audio is entirely silent
 */
export declare function isEntirelySilent(audioData: AudioData, threshold?: number): boolean;
/**
 * Get silence ratio (percentage of silence)
 */
export declare function getSilenceRatio(audioData: AudioData, threshold?: number): number;
/**
 * Find first non-silent sample
 */
export declare function findFirstNonSilentSample(audioData: AudioData, threshold?: number): number;
/**
 * Find last non-silent sample
 */
export declare function findLastNonSilentSample(audioData: AudioData, threshold?: number): number;
/**
 * Get non-silent duration
 */
export declare function getNonSilentDuration(audioData: AudioData, threshold?: number): number;
/**
 * Detect silence at specific time
 */
export declare function isSilentAtTime(audioData: AudioData, timeMs: number, threshold?: number): boolean;
/**
 * Get silence regions with custom window
 */
export declare function detectSilenceWithWindow(audioData: AudioData, windowMs: number, threshold?: number): Array<{
    start: number;
    end: number;
    isSilent: boolean;
}>;
//# sourceMappingURL=detectSilence.d.ts.map