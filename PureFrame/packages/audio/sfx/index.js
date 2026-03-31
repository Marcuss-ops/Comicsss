/**
 * SFX Library - Ready-to-use sound effects
 * Import directly: import { whip, glitchHit } from './sfx'
 */
export { audioRegistry, getAsset, getAssetsByTag, getAssetsByCategory, searchAssets, getAllAssets, hasAsset, } from '../assets/registry';
// Re-export the Sfx node and helpers
export { Sfx, SfxBatch, SfxAt, SfxSequence, RandomSfx, LayeredSfx, Whoosh, Impact, Glitch, UiSound, Notification, Riser, Drop, } from '../nodes/Sfx';
// Named exports for common sound effects (convenience)
import { Sfx } from '../nodes/Sfx';
// Transitions
export const whip = (config) => Sfx('whip', config);
export const whooshFast = (config) => Sfx('whooshFast', config);
export const whooshSlow = (config) => Sfx('whooshSlow', config);
export const swoosh = (config) => Sfx('swoosh', config);
// Impacts
export const impactShort = (config) => Sfx('impactShort', config);
export const impactDeep = (config) => Sfx('impactDeep', config);
export const punch = (config) => Sfx('punch', config);
export const thud = (config) => Sfx('thud', config);
// Glitch
export const glitchHit = (config) => Sfx('glitchHit', config);
export const glitchShort = (config) => Sfx('glitchShort', config);
export const staticNoise = (config) => Sfx('static', config);
// UI
export const click = (config) => Sfx('click', config);
export const pop = (config) => Sfx('pop', config);
export const tap = (config) => Sfx('tap', config);
// Notifications
export const notification = (config) => Sfx('notification', config);
export const alert = (config) => Sfx('alert', config);
export const ding = (config) => Sfx('ding', config);
// Riser/Build
export const riser = (config) => Sfx('riser', config);
export const buildup = (config) => Sfx('buildup', config);
// Drop/Release
export const drop = (config) => Sfx('drop', config);
export const boom = (config) => Sfx('boom', config);
// Misc
export const sparkle = (config) => Sfx('sparkle', config);
export const shimmer = (config) => Sfx('shimmer', config);
export const blip = (config) => Sfx('blip', config);
export const boop = (config) => Sfx('boop', config);
/**
 * Category-based access
 */
export const sfx = {
    // By category
    transitions: {
        whip: (config) => Sfx('whip', config),
        whooshFast: (config) => Sfx('whooshFast', config),
        whooshSlow: (config) => Sfx('whooshSlow', config),
        swoosh: (config) => Sfx('swoosh', config),
    },
    impacts: {
        short: (config) => Sfx('impactShort', config),
        deep: (config) => Sfx('impactDeep', config),
        punch: (config) => Sfx('punch', config),
        thud: (config) => Sfx('thud', config),
    },
    glitch: {
        hit: (config) => Sfx('glitchHit', config),
        short: (config) => Sfx('glitchShort', config),
        static: (config) => Sfx('static', config),
    },
    ui: {
        click: (config) => Sfx('click', config),
        pop: (config) => Sfx('pop', config),
        tap: (config) => Sfx('tap', config),
    },
    notifications: {
        notification: (config) => Sfx('notification', config),
        alert: (config) => Sfx('alert', config),
        ding: (config) => Sfx('ding', config),
    },
    risers: {
        riser: (config) => Sfx('riser', config),
        buildup: (config) => Sfx('buildup', config),
    },
    drops: {
        drop: (config) => Sfx('drop', config),
        boom: (config) => Sfx('boom', config),
    },
    misc: {
        sparkle: (config) => Sfx('sparkle', config),
        shimmer: (config) => Sfx('shimmer', config),
        blip: (config) => Sfx('blip', config),
        boop: (config) => Sfx('boop', config),
    },
    // Direct access by name
    byName: (name, config) => Sfx(name, config),
};
export default sfx;
//# sourceMappingURL=index.js.map