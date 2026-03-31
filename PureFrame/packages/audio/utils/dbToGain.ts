/**
 * Decibel/Gain conversion utilities
 */

/**
 * Convert decibels to linear gain
 */
export function dbToGain(db: number): number {
  return Math.pow(10, db / 20);
}

/**
 * Convert linear gain to decibels
 */
export function gainToDb(gain: number): number {
  if (gain <= 0) {
    return -Infinity;
  }
  return 20 * Math.log10(gain);
}

/**
 * Convert power ratio to decibels
 */
export function powerToDb(power: number): number {
  if (power <= 0) {
    return -Infinity;
  }
  return 10 * Math.log10(power);
}

/**
 * Convert decibels to power ratio
 */
export function dbToPower(db: number): number {
  return Math.pow(10, db / 10);
}

/**
 * Check if dB value is silence
 */
export function isSilenceDb(db: number, threshold: number = -60): boolean {
  return db < threshold;
}

/**
 * Clamp dB value to range
 */
export function clampDb(db: number, min: number = -Infinity, max: number = 0): number {
  return Math.max(min, Math.min(max, db));
}

/**
 * Format dB for display
 */
export function formatDb(db: number, decimals: number = 1): string {
  if (!isFinite(db)) {
    return '-∞ dB';
  }
  return `${db.toFixed(decimals)} dB`;
}

/**
 * Convert percentage to gain (0-100% -> 0-1)
 */
export function percentToGain(percent: number): number {
  return percent / 100;
}

/**
 * Convert gain to percentage (0-1 -> 0-100%)
 */
export function gainToPercent(gain: number): number {
  return gain * 100;
}

/**
 * Convert MIDI velocity to gain (0-127 -> 0-1)
 */
export function velocityToGain(velocity: number): number {
  return velocity / 127;
}

/**
 * Convert gain to MIDI velocity (0-1 -> 0-127)
 */
export function gainToVelocity(gain: number): number {
  return Math.round(gain * 127);
}

/**
 * Apply gain to sample
 */
export function applyGainToSample(sample: number, gain: number): number {
  return sample * gain;
}

/**
 * Apply dB to sample
 */
export function applyDbToSample(sample: number, db: number): number {
  return sample * dbToGain(db);
}

/**
 * Sum gains (additive in dB space)
 */
export function sumGains(gains: number[]): number {
  const dbSum = gains.reduce((sum, gain) => {
    return sum + dbToPower(gain);
  }, 0);
  return Math.sqrt(dbSum);
}

/**
 * Average gains
 */
export function averageGains(gains: number[]): number {
  if (gains.length === 0) return 0;
  return sumGains(gains) / gains.length;
}

/**
 * Get common dB values
 */
export const CommonDb = {
  SILENCE: -Infinity,
  VERY_QUIET: -40,
  QUIET: -20,
  MODERATE: -10,
  LOUD: -3,
  VERY_LOUD: 0,
  CLIPPING: 3,
} as const;

/**
 * Get common gain values
 */
export const CommonGain = {
  SILENCE: 0,
  VERY_QUIET: dbToGain(-40),
  QUIET: dbToGain(-20),
  MODERATE: dbToGain(-10),
  LOUD: dbToGain(-3),
  UNITY: 1,
  BOOST: dbToGain(3),
} as const;