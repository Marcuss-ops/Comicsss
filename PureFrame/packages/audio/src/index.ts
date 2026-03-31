// PureFrame Audio - Entry Point
// Audio system for PureFrame - clips, tracks, mixing, automation

// Nodes - High-level API
export * from '../nodes/Audio.js';
export * from '../nodes/Sfx.js';

// SFX Library
export * from '../sfx/index.js';

// Timing operations
export * from '../timing/trim.js';
export * from '../timing/delay.js';
export * from '../timing/speed.js';

// Mixing
export * from '../mix/volume.js';

// Analysis
export * from '../analysis/getWaveform.js';

// Import
export * from '../import/decodeAudio.js';
export * from '../import/importAudioFromVideo.js';

// Export
export * from '../export/exportAudio.js';

// Utils
export * from '../utils/clampVolume.js';
export * from '../utils/dbToGain.js';
export * from '../utils/detectSilence.js';
export * from '../utils/framesToSeconds.js';
