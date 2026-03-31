/**
 * Audio trim utilities
 */
import { getAudioContext } from '../import/decodeAudio';
/**
 * Trim audio data to a specific time range
 */
export function trimAudio(audioData, startTimeMs, endTimeMs) {
    const { sampleRate, numberOfChannels, channelData, duration } = audioData;
    const startSample = Math.floor((startTimeMs / 1000) * sampleRate);
    const endSample = endTimeMs
        ? Math.floor((endTimeMs / 1000) * sampleRate)
        : channelData[0].length;
    const length = endSample - startSample;
    if (length <= 0) {
        throw new Error('Invalid trim range');
    }
    if (startSample < 0 || endSample > channelData[0].length) {
        throw new Error('Trim range out of bounds');
    }
    // Create trimmed channel data
    const trimmedChannelData = channelData.map((channel) => channel.slice(startSample, endSample));
    // Create a new AudioBuffer
    const ctx = getAudioContext();
    const trimmedBuffer = ctx.createBuffer(numberOfChannels, length, sampleRate);
    for (let i = 0; i < numberOfChannels; i++) {
        trimmedBuffer.getChannelData(i).set(trimmedChannelData[i]);
    }
    return {
        buffer: trimmedBuffer,
        sampleRate,
        duration: length / sampleRate,
        numberOfChannels,
        channelData: trimmedChannelData,
    };
}
/**
 * Trim audio from the beginning
 */
export function trimStart(audioData, durationMs) {
    return trimAudio(audioData, durationMs);
}
/**
 * Trim audio from the end
 */
export function trimEnd(audioData, durationMs) {
    const totalDurationMs = audioData.duration * 1000;
    return trimAudio(audioData, 0, totalDurationMs - durationMs);
}
/**
 * Keep only a specific duration from the start
 */
export function keepDuration(audioData, durationMs) {
    return trimAudio(audioData, 0, durationMs);
}
/**
 * Extract a segment from audio
 */
export function extractSegment(audioData, startTimeMs, endTimeMs) {
    return trimAudio(audioData, startTimeMs, endTimeMs);
}
/**
 * Calculate effective duration after trim
 */
export function calculateTrimmedDuration(originalDurationMs, trimBefore = 0, trimAfter) {
    const end = trimAfter ?? originalDurationMs;
    return Math.max(0, end - trimBefore);
}
/**
 * Apply trim config to audio
 */
export function applyTrimConfig(audioData, config) {
    const trimBefore = config.trimBefore ?? 0;
    const trimAfter = config.trimAfter;
    if (trimBefore === 0 && trimAfter === undefined) {
        return audioData;
    }
    return trimAudio(audioData, trimBefore, trimAfter);
}
/**
 * Get trim boundaries as sample indices
 */
export function getTrimBoundaries(audioData, trimBefore = 0, trimAfter) {
    const { sampleRate, channelData } = audioData;
    const startSample = Math.floor((trimBefore / 1000) * sampleRate);
    const endSample = trimAfter
        ? Math.floor((trimAfter / 1000) * sampleRate)
        : channelData[0].length;
    return { startSample, endSample };
}
/**
 * Check if trim config is valid
 */
export function isValidTrimConfig(audioData, trimBefore = 0, trimAfter) {
    const durationMs = audioData.duration * 1000;
    const end = trimAfter ?? durationMs;
    return (trimBefore >= 0 &&
        end <= durationMs &&
        trimBefore < end);
}
/**
 * Split audio at a specific time
 */
export function splitAudio(audioData, splitTimeMs) {
    const first = trimAudio(audioData, 0, splitTimeMs);
    const second = trimAudio(audioData, splitTimeMs);
    return [first, second];
}
/**
 * Remove silence from the beginning and end
 */
export function trimSilence(audioData, threshold = 0.01) {
    const { channelData, sampleRate } = audioData;
    const channel = channelData[0];
    // Find first non-silent sample
    let startSample = 0;
    for (let i = 0; i < channel.length; i++) {
        if (Math.abs(channel[i]) > threshold) {
            startSample = Math.max(0, i - 100); // Keep a small buffer
            break;
        }
    }
    // Find last non-silent sample
    let endSample = channel.length;
    for (let i = channel.length - 1; i >= 0; i--) {
        if (Math.abs(channel[i]) > threshold) {
            endSample = Math.min(channel.length, i + 100); // Keep a small buffer
            break;
        }
    }
    const startTimeMs = (startSample / sampleRate) * 1000;
    const endTimeMs = (endSample / sampleRate) * 1000;
    return trimAudio(audioData, startTimeMs, endTimeMs);
}
//# sourceMappingURL=trim.js.map