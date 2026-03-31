/**
 * Silence detection utilities
 */

import type { AudioData, SilenceRegion, SilenceDetectionOptions } from '../core/types';

/**
 * Detect silence regions in audio data
 */
export function detectSilence(
  audioData: AudioData,
  options: SilenceDetectionOptions = { threshold: 0.01, minDuration: 100 }
): SilenceRegion[] {
  const { channelData, sampleRate } = audioData;
  const { threshold, minDuration } = options;

  const data = channelData[0];
  const minSamples = Math.floor((minDuration / 1000) * sampleRate);

  const regions: SilenceRegion[] = [];
  let silenceStart = -1;

  for (let i = 0; i < data.length; i++) {
    const isSilent = Math.abs(data[i]) < threshold;

    if (isSilent && silenceStart === -1) {
      silenceStart = i;
    } else if (!isSilent && silenceStart !== -1) {
      const duration = i - silenceStart;
      if (duration >= minSamples) {
        regions.push({
          start: (silenceStart / sampleRate) * 1000,
          end: (i / sampleRate) * 1000,
          duration: (duration / sampleRate) * 1000,
        });
      }
      silenceStart = -1;
    }
  }

  // Handle trailing silence
  if (silenceStart !== -1) {
    const duration = data.length - silenceStart;
    if (duration >= minSamples) {
      regions.push({
        start: (silenceStart / sampleRate) * 1000,
        end: (data.length / sampleRate) * 1000,
        duration: (duration / sampleRate) * 1000,
      });
    }
  }

  return regions;
}

/**
 * Detect leading silence
 */
export function detectLeadingSilence(
  audioData: AudioData,
  threshold: number = 0.01
): number {
  const { channelData, sampleRate } = audioData;
  const data = channelData[0];

  for (let i = 0; i < data.length; i++) {
    if (Math.abs(data[i]) >= threshold) {
      return (i / sampleRate) * 1000;
    }
  }

  return audioData.duration * 1000;
}

/**
 * Detect trailing silence
 */
export function detectTrailingSilence(
  audioData: AudioData,
  threshold: number = 0.01
): number {
  const { channelData, sampleRate } = audioData;
  const data = channelData[0];

  for (let i = data.length - 1; i >= 0; i--) {
    if (Math.abs(data[i]) >= threshold) {
      return ((data.length - i - 1) / sampleRate) * 1000;
    }
  }

  return audioData.duration * 1000;
}

/**
 * Check if audio is entirely silent
 */
export function isEntirelySilent(
  audioData: AudioData,
  threshold: number = 0.01
): boolean {
  const { channelData } = audioData;

  for (const channel of channelData) {
    for (let i = 0; i < channel.length; i++) {
      if (Math.abs(channel[i]) >= threshold) {
        return false;
      }
    }
  }

  return true;
}

/**
 * Get silence ratio (percentage of silence)
 */
export function getSilenceRatio(
  audioData: AudioData,
  threshold: number = 0.01
): number {
  const { channelData } = audioData;
  const data = channelData[0];

  let silentSamples = 0;
  for (let i = 0; i < data.length; i++) {
    if (Math.abs(data[i]) < threshold) {
      silentSamples++;
    }
  }

  return silentSamples / data.length;
}

/**
 * Find first non-silent sample
 */
export function findFirstNonSilentSample(
  audioData: AudioData,
  threshold: number = 0.01
): number {
  const { channelData } = audioData;
  const data = channelData[0];

  for (let i = 0; i < data.length; i++) {
    if (Math.abs(data[i]) >= threshold) {
      return i;
    }
  }

  return -1;
}

/**
 * Find last non-silent sample
 */
export function findLastNonSilentSample(
  audioData: AudioData,
  threshold: number = 0.01
): number {
  const { channelData } = audioData;
  const data = channelData[0];

  for (let i = data.length - 1; i >= 0; i--) {
    if (Math.abs(data[i]) >= threshold) {
      return i;
    }
  }

  return -1;
}

/**
 * Get non-silent duration
 */
export function getNonSilentDuration(
  audioData: AudioData,
  threshold: number = 0.01
): number {
  const { channelData, sampleRate } = audioData;
  const data = channelData[0];

  const first = findFirstNonSilentSample(audioData, threshold);
  const last = findLastNonSilentSample(audioData, threshold);

  if (first === -1 || last === -1) {
    return 0;
  }

  return ((last - first + 1) / sampleRate) * 1000;
}

/**
 * Detect silence at specific time
 */
export function isSilentAtTime(
  audioData: AudioData,
  timeMs: number,
  threshold: number = 0.01
): boolean {
  const { channelData, sampleRate } = audioData;
  const sampleIndex = Math.floor((timeMs / 1000) * sampleRate);

  if (sampleIndex < 0 || sampleIndex >= channelData[0].length) {
    return true;
  }

  return Math.abs(channelData[0][sampleIndex]) < threshold;
}

/**
 * Get silence regions with custom window
 */
export function detectSilenceWithWindow(
  audioData: AudioData,
  windowMs: number,
  threshold: number = 0.01
): Array<{ start: number; end: number; isSilent: boolean }> {
  const { channelData, sampleRate, duration } = audioData;
  const data = channelData[0];
  const windowSamples = Math.floor((windowMs / 1000) * sampleRate);

  const regions: Array<{ start: number; end: number; isSilent: boolean }> = [];

  for (let i = 0; i < data.length; i += windowSamples) {
    const end = Math.min(i + windowSamples, data.length);
    let maxAmplitude = 0;

    for (let j = i; j < end; j++) {
      const abs = Math.abs(data[j]);
      if (abs > maxAmplitude) {
        maxAmplitude = abs;
      }
    }

    regions.push({
      start: (i / sampleRate) * 1000,
      end: (end / sampleRate) * 1000,
      isSilent: maxAmplitude < threshold,
    });
  }

  return regions;
}