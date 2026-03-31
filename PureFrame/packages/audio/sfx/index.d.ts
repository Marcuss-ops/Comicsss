/**
 * SFX Library - Ready-to-use sound effects
 * Import directly: import { whip, glitchHit } from './sfx'
 */
export { audioRegistry, getAsset, getAssetsByTag, getAssetsByCategory, searchAssets, getAllAssets, hasAsset, } from '../assets/registry';
export type { AudioAsset } from '../core/types';
export { Sfx, SfxBatch, SfxAt, SfxSequence, RandomSfx, LayeredSfx, Whoosh, Impact, Glitch, UiSound, Notification, Riser, Drop, } from '../nodes/Sfx';
export type { SfxName } from '../nodes/Sfx';
import { type SfxName } from '../nodes/Sfx';
import type { AudioClipConfig } from '../core/types';
export declare const whip: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const whooshFast: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const whooshSlow: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const swoosh: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const impactShort: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const impactDeep: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const punch: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const thud: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const glitchHit: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const glitchShort: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const staticNoise: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const click: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const pop: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const tap: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const notification: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const alert: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const ding: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const riser: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const buildup: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const drop: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const boom: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const sparkle: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const shimmer: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const blip: (config?: Omit<AudioClipConfig, "asset">) => any;
export declare const boop: (config?: Omit<AudioClipConfig, "asset">) => any;
/**
 * Category-based access
 */
export declare const sfx: {
    transitions: {
        whip: (config?: Omit<AudioClipConfig, "asset">) => any;
        whooshFast: (config?: Omit<AudioClipConfig, "asset">) => any;
        whooshSlow: (config?: Omit<AudioClipConfig, "asset">) => any;
        swoosh: (config?: Omit<AudioClipConfig, "asset">) => any;
    };
    impacts: {
        short: (config?: Omit<AudioClipConfig, "asset">) => any;
        deep: (config?: Omit<AudioClipConfig, "asset">) => any;
        punch: (config?: Omit<AudioClipConfig, "asset">) => any;
        thud: (config?: Omit<AudioClipConfig, "asset">) => any;
    };
    glitch: {
        hit: (config?: Omit<AudioClipConfig, "asset">) => any;
        short: (config?: Omit<AudioClipConfig, "asset">) => any;
        static: (config?: Omit<AudioClipConfig, "asset">) => any;
    };
    ui: {
        click: (config?: Omit<AudioClipConfig, "asset">) => any;
        pop: (config?: Omit<AudioClipConfig, "asset">) => any;
        tap: (config?: Omit<AudioClipConfig, "asset">) => any;
    };
    notifications: {
        notification: (config?: Omit<AudioClipConfig, "asset">) => any;
        alert: (config?: Omit<AudioClipConfig, "asset">) => any;
        ding: (config?: Omit<AudioClipConfig, "asset">) => any;
    };
    risers: {
        riser: (config?: Omit<AudioClipConfig, "asset">) => any;
        buildup: (config?: Omit<AudioClipConfig, "asset">) => any;
    };
    drops: {
        drop: (config?: Omit<AudioClipConfig, "asset">) => any;
        boom: (config?: Omit<AudioClipConfig, "asset">) => any;
    };
    misc: {
        sparkle: (config?: Omit<AudioClipConfig, "asset">) => any;
        shimmer: (config?: Omit<AudioClipConfig, "asset">) => any;
        blip: (config?: Omit<AudioClipConfig, "asset">) => any;
        boop: (config?: Omit<AudioClipConfig, "asset">) => any;
    };
    byName: (name: SfxName, config?: Omit<AudioClipConfig, "asset">) => any;
};
export default sfx;
//# sourceMappingURL=index.d.ts.map