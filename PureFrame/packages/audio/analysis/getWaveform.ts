/**
 * Audio waveform analysis utilities
 */

import type { AudioData, WaveformData, WaveformPeak, AnalysisOptions } from '../core/types';

/**
 * Get waveform data from audio
 */
export function getWaveform(
  audioData: AudioData,
  options: {
    samples?: number;
    channel?: number;
  } = {}
): WaveformData {
  const { samples = 1000, channel = 0 } = options;
  const { channelData, sampleRate, duration } = audioData;

  if (channel >= channelData.length) {
    throw new Error(`Channel ${channel} not available`);
  }

  const data = channelData[channel];
  const samplesPerPixel = Math.floor(data.length / samples);
  const waveformSamples: number[] = [];
  const peaks: WaveformPeak[] = [];

  for (let i = 0; i < samples; i++) {
    const start = i * samplesPerPixel;
    const end = Math.min(start + samplesPerPixel, data.length);

    let min = 0;
    let max = 0;
    let sum = 0;

    for (let j = start; j < end; j++) {
      const sample = data[j];
      sum += sample;
      if (sample < min) min = sample;
      if (sample > max) max = sample;
    }

    const avg = sum / (end - start);
    waveformSamples.push(avg);

    peaks.push({
      time: (start / data.length) * duration,
      value: avg,
      min,
      max,
    });
  }

  return {
    samples: waveformSamples,
    duration,
    sampleRate,
    peaks,
  };
}

/**
 * Get waveform peaks only (for visualization)
 */
export function getWaveformPeaks(
  audioData: AudioData,
  numberOfPeaks: number = 100,
  channel: number = 0
): number[] {
  const { channelData } = audioData;
  const data = channelData[channel];
  const samplesPerPeak = Math.floor(data.length / numberOfPeaks);
  const peaks: number[] = [];

  for (let i = 0; i < numberOfPeaks; i++) {
    const start = i * samplesPerPeak;
    const end = Math.min(start + samplesPerPeak, data.length);

    let peak = 0;
    for (let j = start; j < end; j++) {
      const abs = Math.abs(data[j]);
      if (abs > peak) peak = abs;
    }

    peaks.push(peak);
  }

  return peaks;
}

/**
 * Get min/max waveform data (for detailed visualization)
 */
export function getWaveformMinMax(
  audioData: AudioData,
  numberOfSegments: number = 1000,
  channel: number = 0
): Array<{ min: number; max: number }> {
  const { channelData } = audioData;
  const data = channelData[channel];
  const samplesPerSegment = Math.floor(data.length / numberOfSegments);
  const result: Array<{ min: number; max: number }> = [];

  for (let i = 0; i < numberOfSegments; i++) {
    const start = i * samplesPerSegment;
    const end = Math.min(start + samplesPerSegment, data.length);

    let min = 0;
    let max = 0;

    for (let j = start; j < end; j++) {
      const sample = data[j];
      if (sample < min) min = sample;
      if (sample > max) max = sample;
    }

    result.push({ min, max });
  }

  return result;
}

/**
 * Get average waveform (combines multiple channels)
 */
export function getAverageWaveform(
  audioData: AudioData,
  samples: number = 1000
): number[] {
  const { channelData, numberOfChannels } = audioData;
  const samplesPerSegment = Math.floor(channelData[0].length / samples);
  const result: number[] = [];

  for (let i = 0; i < samples; i++) {
    let sum = 0;
    let count = 0;

    for (let ch = 0; ch < numberOfChannels; ch++) {
      const data = channelData[ch];
      const start = i * samplesPerSegment;
      const end = Math.min(start + samplesPerSegment, data.length);

      for (let j = start; j < end; j++) {
        sum += Math.abs(data[j]);
        count++;
      }
    }

    result.push(sum / count);
  }

  return result;
}

/**
 * Get waveform at a specific time
 */
export function getWaveformAtTime(
  audioData: AudioData,
  timeMs: number,
  windowMs: number = 50,
  channel: number = 0
): number[] {
  const { channelData, sampleRate } = audioData;
  const data = channelData[channel];

  const startSample = Math.floor((timeMs / 1000) * sampleRate);
  const windowSamples = Math.floor((windowMs / 1000) * sampleRate);
  const endSample = Math.min(startSample + windowSamples, data.length);

  const result: number[] = [];
  for (let i = startSample; i < endSample; i++) {
    result.push(data[i] || 0);
  }

  return result;
}

/**
 * Get spectrogram data (frequency over time)
 */
export function getSpectrogram(
  audioData: AudioData,
  options: AnalysisOptions & {
    windowSize?: number;
    hopSize?: number;
  } = {}
): number[][] {
  const { fftSize = 2048, windowSize = fftSize, hopSize = windowSize / 2 } = options;
  const { channelData, sampleRate } = audioData;
  const data = channelData[0];

  const spectrogram: number[][] = [];
  const numFrames = Math.floor((data.length - windowSize) / hopSize) + 1;

  for (let frame = 0; frame < numFrames; frame++) {
    const start = frame * hopSize;
    const window = data.slice(start, start + windowSize);

    // Apply Hanning window
    const windowed = new Float32Array(windowSize);
    for (let i = 0; i < windowSize; i++) {
      const multiplier = 0.5 * (1 - Math.cos((2 * Math.PI * i) / (windowSize - 1)));
      windowed[i] = window[i] * multiplier;
    }

    // Simple DFT (for production, use FFT)
    const magnitudes: number[] = [];
    const halfSize = windowSize / 2;

    for (let k = 0; k < halfSize; k++) {
      let real = 0;
      let imag = 0;

      for (let n = 0; n < windowSize; n++) {
        const angle = (2 * Math.PI * k * n) / windowSize;
        real += windowed[n] * Math.cos(angle);
        imag -= windowed[n] * Math.sin(angle);
      }

      const magnitude = Math.sqrt(real * real + imag * imag);
      magnitudes.push(magnitude);
    }

    spectrogram.push(magnitudes);
  }

  return spectrogram;
}

/**
 * Get zero crossing rate (useful for percussion detection)
 */
export function getZeroCrossingRate(
  audioData: AudioData,
  windowMs: number = 10,
  channel: number = 0
): number[] {
  const { channelData, sampleRate } = audioData;
  const data = channelData[channel];
  const windowSamples = Math.floor((windowMs / 1000) * sampleRate);
  const numWindows = Math.floor(data.length / windowSamples);
  const rates: number[] = [];

  for (let i = 0; i < numWindows; i++) {
    const start = i * windowSamples;
    const end = Math.min(start + windowSamples, data.length);

    let crossings = 0;
    for (let j = start + 1; j < end; j++) {
      if ((data[j] >= 0 && data[j - 1] < 0) || (data[j] < 0 && data[j - 1] >= 0)) {
        crossings++;
      }
    }

    rates.push(crossings / (end - start));
  }

  return rates;
}

/**
 * Get spectral centroid (brightness indicator)
 */
export function getSpectralCentroid(
  audioData: AudioData,
  windowMs: number = 50
): number[] {
  const spectrogram = getSpectrogram(audioData, {
    windowSize: Math.floor((windowMs / 1000) * audioData.sampleRate),
  });

  const centroids: number[] = [];

  for (const frame of spectrogram) {
    let weightedSum = 0;
    let totalMagnitude = 0;

    for (let i = 0; i < frame.length; i++) {
      weightedSum += i * frame[i];
      totalMagnitude += frame[i];
    }

    centroids.push(totalMagnitude > 0 ? weightedSum / totalMagnitude : 0);
  }

  return centroids;
}