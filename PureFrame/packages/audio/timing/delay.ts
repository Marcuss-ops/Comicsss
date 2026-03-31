/**
 * Audio delay/offset utilities
 */

import type { AudioData } from '../core/types';
import { getAudioContext } from '../import/decodeAudio';
import { framesToSeconds, secondsToFrames } from '../utils/framesToSeconds';

/**
 * Add silence to the beginning of audio (delay)
 */
export function delayAudio(
  audioData: AudioData,
  delayMs: number
): AudioData {
  if (delayMs <= 0) {
    return audioData;
  }

  const { sampleRate, numberOfChannels, channelData } = audioData;
  const delaySamples = Math.floor((delayMs / 1000) * sampleRate);
  
  // Create new channel data with delay
  const newChannelData = channelData.map((channel) => {
    const delayed = new Float32Array(channel.length + delaySamples);
    delayed.set(channel, delaySamples);
    return delayed;
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
 * Delay audio by a number of frames
 */
export function delayAudioByFrames(
  audioData: AudioData,
  frames: number,
  fps: number
): AudioData {
  const delayMs = framesToSeconds(frames, fps) * 1000;
  return delayAudio(audioData, delayMs);
}

/**
 * Offset audio to start at a specific time
 */
export function offsetAudio(
  audioData: AudioData,
  offsetMs: number
): AudioData {
  return delayAudio(audioData, Math.max(0, offsetMs));
}

/**
 * Offset audio to start at a specific frame
 */
export function offsetAudioToFrame(
  audioData: AudioData,
  frame: number,
  fps: number
): AudioData {
  const offsetMs = framesToSeconds(frame, fps) * 1000;
  return offsetAudio(audioData, offsetMs);
}

/**
 * Calculate delay samples from milliseconds
 */
export function calculateDelaySamples(
  delayMs: number,
  sampleRate: number
): number {
  return Math.floor((delayMs / 1000) * sampleRate);
}

/**
 * Calculate delay frames from milliseconds
 */
export function calculateDelayFrames(
  delayMs: number,
  fps: number
): number {
  return secondsToFrames(delayMs / 1000, fps);
}

/**
 * Create a delayed copy of audio
 */
export function createDelayedCopy(
  audioData: AudioData,
  delayMs: number
): AudioData {
  return delayAudio(audioData, delayMs);
}

/**
 * Add silence padding at the end
 */
export function padEnd(
  audioData: AudioData,
  padMs: number
): AudioData {
  if (padMs <= 0) {
    return audioData;
  }

  const { sampleRate, numberOfChannels, channelData } = audioData;
  const padSamples = Math.floor((padMs / 1000) * sampleRate);
  
  // Create new channel data with padding
  const newChannelData = channelData.map((channel) => {
    const padded = new Float32Array(channel.length + padSamples);
    padded.set(channel, 0);
    return padded;
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
 * Add silence padding at the start
 */
export function padStart(
  audioData: AudioData,
  padMs: number
): AudioData {
  return delayAudio(audioData, padMs);
}

/**
 * Add silence padding to both ends
 */
export function padBoth(
  audioData: AudioData,
  padMs: number
): AudioData {
  const padded = padStart(audioData, padMs);
  return padEnd(padded, padMs);
}

/**
 * Trim silence from start and return the offset
 */
export function findStartOffset(
  audioData: AudioData,
  threshold: number = 0.01
): number {
  const { channelData, sampleRate } = audioData;
  const channel = channelData[0];
  
  for (let i = 0; i < channel.length; i++) {
    if (Math.abs(channel[i]) > threshold) {
      return (i / sampleRate) * 1000;
    }
  }
  
  return 0;
}

/**
 * Remove leading silence (reduce offset)
 */
export function removeLeadingSilence(
  audioData: AudioData,
  threshold: number = 0.01
): AudioData {
  const offsetMs = findStartOffset(audioData, threshold);
  
  if (offsetMs === 0) {
    return audioData;
  }

  const { sampleRate, numberOfChannels, channelData } = audioData;
  const startSample = Math.floor((offsetMs / 1000) * sampleRate);
  
  // Create trimmed channel data
  const trimmedChannelData = channelData.map((channel) =>
    channel.slice(startSample)
  );

  // Create a new AudioBuffer
  const ctx = getAudioContext();
  const newBuffer = ctx.createBuffer(numberOfChannels, trimmedChannelData[0].length, sampleRate);
  
  for (let i = 0; i < numberOfChannels; i++) {
    newBuffer.getChannelData(i).set(trimmedChannelData[i]);
  }

  return {
    buffer: newBuffer,
    sampleRate,
    duration: trimmedChannelData[0].length / sampleRate,
    numberOfChannels,
    channelData: trimmedChannelData,
  };
}