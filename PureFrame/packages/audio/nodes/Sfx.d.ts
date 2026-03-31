/**
 * Sfx node - high-level API for sound effects
 * Provides convenient access to the audio registry
 */
import type { AudioClipConfig } from '../core/types';
import { AudioClip } from '../core/AudioClip';
import { audioRegistry } from '../assets/registry';
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
export declare function Sfx(name: SfxName, config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
/**
 * Create multiple sound effects at once
 */
export declare function SfxBatch(effects: Array<{
    name: SfxName;
    config?: Omit<AudioClipConfig, 'asset'>;
}>): AudioClip[];
/**
 * Play a sound effect at a specific frame
 */
export declare function SfxAt(frame: number, name: SfxName, options?: Omit<AudioClipConfig, 'asset' | 'from'>): AudioClip;
/**
 * Create a sequence of sound effects
 */
export declare function SfxSequence(names: SfxName[], options?: {
    startFrame?: number;
    spacing?: number;
    volume?: number;
}): AudioClip[];
/**
 * Create a random sound effect from a category
 */
export declare function RandomSfx(category: string, config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
/**
 * Create a layered sound effect (multiple effects at the same time)
 */
export declare function LayeredSfx(names: SfxName[], config?: Omit<AudioClipConfig, 'asset'>): AudioClip[];
/**
 * Helper to create a whoosh effect
 */
export declare function Whoosh(type?: 'fast' | 'slow' | 'swoosh', config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
/**
 * Helper to create an impact effect
 */
export declare function Impact(type?: 'short' | 'deep' | 'punch' | 'thud', config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
/**
 * Helper to create a glitch effect
 */
export declare function Glitch(type?: 'hit' | 'short' | 'static', config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
/**
 * Helper to create a UI sound effect
 */
export declare function UiSound(type?: 'click' | 'pop' | 'tap', config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
/**
 * Helper to create a notification sound
 */
export declare function Notification(type?: 'notification' | 'alert' | 'ding', config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
/**
 * Helper to create a riser/buildup effect
 */
export declare function Riser(type?: 'riser' | 'buildup', config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
/**
 * Helper to create a drop/boom effect
 */
export declare function Drop(type?: 'drop' | 'boom', config?: Omit<AudioClipConfig, 'asset'>): AudioClip;
export default Sfx;
//# sourceMappingURL=Sfx.d.ts.map