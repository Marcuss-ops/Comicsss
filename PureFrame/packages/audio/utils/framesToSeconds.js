/**
 * Frame/time conversion utilities
 */
/**
 * Convert frames to seconds
 */
export function framesToSeconds(frames, fps) {
    return frames / fps;
}
/**
 * Convert seconds to frames
 */
export function secondsToFrames(seconds, fps) {
    return Math.floor(seconds * fps);
}
/**
 * Convert frames to milliseconds
 */
export function framesToMilliseconds(frames, fps) {
    return (frames / fps) * 1000;
}
/**
 * Convert milliseconds to frames
 */
export function millisecondsToFrames(ms, fps) {
    return Math.floor((ms / 1000) * fps);
}
/**
 * Convert seconds to timecode string (HH:MM:SS:FF)
 */
export function secondsToTimecode(seconds, fps) {
    const totalFrames = secondsToFrames(seconds, fps);
    const frames = totalFrames % fps;
    const totalSeconds = Math.floor(totalFrames / fps);
    const secs = totalSeconds % 60;
    const totalMinutes = Math.floor(totalSeconds / 60);
    const mins = totalMinutes % 60;
    const hours = Math.floor(totalMinutes / 60);
    return [
        hours.toString().padStart(2, '0'),
        mins.toString().padStart(2, '0'),
        secs.toString().padStart(2, '0'),
        frames.toString().padStart(2, '0'),
    ].join(':');
}
/**
 * Convert timecode string to seconds
 */
export function timecodeToSeconds(timecode, fps) {
    const parts = timecode.split(':').map(Number);
    if (parts.length !== 4) {
        throw new Error('Invalid timecode format. Expected HH:MM:SS:FF');
    }
    const [hours, mins, secs, frames] = parts;
    return hours * 3600 + mins * 60 + secs + frames / fps;
}
/**
 * Convert frames to human-readable duration
 */
export function framesToDuration(frames, fps) {
    const seconds = framesToSeconds(frames, fps);
    return secondsToDuration(seconds);
}
/**
 * Convert seconds to human-readable duration
 */
export function secondsToDuration(seconds) {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    const parts = [];
    if (hrs > 0) {
        parts.push(`${hrs}h`);
    }
    if (mins > 0) {
        parts.push(`${mins}m`);
    }
    if (secs > 0 || parts.length === 0) {
        parts.push(`${secs}s`);
    }
    if (ms > 0 && hrs === 0) {
        parts.push(`${ms}ms`);
    }
    return parts.join(' ');
}
/**
 * Convert samples to seconds
 */
export function samplesToSeconds(samples, sampleRate) {
    return samples / sampleRate;
}
/**
 * Convert seconds to samples
 */
export function secondsToSamples(seconds, sampleRate) {
    return Math.floor(seconds * sampleRate);
}
/**
 * Convert samples to frames
 */
export function samplesToFrames(samples, sampleRate, fps) {
    const seconds = samplesToSeconds(samples, sampleRate);
    return secondsToFrames(seconds, fps);
}
/**
 * Convert frames to samples
 */
export function framesToSamples(frames, fps, sampleRate) {
    const seconds = framesToSeconds(frames, fps);
    return secondsToSamples(seconds, sampleRate);
}
/**
 * Calculate frame duration in seconds
 */
export function frameDuration(fps) {
    return 1 / fps;
}
/**
 * Calculate frame duration in milliseconds
 */
export function frameDurationMs(fps) {
    return 1000 / fps;
}
/**
 * Snap time to nearest frame
 */
export function snapToFrame(time, fps) {
    return Math.round(time * fps) / fps;
}
/**
 * Get frame number at time
 */
export function frameAtTime(time, fps) {
    return Math.floor(time * fps);
}
/**
 * Get time at frame start
 */
export function timeAtFrame(frame, fps) {
    return frame / fps;
}
/**
 * Get time at frame end
 */
export function timeAtFrameEnd(frame, fps) {
    return (frame + 1) / fps;
}
/**
 * Get time at frame center
 */
export function timeAtFrameCenter(frame, fps) {
    return (frame + 0.5) / fps;
}
//# sourceMappingURL=framesToSeconds.js.map