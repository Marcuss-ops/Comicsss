/**
 * Volume control utilities
 */

import type { AudioData, VolumeFunction, VolumeEnvelope, EnvelopePoint } from '../core/types';
import { clampVolume } from '../utils/clampVolume';

/**
 * Apply a static volume to audio data
 */
export function applyVolume(
  audioData: AudioData,
  volume: number
): AudioData {
  const clampedVolume = clampVolume(volume);
  
  if (clampedVolume === 1) {
    return audioData;
  }

  const { channelData, sampleRate, duration, numberOfChannels, buffer } = audioData;
  
  // Create new channel data with volume applied
  const newChannelData = channelData.map((channel) => {
    const newChannel = new Float32Array(channel.length);
    for (let i = 0; i < channel.length; i++) {
      newChannel[i] = channel[i] * clampedVolume;
    }
    return newChannel;
  });

  // Create a new AudioBuffer
  const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
  const newBuffer = ctx.createBuffer(numberOfChannels, newChannelData[0].length, sampleRate);
  
  for (let i = 0; i < numberOfChannels; i++) {
    newBuffer.getChannelData(i).set(newChannelData[i]);
  }

  return {
    buffer: newBuffer,
    sampleRate,
    duration,
    numberOfChannels,
    channelData: newChannelData,
  };
}

/**
 * Apply a volume function that varies over time
 */
export function applyVolumeEnvelope(
  audioData: AudioData,
  envelope: VolumeEnvelope
): AudioData {
  const { channelData, sampleRate, duration, numberOfChannels } = audioData;
  const { points, interpolate = 'linear' } = envelope;

  if (points.length === 0) {
    return audioData;
  }

  // Sort points by frame
  const sortedPoints = [...points].sort((a, b) => a.frame - b.frame);

  // Create new channel data with envelope applied
  const newChannelData = channelData.map((channel) => {
    const newChannel = new Float32Array(channel.length);
    
    for (let i = 0; i < channel.length; i++) {
      const time = i / sampleRate;
      const frame = time * 30; // Assuming 30fps
      const volume = interpolateVolume(sortedPoints, frame, interpolate);
      newChannel[i] = channel[i] * volume;
    }
    
    return newChannel;
  });

  // Create a new AudioBuffer
  const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
  const newBuffer = ctx.createBuffer(numberOfChannels, newChannelData[0].length, sampleRate);
  
  for (let i = 0; i < numberOfChannels; i++) {
    newBuffer.getChannelData(i).set(newChannelData[i]);
  }

  return {
    buffer: newBuffer,
    sampleRate,
    duration,
    numberOfChannels,
    channelData: newChannelData,
  };
}

/**
 * Interpolate volume between envelope points
 */
function interpolateVolume(
  points: EnvelopePoint[],
  frame: number,
  method: 'linear' | 'cubic'
): number {
  // Before first point
  if (frame <= points[0].frame) {
    return points[0].value;
  }

  // After last point
  if (frame >= points[points.length - 1].frame) {
    return points[points.length - 1].value;
  }

  // Find the two points to interpolate between
  let i = 0;
  while (i < points.length - 1 && points[i + 1].frame < frame) {
    i++;
  }

  const p0 = points[i];
  const p1 = points[i + 1];

  const t = (frame - p0.frame) / (p1.frame - p0.frame);

  if (method === 'cubic') {
    // Cubic interpolation (simplified)
    return p0.value + (p1.value - p0.value) * (3 * t * t - 2 * t * t * t);
  }

  // Linear interpolation
  return p0.value + (p1.value - p0.value) * t;
}

/**
 * Apply a volume function to audio data
 */
export function applyVolumeFunction(
  audioData: AudioData,
  volumeFn: VolumeFunction,
  fps: number = 30
): AudioData {
  const { channelData, sampleRate, duration, numberOfChannels } = audioData;

  // Create new channel data with function applied
  const newChannelData = channelData.map((channel) => {
    const newChannel = new Float32Array(channel.length);
    
    for (let i = 0; i < channel.length; i++) {
      const time = i / sampleRate;
      const frame = Math.floor(time * fps);
      const volume = clampVolume(volumeFn(frame));
      newChannel[i] = channel[i] * volume;
    }
    
    return newChannel;
  });

  // Create a new AudioBuffer
  const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
  const newBuffer = ctx.createBuffer(numberOfChannels, newChannelData[0].length, sampleRate);
  
  for (let i = 0; i < numberOfChannels; i++) {
    newBuffer.getChannelData(i).set(newChannelData[i]);
  }

  return {
    buffer: newBuffer,
    sampleRate,
    duration,
    numberOfChannels,
    channelData: newChannelData,
  };
}

/**
 * Normalize audio to a target peak level
 */
export function normalize(
  audioData: AudioData,
  targetPeak: number = 1.0
): AudioData {
  const { channelData } = audioData;
  
  // Find the current peak
  let currentPeak = 0;
  for (const channel of channelData) {
    for (let i = 0; i < channel.length; i++) {
      const abs = Math.abs(channel[i]);
      if (abs > currentPeak) {
        currentPeak = abs;
      }
    }
  }

  if (currentPeak === 0) {
    return audioData;
  }

  const gain = targetPeak / currentPeak;
  return applyVolume(audioData, gain);
}

/**
 * Apply gain in decibels
 */
export function applyGainDb(
  audioData: AudioData,
  gainDb: number
): AudioData {
  // Convert dB to linear gain
  const linearGain = Math.pow(10, gainDb / 20);
  return applyVolume(audioData, linearGain);
}

/**
 * Create a fade-in envelope
 */
export function createFadeIn(
  durationFrames: number,
  type: 'linear' | 'exponential' | 'logarithmic' = 'linear'
): VolumeEnvelope {
  const points: EnvelopePoint[] = [];

  switch (type) {
    case 'exponential':
      for (let i = 0; i <= durationFrames; i += 5) {
        const t = i / durationFrames;
        points.push({ frame: i, value: Math.pow(t, 2) });
      }
      break;
    case 'logarithmic':
      for (let i = 0; i <= durationFrames; i += 5) {
        const t = i / durationFrames;
        points.push({ frame: i, value: Math.log(1 + t * 9) / Math.log(10) });
      }
      break;
    default: // linear
      points.push({ frame: 0, value: 0 });
      points.push({ frame: durationFrames, value: 1 });
  }

  return { points, interpolate: 'linear' };
}

/**
 * Create a fade-out envelope
 */
export function createFadeOut(
  startFrame: number,
  durationFrames: number,
  type: 'linear' | 'exponential' | 'logarithmic' = 'linear'
): VolumeEnvelope {
  const points: EnvelopePoint[] = [];

  switch (type) {
    case 'exponential':
      for (let i = 0; i <= durationFrames; i += 5) {
        const t = i / durationFrames;
        points.push({ frame: startFrame + i, value: 1 - Math.pow(t, 2) });
      }
      break;
    case 'logarithmic':
      for (let i = 0; i <= durationFrames; i += 5) {
        const t = i / durationFrames;
        points.push({ frame: startFrame + i, value: 1 - Math.log(1 + t * 9) / Math.log(10) });
      }
      break;
    default: // linear
      points.push({ frame: startFrame, value: 1 });
      points.push({ frame: startFrame + durationFrames, value: 0 });
  }

  return { points, interpolate: 'linear' };
}