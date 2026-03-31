/**
 * Audio export utilities
 */

import type { AudioData, AudioExportConfig, AudioExportFormat } from '../core/types';

/**
 * Export audio data to a specific format
 */
export async function exportAudio(
  audioData: AudioData,
  config: AudioExportConfig
): Promise<Blob> {
  const { format, sampleRate, bitDepth = 16, channels = 2, normalize = true } = config;

  switch (format) {
    case 'wav':
      return exportWav(audioData, { sampleRate, bitDepth, channels, normalize });
    case 'mp3':
      return exportMp3(audioData, { bitrate: config.bitrate ?? 128, normalize });
    case 'aac':
      return exportAac(audioData, { bitrate: config.bitrate ?? 128, normalize });
    default:
      throw new Error(`Unsupported format: ${format}`);
  }
}

/**
 * Export audio to WAV format
 */
export function exportWav(
  audioData: AudioData,
  options: {
    sampleRate?: number;
    bitDepth?: 16 | 24 | 32;
    channels?: 1 | 2;
    normalize?: boolean;
  } = {}
): Blob {
  const {
    sampleRate = audioData.sampleRate,
    bitDepth = 16,
    channels = 2,
    normalize = true,
  } = options;

  const { channelData, numberOfChannels } = audioData;
  
  // Prepare audio data
  let processedData = channelData;
  if (normalize) {
    processedData = normalizeAudioData(channelData);
  }

  // Convert to target channels
  const outputChannels = channels === 1 ? mixToMono(processedData) : processedData;

  // Calculate sizes
  const bytesPerSample = bitDepth / 8;
  const numSamples = outputChannels[0].length;
  const dataSize = numSamples * channels * bytesPerSample;
  const bufferSize = 44 + dataSize;

  // Create buffer
  const buffer = new ArrayBuffer(bufferSize);
  const view = new DataView(buffer);

  // Write WAV header
  writeWavHeader(view, {
    sampleRate,
    bitDepth,
    channels,
    numSamples,
  });

  // Write audio data
  const offset = 44;
  writeAudioData(view, outputChannels, offset, bitDepth, channels);

  return new Blob([buffer], { type: 'audio/wav' });
}

/**
 * Export audio to MP3 format (requires external encoder)
 */
export async function exportMp3(
  audioData: AudioData,
  options: {
    bitrate?: number;
    normalize?: boolean;
  } = {}
): Promise<Blob> {
  const { bitrate = 128, normalize = true } = options;

  // Note: This is a placeholder. In production, use a library like lamejs
  // or send to a server-side encoder
  console.warn('MP3 encoding requires external library. Falling back to WAV.');
  return exportWav(audioData, { normalize });
}

/**
 * Export audio to AAC format (requires external encoder)
 */
export async function exportAac(
  audioData: AudioData,
  options: {
    bitrate?: number;
    normalize?: boolean;
  } = {}
): Promise<Blob> {
  const { bitrate = 128, normalize = true } = options;

  // Note: This is a placeholder. In production, use a library or server-side encoder
  console.warn('AAC encoding requires external library. Falling back to WAV.');
  return exportWav(audioData, { normalize });
}

/**
 * Write WAV file header
 */
function writeWavHeader(
  view: DataView,
  options: {
    sampleRate: number;
    bitDepth: number;
    channels: number;
    numSamples: number;
  }
): void {
  const { sampleRate, bitDepth, channels, numSamples } = options;
  const bytesPerSample = bitDepth / 8;
  const dataSize = numSamples * channels * bytesPerSample;

  // RIFF header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeString(view, 8, 'WAVE');

  // fmt chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // chunk size
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, channels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * channels * bytesPerSample, true); // byte rate
  view.setUint16(32, channels * bytesPerSample, true); // block align
  view.setUint16(34, bitDepth, true);

  // data chunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataSize, true);
}

/**
 * Write audio samples to DataView
 */
function writeAudioData(
  view: DataView,
  channelData: Float32Array[],
  offset: number,
  bitDepth: number,
  channels: number
): void {
  const numSamples = channelData[0].length;
  let pos = offset;

  for (let i = 0; i < numSamples; i++) {
    for (let ch = 0; ch < channels; ch++) {
      const sample = channelData[ch]?.[i] ?? 0;
      const intSample = floatToInt(sample, bitDepth);

      switch (bitDepth) {
        case 16:
          view.setInt16(pos, intSample, true);
          pos += 2;
          break;
        case 24:
          view.setInt8(pos, intSample & 0xff);
          view.setInt8(pos + 1, (intSample >> 8) & 0xff);
          view.setInt8(pos + 2, (intSample >> 16) & 0xff);
          pos += 3;
          break;
        case 32:
          view.setInt32(pos, intSample, true);
          pos += 4;
          break;
      }
    }
  }
}

/**
 * Convert float sample to integer
 */
function floatToInt(sample: number, bitDepth: number): number {
  const max = Math.pow(2, bitDepth - 1) - 1;
  return Math.round(sample * max);
}

/**
 * Write string to DataView
 */
function writeString(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

/**
 * Normalize audio data to peak at 1.0
 */
function normalizeAudioData(channelData: Float32Array[]): Float32Array[] {
  let peak = 0;

  for (const channel of channelData) {
    for (let i = 0; i < channel.length; i++) {
      const abs = Math.abs(channel[i]);
      if (abs > peak) peak = abs;
    }
  }

  if (peak === 0 || peak === 1) {
    return channelData;
  }

  const gain = 1 / peak;
  return channelData.map((channel) => {
    const normalized = new Float32Array(channel.length);
    for (let i = 0; i < channel.length; i++) {
      normalized[i] = channel[i] * gain;
    }
    return normalized;
  });
}

/**
 * Mix multiple channels to mono
 */
function mixToMono(channelData: Float32Array[]): Float32Array[] {
  if (channelData.length === 1) {
    return channelData;
  }

  const length = channelData[0].length;
  const mono = new Float32Array(length);

  for (let i = 0; i < length; i++) {
    let sum = 0;
    for (const channel of channelData) {
      sum += channel[i];
    }
    mono[i] = sum / channelData.length;
  }

  return [mono];
}

/**
 * Download audio as file
 */
export function downloadAudio(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Create audio URL for playback
 */
export function createAudioUrl(blob: Blob): string {
  return URL.createObjectURL(blob);
}

/**
 * Revoke audio URL
 */
export function revokeAudioUrl(url: string): void {
  URL.revokeObjectURL(url);
}

/**
 * Get export file extension
 */
export function getExportExtension(format: AudioExportFormat): string {
  const extensions: Record<AudioExportFormat, string> = {
    wav: '.wav',
    mp3: '.mp3',
    aac: '.aac',
    ogg: '.ogg',
    flac: '.flac',
  };
  return extensions[format];
}

/**
 * Get MIME type for format
 */
export function getMimeType(format: AudioExportFormat): string {
  const mimeTypes: Record<AudioExportFormat, string> = {
    wav: 'audio/wav',
    mp3: 'audio/mpeg',
    aac: 'audio/aac',
    ogg: 'audio/ogg',
    flac: 'audio/flac',
  };
  return mimeTypes[format];
}