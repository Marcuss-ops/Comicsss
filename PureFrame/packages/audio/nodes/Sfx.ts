/**
 * Sfx node - high-level API for sound effects
 * Provides convenient access to the audio registry
 */

import type { AudioClipConfig, AudioAsset } from '../core/types';
import { AudioClip } from '../core/AudioClip';
import { audioRegistry, getAsset } from '../assets/registry';

/**
 * Type for registry sound effect names
 */
export type SfxName = keyof typeof audioRegistry;

/**
 * Create a sound effect node from the registry
 * 
 * @example
 * ```ts
 * // Simple usage
 * const whip = Sfx('whip');
 * 
 * // With options
 * const glitch = Sfx('glitchHit', { from: 30, volume: 0.8 });
 * 
 * // With trim
 * const shortWhoosh = Sfx('whooshSlow', { trimAfter: 200 });
 * ```
 */
export function Sfx(
  name: SfxName,
  config: Omit<AudioClipConfig, 'asset'> = {}
): AudioClip {
  const asset = audioRegistry[name];
  
  if (!asset) {
    throw new Error(`Sound effect not found: ${name}`);
  }

  return new AudioClip({ ...config, asset }, asset);
}

/**
 * Create multiple sound effects at once
 */
export function SfxBatch(
  effects: Array<{ name: SfxName; config?: Omit<AudioClipConfig, 'asset'> }>
): AudioClip[] {
  return effects.map(({ name, config = {} }) => Sfx(name, config));
}

/**
 * Play a sound effect at a specific frame
 */
export function SfxAt(
  frame: number,
  name: SfxName,
  options: Omit<AudioClipConfig, 'asset' | 'from'> = {}
): AudioClip {
  return Sfx(name, { ...options, from: frame });
}

/**
 * Create a sequence of sound effects
 */
export function SfxSequence(
  names: SfxName[],
  options: {
    startFrame?: number;
    spacing?: number;
    volume?: number;
  } = {}
): AudioClip[] {
  const { startFrame = 0, spacing = 0, volume } = options;
  
  return names.map((name, index) => {
    const asset = audioRegistry[name];
    const durationMs = asset?.durationMs ?? 0;
    const from = startFrame + index * (durationMs + spacing);
    
    return Sfx(name, { from, volume });
  });
}

/**
 * Create a random sound effect from a category
 */
export function RandomSfx(
  category: string,
  config: Omit<AudioClipConfig, 'asset'> = {}
): AudioClip {
  const assets = Object.values(audioRegistry).filter(
    (asset) => asset.tags?.includes(category)
  );

  if (assets.length === 0) {
    throw new Error(`No sound effects found in category: ${category}`);
  }

  const randomAsset = assets[Math.floor(Math.random() * assets.length)];
  return new AudioClip({ ...config, asset: randomAsset }, randomAsset);
}

/**
 * Create a layered sound effect (multiple effects at the same time)
 */
export function LayeredSfx(
  names: SfxName[],
  config: Omit<AudioClipConfig, 'asset'> = {}
): AudioClip[] {
  return names.map((name) => Sfx(name, config));
}

/**
 * Helper to create a whoosh effect
 */
export function Whoosh(
  type: 'fast' | 'slow' | 'swoosh' = 'fast',
  config: Omit<AudioClipConfig, 'asset'> = {}
): AudioClip {
  const whooshMap: Record<string, SfxName> = {
    fast: 'whooshFast',
    slow: 'whooshSlow',
    swoosh: 'swoosh',
  };
  
  return Sfx(whooshMap[type], config);
}

/**
 * Helper to create an impact effect
 */
export function Impact(
  type: 'short' | 'deep' | 'punch' | 'thud' = 'short',
  config: Omit<AudioClipConfig, 'asset'> = {}
): AudioClip {
  const impactMap: Record<string, SfxName> = {
    short: 'impactShort',
    deep: 'impactDeep',
    punch: 'punch',
    thud: 'thud',
  };
  
  return Sfx(impactMap[type], config);
}

/**
 * Helper to create a glitch effect
 */
export function Glitch(
  type: 'hit' | 'short' | 'static' = 'hit',
  config: Omit<AudioClipConfig, 'asset'> = {}
): AudioClip {
  const glitchMap: Record<string, SfxName> = {
    hit: 'glitchHit',
    short: 'glitchShort',
    static: 'static',
  };
  
  return Sfx(glitchMap[type], config);
}

/**
 * Helper to create a UI sound effect
 */
export function UiSound(
  type: 'click' | 'pop' | 'tap' = 'click',
  config: Omit<AudioClipConfig, 'asset'> = {}
): AudioClip {
  const uiMap: Record<string, SfxName> = {
    click: 'click',
    pop: 'pop',
    tap: 'tap',
  };
  
  return Sfx(uiMap[type], config);
}

/**
 * Helper to create a notification sound
 */
export function Notification(
  type: 'notification' | 'alert' | 'ding' = 'notification',
  config: Omit<AudioClipConfig, 'asset'> = {}
): AudioClip {
  const notifMap: Record<string, SfxName> = {
    notification: 'notification',
    alert: 'alert',
    ding: 'ding',
  };
  
  return Sfx(notifMap[type], config);
}

/**
 * Helper to create a riser/buildup effect
 */
export function Riser(
  type: 'riser' | 'buildup' = 'riser',
  config: Omit<AudioClipConfig, 'asset'> = {}
): AudioClip {
  const riserMap: Record<string, SfxName> = {
    riser: 'riser',
    buildup: 'buildup',
  };
  
  return Sfx(riserMap[type], config);
}

/**
 * Helper to create a drop/boom effect
 */
export function Drop(
  type: 'drop' | 'boom' = 'drop',
  config: Omit<AudioClipConfig, 'asset'> = {}
): AudioClip {
  const dropMap: Record<string, SfxName> = {
    drop: 'drop',
    boom: 'boom',
  };
  
  return Sfx(dropMap[type], config);
}

export default Sfx;