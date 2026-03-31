/**
 * Volume clamping utilities
 */
/**
 * Clamp volume to valid range (0-1)
 */
export declare function clampVolume(volume: number): number;
/**
 * Clamp volume with custom min/max
 */
export declare function clampVolumeRange(volume: number, min: number, max: number): number;
/**
 * Check if volume is valid
 */
export declare function isValidVolume(volume: number): boolean;
/**
 * Check if volume is silent
 */
export declare function isSilent(volume: number, threshold?: number): boolean;
/**
 * Check if volume is at full
 */
export declare function isFull(volume: number): boolean;
/**
 * Convert volume to percentage
 */
export declare function volumeToPercent(volume: number): number;
/**
 * Convert percentage to volume
 */
export declare function percentToVolume(percent: number): number;
/**
 * Interpolate between two volumes
 */
export declare function lerpVolume(a: number, b: number, t: number): number;
/**
 * Get volume at fraction (0-1) between min and max
 */
export declare function volumeAtFraction(min: number, max: number, fraction: number): number;
/**
 * Scale volume by factor
 */
export declare function scaleVolume(volume: number, factor: number): number;
/**
 * Add volumes (in linear space)
 */
export declare function addVolumes(a: number, b: number): number;
/**
 * Multiply volumes
 */
export declare function multiplyVolumes(a: number, b: number): number;
/**
 * Get volume ramp array
 */
export declare function getVolumeRamp(startVolume: number, endVolume: number, steps: number): number[];
/**
 * Apply volume curve
 */
export declare function applyVolumeCurve(volume: number, curve?: 'linear' | 'exponential' | 'logarithmic'): number;
/**
 * Get human-readable volume label
 */
export declare function getVolumeLabel(volume: number): string;
/**
 * Common volume presets
 */
export declare const VolumePresets: {
    readonly MUTED: 0;
    readonly VERY_LOW: 0.1;
    readonly LOW: 0.25;
    readonly MEDIUM_LOW: 0.4;
    readonly MEDIUM: 0.5;
    readonly MEDIUM_HIGH: 0.6;
    readonly HIGH: 0.75;
    readonly VERY_HIGH: 0.9;
    readonly FULL: 1;
};
//# sourceMappingURL=clampVolume.d.ts.map