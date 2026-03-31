/**
 * Audio delay/offset utilities
 */
import type { AudioData } from '../core/types';
/**
 * Add silence to the beginning of audio (delay)
 */
export declare function delayAudio(audioData: AudioData, delayMs: number): AudioData;
/**
 * Delay audio by a number of frames
 */
export declare function delayAudioByFrames(audioData: AudioData, frames: number, fps: number): AudioData;
/**
 * Offset audio to start at a specific time
 */
export declare function offsetAudio(audioData: AudioData, offsetMs: number): AudioData;
/**
 * Offset audio to start at a specific frame
 */
export declare function offsetAudioToFrame(audioData: AudioData, frame: number, fps: number): AudioData;
/**
 * Calculate delay samples from milliseconds
 */
export declare function calculateDelaySamples(delayMs: number, sampleRate: number): number;
/**
 * Calculate delay frames from milliseconds
 */
export declare function calculateDelayFrames(delayMs: number, fps: number): number;
/**
 * Create a delayed copy of audio
 */
export declare function createDelayedCopy(audioData: AudioData, delayMs: number): AudioData;
/**
 * Add silence padding at the end
 */
export declare function padEnd(audioData: AudioData, padMs: number): AudioData;
/**
 * Add silence padding at the start
 */
export declare function padStart(audioData: AudioData, padMs: number): AudioData;
/**
 * Add silence padding to both ends
 */
export declare function padBoth(audioData: AudioData, padMs: number): AudioData;
/**
 * Trim silence from start and return the offset
 */
export declare function findStartOffset(audioData: AudioData, threshold?: number): number;
/**
 * Remove leading silence (reduce offset)
 */
export declare function removeLeadingSilence(audioData: AudioData, threshold?: number): AudioData;
//# sourceMappingURL=delay.d.ts.map