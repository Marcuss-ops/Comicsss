/**
 * Decibel/Gain conversion utilities
 */
/**
 * Convert decibels to linear gain
 */
export declare function dbToGain(db: number): number;
/**
 * Convert linear gain to decibels
 */
export declare function gainToDb(gain: number): number;
/**
 * Convert power ratio to decibels
 */
export declare function powerToDb(power: number): number;
/**
 * Convert decibels to power ratio
 */
export declare function dbToPower(db: number): number;
/**
 * Check if dB value is silence
 */
export declare function isSilenceDb(db: number, threshold?: number): boolean;
/**
 * Clamp dB value to range
 */
export declare function clampDb(db: number, min?: number, max?: number): number;
/**
 * Format dB for display
 */
export declare function formatDb(db: number, decimals?: number): string;
/**
 * Convert percentage to gain (0-100% -> 0-1)
 */
export declare function percentToGain(percent: number): number;
/**
 * Convert gain to percentage (0-1 -> 0-100%)
 */
export declare function gainToPercent(gain: number): number;
/**
 * Convert MIDI velocity to gain (0-127 -> 0-1)
 */
export declare function velocityToGain(velocity: number): number;
/**
 * Convert gain to MIDI velocity (0-1 -> 0-127)
 */
export declare function gainToVelocity(gain: number): number;
/**
 * Apply gain to sample
 */
export declare function applyGainToSample(sample: number, gain: number): number;
/**
 * Apply dB to sample
 */
export declare function applyDbToSample(sample: number, db: number): number;
/**
 * Sum gains (additive in dB space)
 */
export declare function sumGains(gains: number[]): number;
/**
 * Average gains
 */
export declare function averageGains(gains: number[]): number;
/**
 * Get common dB values
 */
export declare const CommonDb: {
    readonly SILENCE: number;
    readonly VERY_QUIET: -40;
    readonly QUIET: -20;
    readonly MODERATE: -10;
    readonly LOUD: -3;
    readonly VERY_LOUD: 0;
    readonly CLIPPING: 3;
};
/**
 * Get common gain values
 */
export declare const CommonGain: {
    readonly SILENCE: 0;
    readonly VERY_QUIET: number;
    readonly QUIET: number;
    readonly MODERATE: number;
    readonly LOUD: number;
    readonly UNITY: 1;
    readonly BOOST: number;
};
//# sourceMappingURL=dbToGain.d.ts.map