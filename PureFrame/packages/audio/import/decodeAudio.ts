/**
 * Audio decoding utilities
 */

import type { AudioData } from '../core/types';

/**
 * Audio context singleton for decoding
 */
let audioContext: AudioContext | null = null;

/**
 * Get or create the audio context
 */
export function getAudioContext(): AudioContext {
  if (!audioContext) {
    audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
  }
  return audioContext;
}

/**
 * Decode audio data from an ArrayBuffer
 */
export async function decodeAudio(
  buffer: ArrayBuffer,
  sampleRate?: number
): Promise<AudioData> {
  const ctx = getAudioContext();
  
  // Resume context if suspended (required by some browsers)
  if (ctx.state === 'suspended') {
    await ctx.resume();
  }

  const audioBuffer = await ctx.decodeAudioData(buffer);
  
  return extractAudioData(audioBuffer);
}

/**
 * Decode audio from a Blob
 */
export async function decodeAudioFromBlob(
  blob: Blob,
  sampleRate?: number
): Promise<AudioData> {
  const arrayBuffer = await blob.arrayBuffer();
  return decodeAudio(arrayBuffer, sampleRate);
}

/**
 * Decode audio from a URL
 */
export async function decodeAudioFromUrl(
  url: string,
  sampleRate?: number
): Promise<AudioData> {
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch audio: ${response.statusText}`);
  }
  
  const buffer = await response.arrayBuffer();
  return decodeAudio(buffer, sampleRate);
}

/**
 * Decode audio from an HTMLAudioElement
 */
export async function decodeAudioFromElement(
  audio: HTMLAudioElement,
  sampleRate?: number
): Promise<AudioData> {
  const response = await fetch(audio.src);
  const buffer = await response.arrayBuffer();
  return decodeAudio(buffer, sampleRate);
}

/**
 * Extract AudioData from an AudioBuffer
 */
export function extractAudioData(audioBuffer: AudioBuffer): AudioData {
  const channelData: Float32Array[] = [];
  
  for (let i = 0; i < audioBuffer.numberOfChannels; i++) {
    channelData.push(audioBuffer.getChannelData(i));
  }

  return {
    buffer: audioBuffer,
    sampleRate: audioBuffer.sampleRate,
    duration: audioBuffer.duration,
    numberOfChannels: audioBuffer.numberOfChannels,
    channelData,
  };
}

/**
 * Resample audio to a target sample rate
 */
export async function resampleAudio(
  audioData: AudioData,
  targetSampleRate: number
): Promise<AudioData> {
  if (audioData.sampleRate === targetSampleRate) {
    return audioData;
  }

  const ctx = getAudioContext();
  const { buffer } = audioData;

  // Create an offline context for resampling
  const duration = buffer.duration;
  const numberOfChannels = buffer.numberOfChannels;
  const offlineCtx = new OfflineAudioContext(
    numberOfChannels,
    duration * targetSampleRate,
    targetSampleRate
  );

  // Create a buffer source
  const source = offlineCtx.createBufferSource();
  source.buffer = buffer;
  source.connect(offlineCtx.destination);
  source.start(0);

  // Render the resampled audio
  const resampledBuffer = await offlineCtx.startRendering();
  
  return extractAudioData(resampledBuffer);
}

/**
 * Convert stereo to mono
 */
export function stereoToMono(audioData: AudioData): AudioData {
  if (audioData.numberOfChannels === 1) {
    return audioData;
  }

  const { buffer, sampleRate, duration, channelData } = audioData;
  const left = channelData[0];
  const right = channelData[1];
  const mono = new Float32Array(left.length);

  for (let i = 0; i < left.length; i++) {
    mono[i] = (left[i] + right[i]) / 2;
  }

  // Create a new AudioBuffer with mono channel
  const ctx = getAudioContext();
  const monoBuffer = ctx.createBuffer(1, mono.length, sampleRate);
  monoBuffer.getChannelData(0).set(mono);

  return {
    buffer: monoBuffer,
    sampleRate,
    duration,
    numberOfChannels: 1,
    channelData: [mono],
  };
}

/**
 * Convert mono to stereo
 */
export function monoToStereo(audioData: AudioData): AudioData {
  if (audioData.numberOfChannels === 2) {
    return audioData;
  }

  const { buffer, sampleRate, duration, channelData } = audioData;
  const mono = channelData[0];

  // Create a new AudioBuffer with stereo channels
  const ctx = getAudioContext();
  const stereoBuffer = ctx.createBuffer(2, mono.length, sampleRate);
  stereoBuffer.getChannelData(0).set(mono);
  stereoBuffer.getChannelData(1).set(mono);

  return {
    buffer: stereoBuffer,
    sampleRate,
    duration,
    numberOfChannels: 2,
    channelData: [mono, mono.slice()],
  };
}

/**
 * Get the peak amplitude of audio data
 */
export function getPeakAmplitude(audioData: AudioData): number {
  let peak = 0;
  
  for (const channel of audioData.channelData) {
    for (let i = 0; i < channel.length; i++) {
      const abs = Math.abs(channel[i]);
      if (abs > peak) {
        peak = abs;
      }
    }
  }
  
  return peak;
}

/**
 * Get the RMS (root mean square) of audio data
 */
export function getRMS(audioData: AudioData): number {
  let sumSquares = 0;
  let sampleCount = 0;
  
  for (const channel of audioData.channelData) {
    for (let i = 0; i < channel.length; i++) {
      sumSquares += channel[i] * channel[i];
      sampleCount++;
    }
  }
  
  return Math.sqrt(sumSquares / sampleCount);
}

/**
 * Check if audio data contains silence
 */
export function isSilent(
  audioData: AudioData,
  threshold: number = 0.001
): boolean {
  return getPeakAmplitude(audioData) < threshold;
}

/**
 * Dispose of the audio context (call when done)
 */
export function disposeAudioContext(): void {
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
}