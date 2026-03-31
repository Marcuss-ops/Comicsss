/**
 * SFX Library - Ready-to-use sound effects
 * Import directly: import { whip, glitchHit } from './sfx'
 */

export { 
  audioRegistry,
  getAsset,
  getAssetsByTag,
  getAssetsByCategory,
  searchAssets,
  getAllAssets,
  hasAsset,
} from '../assets/registry';

export type { AudioAsset } from '../core/types';

// Re-export the Sfx node and helpers
export {
  Sfx,
  SfxBatch,
  SfxAt,
  SfxSequence,
  RandomSfx,
  LayeredSfx,
  Whoosh,
  Impact,
  Glitch,
  UiSound,
  Notification,
  Riser,
  Drop,
} from '../nodes/Sfx';

export type { SfxName } from '../nodes/Sfx';

// Named exports for common sound effects (convenience)
import { Sfx, type SfxName } from '../nodes/Sfx';
import type { AudioClipConfig } from '../core/types';
import { AudioClip } from '../core/AudioClip';

// Transitions
export const whip = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('whip', config);
export const whooshFast = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('whooshFast', config);
export const whooshSlow = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('whooshSlow', config);
export const swoosh = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('swoosh', config);

// Impacts
export const impactShort = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('impactShort', config);
export const impactDeep = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('impactDeep', config);
export const punch = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('punch', config);
export const thud = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('thud', config);

// Glitch
export const glitchHit = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('glitchHit', config);
export const glitchShort = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('glitchShort', config);
export const staticNoise = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('static', config);

// UI
export const click = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('click', config);
export const pop = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('pop', config);
export const tap = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('tap', config);

// Notifications
export const notification = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('notification', config);
export const alert = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('alert', config);
export const ding = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('ding', config);

// Riser/Build
export const riser = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('riser', config);
export const buildup = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('buildup', config);

// Drop/Release
export const drop = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('drop', config);
export const boom = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('boom', config);

// Misc
export const sparkle = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('sparkle', config);
export const shimmer = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('shimmer', config);
export const blip = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('blip', config);
export const boop = (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('boop', config);

/**
 * Category-based access
 */
export const sfx = {
  // By category
  transitions: {
    whip: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('whip', config),
    whooshFast: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('whooshFast', config),
    whooshSlow: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('whooshSlow', config),
    swoosh: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('swoosh', config),
  },
  impacts: {
    short: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('impactShort', config),
    deep: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('impactDeep', config),
    punch: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('punch', config),
    thud: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('thud', config),
  },
  glitch: {
    hit: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('glitchHit', config),
    short: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('glitchShort', config),
    static: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('static', config),
  },
  ui: {
    click: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('click', config),
    pop: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('pop', config),
    tap: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('tap', config),
  },
  notifications: {
    notification: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('notification', config),
    alert: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('alert', config),
    ding: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('ding', config),
  },
  risers: {
    riser: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('riser', config),
    buildup: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('buildup', config),
  },
  drops: {
    drop: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('drop', config),
    boom: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('boom', config),
  },
  misc: {
    sparkle: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('sparkle', config),
    shimmer: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('shimmer', config),
    blip: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('blip', config),
    boop: (config?: Omit<AudioClipConfig, 'asset'>) => Sfx('boop', config),
  },
  
  // Direct access by name
  byName: (name: SfxName, config?: Omit<AudioClipConfig, 'asset'>) => Sfx(name, config),
};

export default sfx;