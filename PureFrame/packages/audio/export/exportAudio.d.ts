/**
 * Audio export utilities
 */
import type { AudioData, AudioExportConfig, AudioExportFormat } from '../core/types';
/**
 * Export audio data to a specific format
 */
export declare function exportAudio(audioData: AudioData, config: AudioExportConfig): Promise<Blob>;
/**
 * Export audio to WAV format
 */
export declare function exportWav(audioData: AudioData, options?: {
    sampleRate?: number;
    bitDepth?: 16 | 24 | 32;
    channels?: 1 | 2;
    normalize?: boolean;
}): Blob;
/**
 * Export audio to MP3 format (requires external encoder)
 */
export declare function exportMp3(audioData: AudioData, options?: {
    bitrate?: number;
    normalize?: boolean;
}): Promise<Blob>;
/**
 * Export audio to AAC format (requires external encoder)
 */
export declare function exportAac(audioData: AudioData, options?: {
    bitrate?: number;
    normalize?: boolean;
}): Promise<Blob>;
/**
 * Download audio as file
 */
export declare function downloadAudio(blob: Blob, filename: string): void;
/**
 * Create audio URL for playback
 */
export declare function createAudioUrl(blob: Blob): string;
/**
 * Revoke audio URL
 */
export declare function revokeAudioUrl(url: string): void;
/**
 * Get export file extension
 */
export declare function getExportExtension(format: AudioExportFormat): string;
/**
 * Get MIME type for format
 */
export declare function getMimeType(format: AudioExportFormat): string;
//# sourceMappingURL=exportAudio.d.ts.map