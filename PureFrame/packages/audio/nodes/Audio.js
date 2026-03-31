/**
 * Audio node - high-level API for creating audio clips
 * Inspired by Remotion's Audio component
 */
import { AudioClip } from '../core/AudioClip';
import { getAsset } from '../assets/registry';
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
export function Audio(config) {
    // Resolve asset
    let asset;
    if (typeof config.asset === 'string') {
        const registryAsset = getAsset(config.asset);
        if (!registryAsset) {
            throw new Error(`Audio asset not found: ${config.asset}`);
        }
        asset = registryAsset;
    }
    else {
        asset = config.asset;
    }
    return new AudioClip(config, asset);
}
/**
 * Create an audio node from a local file path
 */
export function LocalAudio(path, config = {}) {
    return Audio({
        ...config,
        asset: {
            id: `local-${Date.now()}`,
            src: path,
        },
    });
}
/**
 * Create an audio node from a remote URL
 */
export function RemoteAudio(url, config = {}) {
    return Audio({
        ...config,
        asset: {
            id: `remote-${Date.now()}`,
            src: url,
        },
    });
}
/**
 * Create multiple audio nodes from an array of configs
 */
export function AudioSequence(configs) {
    return configs.map((config) => Audio(config));
}
/**
 * Helper to create an audio clip with specific timing
 */
export function AudioAt(frame, assetId, options = {}) {
    return Audio({
        asset: assetId,
        from: frame,
        ...options,
    });
}
/**
 * Helper to create an audio clip that plays for a specific duration
 */
export function AudioWithDuration(assetId, durationMs, options = {}) {
    return Audio({
        asset: assetId,
        trimAfter: durationMs,
        ...options,
    });
}
/**
 * Helper to create a looping audio clip
 */
export function LoopingAudio(assetId, loopCount, options = {}) {
    const asset = getAsset(assetId);
    if (!asset) {
        throw new Error(`Audio asset not found: ${assetId}`);
    }
    const durationMs = asset.durationMs ?? 0;
    const clips = [];
    for (let i = 0; i < loopCount; i++) {
        clips.push(Audio({
            asset: assetId,
            from: (options.from ?? 0) + i * (durationMs / 1000) * 30, // Assuming 30fps
            ...options,
        }));
    }
    return clips;
}
export default Audio;
//# sourceMappingURL=Audio.js.map