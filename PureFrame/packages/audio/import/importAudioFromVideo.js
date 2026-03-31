/**
 * Import audio from video files
 * Inspired by Remotion's audio-from-video feature
 */
import { decodeAudio, getAudioContext } from './decodeAudio';
/**
 * Extract audio from a video file URL
 */
export async function importAudioFromVideo(videoSrc, options = {}) {
    const { trackIndex = 0, startTime, endTime } = options;
    // Create a video element to load the video
    const video = document.createElement('video');
    video.crossOrigin = 'anonymous';
    video.preload = 'auto';
    return new Promise((resolve, reject) => {
        video.onloadedmetadata = async () => {
            try {
                // Fetch the video file
                const response = await fetch(videoSrc);
                if (!response.ok) {
                    throw new Error(`Failed to fetch video: ${response.statusText}`);
                }
                const buffer = await response.arrayBuffer();
                const audioData = await decodeAudio(buffer);
                // Apply time range if specified
                if (startTime !== undefined || endTime !== undefined) {
                    const trimmedData = await trimAudioData(audioData, startTime ?? 0, endTime ?? audioData.duration);
                    resolve(trimmedData);
                }
                else {
                    resolve(audioData);
                }
            }
            catch (error) {
                reject(error);
            }
        };
        video.onerror = () => {
            reject(new Error('Failed to load video'));
        };
        video.src = videoSrc;
    });
}
/**
 * Extract audio from a video element
 */
export async function importAudioFromVideoElement(video) {
    const response = await fetch(video.src);
    const buffer = await response.arrayBuffer();
    return decodeAudio(buffer);
}
/**
 * Extract audio from a video Blob
 */
export async function importAudioFromVideoBlob(blob) {
    const buffer = await blob.arrayBuffer();
    return decodeAudio(buffer);
}
/**
 * Extract audio from a MediaStream (e.g., screen recording)
 */
export async function importAudioFromMediaStream(stream) {
    const ctx = getAudioContext();
    const source = ctx.createMediaStreamSource(stream);
    // Create a recorder to capture the audio
    const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm',
    });
    const chunks = [];
    return new Promise((resolve, reject) => {
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                chunks.push(event.data);
            }
        };
        mediaRecorder.onstop = async () => {
            try {
                const blob = new Blob(chunks, { type: 'audio/webm' });
                const buffer = await blob.arrayBuffer();
                const audioData = await decodeAudio(buffer);
                resolve(audioData);
            }
            catch (error) {
                reject(error);
            }
        };
        mediaRecorder.onerror = (event) => {
            reject(new Error('MediaRecorder error'));
        };
        mediaRecorder.start();
        // Stop after a short delay (adjust as needed)
        setTimeout(() => {
            mediaRecorder.stop();
        }, 100);
    });
}
/**
 * Trim audio data to a specific time range
 */
async function trimAudioData(audioData, startTime, endTime) {
    const { sampleRate, numberOfChannels, channelData } = audioData;
    const startSample = Math.floor(startTime * sampleRate);
    const endSample = Math.floor(endTime * sampleRate);
    const length = endSample - startSample;
    if (length <= 0) {
        throw new Error('Invalid time range');
    }
    // Create trimmed channel data
    const trimmedChannelData = channelData.map((channel) => channel.slice(startSample, endSample));
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
 * Get video duration without loading the entire file
 */
export async function getVideoDuration(videoSrc) {
    const video = document.createElement('video');
    video.preload = 'metadata';
    return new Promise((resolve, reject) => {
        video.onloadedmetadata = () => {
            resolve(video.duration);
        };
        video.onerror = () => {
            reject(new Error('Failed to load video metadata'));
        };
        video.src = videoSrc;
    });
}
/**
 * Check if a video file contains audio tracks
 */
export async function hasAudioTrack(videoSrc) {
    try {
        const response = await fetch(videoSrc, { method: 'HEAD' });
        const contentType = response.headers.get('content-type') || '';
        // Common video formats that support audio
        const videoFormats = [
            'video/mp4',
            'video/webm',
            'video/ogg',
            'video/quicktime',
        ];
        return videoFormats.some((format) => contentType.includes(format));
    }
    catch {
        return false;
    }
}
/**
 * Get audio track information from a video
 */
export async function getVideoAudioInfo(videoSrc) {
    try {
        const audioData = await importAudioFromVideo(videoSrc);
        return {
            hasAudio: true,
            sampleRate: audioData.sampleRate,
            numberOfChannels: audioData.numberOfChannels,
            duration: audioData.duration,
        };
    }
    catch {
        return {
            hasAudio: false,
            sampleRate: 0,
            numberOfChannels: 0,
            duration: 0,
        };
    }
}
/**
 * Extract multiple audio tracks from a video (if available)
 */
export async function extractAudioTracks(videoSrc) {
    // Note: Most browsers only expose one audio track
    // This is a simplified implementation
    const audioData = await importAudioFromVideo(videoSrc);
    return [audioData];
}
/**
 * Create a preview audio clip from a video
 */
export async function createVideoAudioPreview(videoSrc, previewDuration = 5) {
    const fullAudio = await importAudioFromVideo(videoSrc);
    if (fullAudio.duration <= previewDuration) {
        return fullAudio;
    }
    return trimAudioData(fullAudio, 0, previewDuration);
}
//# sourceMappingURL=importAudioFromVideo.js.map