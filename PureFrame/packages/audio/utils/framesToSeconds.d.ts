/**
 * Frame/time conversion utilities
 */
/**
 * Convert frames to seconds
 */
export declare function framesToSeconds(frames: number, fps: number): number;
/**
 * Convert seconds to frames
 */
export declare function secondsToFrames(seconds: number, fps: number): number;
/**
 * Convert frames to milliseconds
 */
export declare function framesToMilliseconds(frames: number, fps: number): number;
/**
 * Convert milliseconds to frames
 */
export declare function millisecondsToFrames(ms: number, fps: number): number;
/**
 * Convert seconds to timecode string (HH:MM:SS:FF)
 */
export declare function secondsToTimecode(seconds: number, fps: number): string;
/**
 * Convert timecode string to seconds
 */
export declare function timecodeToSeconds(timecode: string, fps: number): number;
/**
 * Convert frames to human-readable duration
 */
export declare function framesToDuration(frames: number, fps: number): string;
/**
 * Convert seconds to human-readable duration
 */
export declare function secondsToDuration(seconds: number): string;
/**
 * Convert samples to seconds
 */
export declare function samplesToSeconds(samples: number, sampleRate: number): number;
/**
 * Convert seconds to samples
 */
export declare function secondsToSamples(seconds: number, sampleRate: number): number;
/**
 * Convert samples to frames
 */
export declare function samplesToFrames(samples: number, sampleRate: number, fps: number): number;
/**
 * Convert frames to samples
 */
export declare function framesToSamples(frames: number, fps: number, sampleRate: number): number;
/**
 * Calculate frame duration in seconds
 */
export declare function frameDuration(fps: number): number;
/**
 * Calculate frame duration in milliseconds
 */
export declare function frameDurationMs(fps: number): number;
/**
 * Snap time to nearest frame
 */
export declare function snapToFrame(time: number, fps: number): number;
/**
 * Get frame number at time
 */
export declare function frameAtTime(time: number, fps: number): number;
/**
 * Get time at frame start
 */
export declare function timeAtFrame(frame: number, fps: number): number;
/**
 * Get time at frame end
 */
export declare function timeAtFrameEnd(frame: number, fps: number): number;
/**
 * Get time at frame center
 */
export declare function timeAtFrameCenter(frame: number, fps: number): number;
//# sourceMappingURL=framesToSeconds.d.ts.map