/**
 * Audio node - high-level API for creating audio clips
 * Inspired by Remotion's Audio component
 */
import type { AudioClipConfig } from '../core/types';
import { AudioClip } from '../core/AudioClip';
/**
 * Create an audio node with the given configuration
 *
 * @example
 * ```ts
 * // Using a registry asset
 * const clip = Audio({ asset: 'whip', from: 30, volume: 0.8 });
 *
 * // Using a custom asset
 * const clip = Audio({
 *   asset: { id: 'custom', src: '/path/to/audio.wav' },
 *   from: 0,
 *   trimBefore: 100,
 *   trimAfter: 500
 * });
 * ```
 */
export declare function Audio(config: AudioClipConfig): AudioClip;
/**
 * Create an audio node from a local file path
 */
export declare function LocalAudio(path: string, config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
/**
 * Create an audio node from a remote URL
 */
export declare function RemoteAudio(url: string, config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
/**
 * Create multiple audio nodes from an array of configs
 */
export declare function AudioSequence(configs: AudioClipConfig[]): AudioClip[];
/**
 * Helper to create an audio clip with specific timing
 */
export declare function AudioAt(frame: number, assetId: string, options?: Omit<AudioClipConfig, 'asset' | 'from'>): AudioClip;
/**
 * Helper to create an audio clip that plays for a specific duration
 */
export declare function AudioWithDuration(assetId: string, durationMs: number, options?: Omit<AudioClipConfig, 'asset' | 'trimAfter'>): AudioClip;
/**
 * Helper to create a looping audio clip
 */
export declare function LoopingAudio(assetId: string, loopCount: number, options?: Omit<AudioClipConfig, 'asset'>): AudioClip[];
export default Audio;
//# sourceMappingURL=Audio.d.ts.map