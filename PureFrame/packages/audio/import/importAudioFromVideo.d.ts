/**
 * Import audio from video files
 * Inspired by Remotion's audio-from-video feature
 */
import type { AudioData } from '../core/types';
/**
 * Extract audio from a video file URL
 */
export declare function importAudioFromVideo(videoSrc: string, options?: {
    trackIndex?: number;
    startTime?: number;
    endTime?: number;
}): Promise<AudioData>;
/**
 * Extract audio from a video element
 */
export declare function importAudioFromVideoElement(video: HTMLVideoElement): Promise<AudioData>;
/**
 * Extract audio from a video Blob
 */
export declare function importAudioFromVideoBlob(blob: Blob): Promise<AudioData>;
/**
 * Extract audio from a MediaStream (e.g., screen recording)
 */
export declare function importAudioFromMediaStream(stream: MediaStream): Promise<AudioData>;
/**
 * Get video duration without loading the entire file
 */
export declare function getVideoDuration(videoSrc: string): Promise<number>;
/**
 * Check if a video file contains audio tracks
 */
export declare function hasAudioTrack(videoSrc: string): Promise<boolean>;
/**
 * Get audio track information from a video
 */
export declare function getVideoAudioInfo(videoSrc: string): Promise<{
    hasAudio: boolean;
    sampleRate: number;
    numberOfChannels: number;
    duration: number;
}>;
/**
 * Extract multiple audio tracks from a video (if available)
 */
export declare function extractAudioTracks(videoSrc: string): Promise<AudioData[]>;
/**
 * Create a preview audio clip from a video
 */
export declare function createVideoAudioPreview(videoSrc: string, previewDuration?: number): Promise<AudioData>;
//# sourceMappingURL=importAudioFromVideo.d.ts.map