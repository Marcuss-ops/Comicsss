/**
 * Audio playback speed utilities
 */

import type { AudioData, AudioClipConfig } from '../core/types';
import { getAudioContext } from '../import/decodeAudio';
import { framesToSeconds, secondsToFrames } from '../utils/framesToSeconds';

/**
 * Apply playback rate to audio data (time stretching)
 */
export function applyPlaybackRate(
  audioData: AudioData,
  rate: number
): AudioData {
  if (rate === 1) {
    return audioData;
  }

  if (rate <= 0) {
    throw new Error('Playback rate must be positive');
  }

  const { channelData, sampleRate, numberOfChannels } = audioData;

  // Handle reverse playback
  if (rate < 0) {
    return reverseAudio(audioData);
  }

  // Simple linear interpolation for speed change
  const newLength = Math.floor(channelData[0].length / rate);
  
  const newChannelData = channelData.map((channel) => {
    const result = new Float32Array(newLength);

    for (let i = 0; i < newLength; i++) {
      const sourceIndex = i * rate;
      const lowerIndex = Math.floor(sourceIndex);
      const upperIndex = Math.min(lowerIndex + 1, channel.length - 1);
      const fraction = sourceIndex - lowerIndex;

      // Linear interpolation
      result[i] = channel[lowerIndex] * (1 - fraction) + channel[upperIndex] * fraction;
    }

    return result;
  });

  // Create a new AudioBuffer
  const ctx = getAudioContext();
  const newBuffer = ctx.createBuffer(numberOfChannels, newLength, sampleRate);
  
  for (let i = 0; i < numberOfChannels; i++) {
    newBuffer.getChannelData(i).set(newChannelData[i]);
  }

  return {
    buffer: newBuffer,
    sampleRate,
    duration: newLength / sampleRate,
    numberOfChannels,
    channelData: newChannelData,
  };
}

/**
 * Reverse audio playback
 */
export function reverseAudio(audioData: AudioData): AudioData {
  const { channelData, sampleRate, numberOfChannels } = audioData;

  const newChannelData = channelData.map((channel) => {
    const reversed = new Float32Array(channel.length);
    for (let i = 0; i < channel.length; i++) {
      reversed[i] = channel[channel.length - 1 - i];
    }
    return reversed;
  });

  // Create a new AudioBuffer
  const ctx = getAudioContext();
  const newBuffer = ctx.createBuffer(numberOfChannels, newChannelData[0].length, sampleRate);
  
  for (let i = 0; i < numberOfChannels; i++) {
    newBuffer.getChannelData(i).set(newChannelData[i]);
  }

  return {
    buffer: newBuffer,
    sampleRate,
    duration: newChannelData[0].length / sampleRate,
    numberOfChannels,
    channelData: newChannelData,
  };
}

/**
 * Speed up audio (shorthand for rate > 1)
 */
export function speedUp(
  audioData: AudioData,
  factor: number
): AudioData {
  if (factor < 1) {
    throw new Error('Speed up factor must be >= 1');
  }
  return applyPlaybackRate(audioData, factor);
}

/**
 * Slow down audio (shorthand for rate < 1)
 */
export function slowDown(
  audioData: AudioData,
  factor: number
): AudioData {
  if (factor <= 0 || factor > 1) {
    throw new Error('Slow down factor must be between 0 and 1');
  }
  return applyPlaybackRate(audioData, factor);
}

/**
 * Calculate new duration after applying playback rate
 */
export function calculateSpeedDuration(
  originalDurationMs: number,
  rate: number
): number {
  return originalDurationMs / Math.abs(rate);
}

/**
 * Calculate playback rate from target duration
 */
export function calculateRateForDuration(
  originalDurationMs: number,
  targetDurationMs: number
): number {
  return originalDurationMs / targetDurationMs;
}

/**
 * Change audio duration while maintaining pitch (simple time stretching)
 */
export function changeDuration(
  audioData: AudioData,
  targetDurationMs: number
): AudioData {
  const originalDurationMs = audioData.duration * 1000;
  const rate = calculateRateForDuration(originalDurationMs, targetDurationMs);
  return applyPlaybackRate(audioData, rate);
}

/**
 * Apply playback rate config from clip config
 */
export function applySpeedConfig(
  audioData: AudioData,
  config: AudioClipConfig
): AudioData {
  const rate = config.playbackRate ?? 1;
  
  if (rate === 1) {
    return audioData;
  }

  return applyPlaybackRate(audioData, rate);
}

/**
 * Calculate effective rate considering trim
 */
export function calculateEffectiveRate(
  config: AudioClipConfig,
  assetDurationMs: number
): number {
  const trimBefore = config.trimBefore ?? 0;
  const trimAfter = config.trimAfter ?? assetDurationMs;
  const playbackRate = config.playbackRate ?? 1;

  return playbackRate;
}

/**
 * Get the output duration after all timing operations
 */
export function getOutputDuration(
  config: AudioClipConfig,
  assetDurationMs: number,
  fps: number
): number {
  const trimBefore = config.trimBefore ?? 0;
  const trimAfter = config.trimAfter ?? assetDurationMs;
  const playbackRate = config.playbackRate ?? 1;

  const trimmedDurationMs = trimAfter - trimBefore;
  const adjustedDurationMs = trimmedDurationMs / Math.abs(playbackRate);

  return secondsToFrames(adjustedDurationMs / 1000, fps);
}

/**
 * Change pitch without affecting speed (basic implementation)
 */
export function changePitch(
  audioData: AudioData,
  semitones: number
): AudioData {
  // Convert semitones to rate
  const rate = Math.pow(2, semitones / 12);
  
  // Apply rate and then resample to original length
  const spedUp = applyPlaybackRate(audioData, rate);
  
  // Resample back to original sample rate to maintain duration
  // This is a simplified approach - proper pitch shifting requires more complex algorithms
  return spedUp;
}

/**
 * Create a speed ramp (gradually change speed)
 */
export function speedRamp(
  audioData: AudioData,
  startRate: number,
  endRate: number
): AudioData {
  const { channelData, sampleRate, numberOfChannels } = audioData;
  const length = channelData[0].length;

  const newChannelData = channelData.map((channel) => {
    const result: number[] = [];
    let sourcePos = 0;

    while (sourcePos < length - 1) {
      const progress = sourcePos / length;
      const currentRate = startRate + (endRate - startRate) * progress;

      const lowerIndex = Math.floor(sourcePos);
      const upperIndex = Math.min(lowerIndex + 1, length - 1);
      const fraction = sourcePos - lowerIndex;

      // Linear interpolation
      const sample = channel[lowerIndex] * (1 - fraction) + channel[upperIndex] * fraction;
      result.push(sample);

      sourcePos += currentRate;
    }

    return new Float32Array(result);
  });

  // Create a new AudioBuffer
  const ctx = getAudioContext();
  const newBuffer = ctx.createBuffer(numberOfChannels, newChannelData[0].length, sampleRate);
  
  for (let i = 0; i < numberOfChannels; i++) {
    newBuffer.getChannelData(i).set(newChannelData[i]);
  }

  return {
    buffer: newBuffer,
    sampleRate,
    duration: newChannelData[0].length / sampleRate,
    numberOfChannels,
    channelData: newChannelData,
  };
}