/**
 * Volume clamping utilities
 */
/**
 * Clamp volume to valid range (0-1)
 */
export function clampVolume(volume) {
    return Math.max(0, Math.min(1, volume));
}
/**
 * Clamp volume with custom min/max
 */
export function clampVolumeRange(volume, min, max) {
    return Math.max(min, Math.min(max, volume));
}
/**
 * Check if volume is valid
 */
export function isValidVolume(volume) {
    return typeof volume === 'number' && isFinite(volume) && volume >= 0 && volume <= 1;
}
/**
 * Check if volume is silent
 */
export function isSilent(volume, threshold = 0.001) {
    return volume < threshold;
}
/**
 * Check if volume is at full
 */
export function isFull(volume) {
    return volume >= 1;
}
/**
 * Convert volume to percentage
 */
export function volumeToPercent(volume) {
    return clampVolume(volume) * 100;
}
/**
 * Convert percentage to volume
 */
export function percentToVolume(percent) {
    return clampVolume(percent / 100);
}
/**
 * Interpolate between two volumes
 */
export function lerpVolume(a, b, t) {
    return clampVolume(a + (b - a) * t);
}
/**
 * Get volume at fraction (0-1) between min and max
 */
export function volumeAtFraction(min, max, fraction) {
    return lerpVolume(min, max, fraction);
}
/**
 * Scale volume by factor
 */
export function scaleVolume(volume, factor) {
    return clampVolume(volume * factor);
}
/**
 * Add volumes (in linear space)
 */
export function addVolumes(a, b) {
    return clampVolume(a + b);
}
/**
 * Multiply volumes
 */
export function multiplyVolumes(a, b) {
    return clampVolume(a * b);
}
/**
 * Get volume ramp array
 */
export function getVolumeRamp(startVolume, endVolume, steps) {
    const ramp = [];
    for (let i = 0; i < steps; i++) {
        const t = i / (steps - 1);
        ramp.push(lerpVolume(startVolume, endVolume, t));
    }
    return ramp;
}
/**
 * Apply volume curve
 */
export function applyVolumeCurve(volume, curve = 'linear') {
    const clamped = clampVolume(volume);
    switch (curve) {
        case 'exponential':
            return clamped * clamped;
        case 'logarithmic':
            return Math.sqrt(clamped);
        default:
            return clamped;
    }
}
/**
 * Get human-readable volume label
 */
export function getVolumeLabel(volume) {
    const clamped = clampVolume(volume);
    if (clamped === 0)
        return 'Muted';
    if (clamped < 0.25)
        return 'Very Low';
    if (clamped < 0.5)
        return 'Low';
    if (clamped < 0.75)
        return 'Medium';
    if (clamped < 1)
        return 'High';
    return 'Full';
}
/**
 * Common volume presets
 */
export const VolumePresets = {
    MUTED: 0,
    VERY_LOW: 0.1,
    LOW: 0.25,
    MEDIUM_LOW: 0.4,
    MEDIUM: 0.5,
    MEDIUM_HIGH: 0.6,
    HIGH: 0.75,
    VERY_HIGH: 0.9,
    FULL: 1,
};
//# sourceMappingURL=clampVolume.js.map