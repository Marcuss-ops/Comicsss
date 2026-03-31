/**
 * Audio trim utilities
 */

import type { AudioData, AudioClipConfig } from '../core/types';
import { getAudioContext } from '../import/decodeAudio';

/**
 * Trim audio data to a specific time range
 */
export function trimAudio(
  audioData: AudioData,
  startTimeMs: number,
  endTimeMs?: number
): AudioData {
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
  const trimmedChannelData = channelData.map((channel) =>
    channel.slice(startSample, endSample)
  );

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
export function trimStart(
  audioData: AudioData,
  durationMs: number
): AudioData {
  return trimAudio(audioData, durationMs);
}

/**
 * Trim audio from the end
 */
export function trimEnd(
  audioData: AudioData,
  durationMs: number
): AudioData {
  const totalDurationMs = audioData.duration * 1000;
  return trimAudio(audioData, 0, totalDurationMs - durationMs);
}

/**
 * Keep only a specific duration from the start
 */
export function keepDuration(
  audioData: AudioData,
  durationMs: number
): AudioData {
  return trimAudio(audioData, 0, durationMs);
}

/**
 * Extract a segment from audio
 */
export function extractSegment(
  audioData: AudioData,
  startTimeMs: number,
  endTimeMs: number
): AudioData {
  return trimAudio(audioData, startTimeMs, endTimeMs);
}

/**
 * Calculate effective duration after trim
 */
export function calculateTrimmedDuration(
  originalDurationMs: number,
  trimBefore: number = 0,
  trimAfter?: number
): number {
  const end = trimAfter ?? originalDurationMs;
  return Math.max(0, end - trimBefore);
}

/**
 * Apply trim config to audio
 */
export function applyTrimConfig(
  audioData: AudioData,
  config: AudioClipConfig
): AudioData {
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
export function getTrimBoundaries(
  audioData: AudioData,
  trimBefore: number = 0,
  trimAfter?: number
): { startSample: number; endSample: number } {
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
export function isValidTrimConfig(
  audioData: AudioData,
  trimBefore: number = 0,
  trimAfter?: number
): boolean {
  const durationMs = audioData.duration * 1000;
  const end = trimAfter ?? durationMs;
  
  return (
    trimBefore >= 0 &&
    end <= durationMs &&
    trimBefore < end
  );
}

/**
 * Split audio at a specific time
 */
export function splitAudio(
  audioData: AudioData,
  splitTimeMs: number
): [AudioData, AudioData] {
  const first = trimAudio(audioData, 0, splitTimeMs);
  const second = trimAudio(audioData, splitTimeMs);
  
  return [first, second];
}

/**
 * Remove silence from the beginning and end
 */
export function trimSilence(
  audioData: AudioData,
  threshold: number = 0.01
): AudioData {
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