/**
 * Audio waveform analysis utilities
 */
import type { AudioData, WaveformData, AnalysisOptions } from '../core/types';
/**
 * Get waveform data from audio
 */
export declare function getWaveform(audioData: AudioData, options?: {
    samples?: number;
    channel?: number;
}): WaveformData;
/**
 * Get waveform peaks only (for visualization)
 */
export declare function getWaveformPeaks(audioData: AudioData, numberOfPeaks?: number, channel?: number): number[];
/**
 * Get min/max waveform data (for detailed visualization)
 */
export declare function getWaveformMinMax(audioData: AudioData, numberOfSegments?: number, channel?: number): Array<{
    min: number;
    max: number;
}>;
/**
 * Get average waveform (combines multiple channels)
 */
export declare function getAverageWaveform(audioData: AudioData, samples?: number): number[];
/**
 * Get waveform at a specific time
 */
export declare function getWaveformAtTime(audioData: AudioData, timeMs: number, windowMs?: number, channel?: number): number[];
/**
 * Get spectrogram data (frequency over time)
 */
export declare function getSpectrogram(audioData: AudioData, options?: AnalysisOptions & {
    windowSize?: number;
    hopSize?: number;
}): number[][];
/**
 * Get zero crossing rate (useful for percussion detection)
 */
export declare function getZeroCrossingRate(audioData: AudioData, windowMs?: number, channel?: number): number[];
/**
 * Get spectral centroid (brightness indicator)
 */
export declare function getSpectralCentroid(audioData: AudioData, windowMs?: number): number[];
//# sourceMappingURL=getWaveform.d.ts.map