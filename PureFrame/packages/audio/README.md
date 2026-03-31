# PureFrame Audio Module

A comprehensive audio system inspired by Remotion's audio handling, designed for programmatic video/audio generation.

## Features

- **Asset Management**: Registry-based sound effect library with categories
- **Timing Control**: Trim, delay, and playback rate with predictable order of operations
- **Mixing**: Volume, fades, envelopes, pan, and normalization
- **Analysis**: Waveform, spectrum, peaks, and RMS analysis
- **Export**: WAV export with support for MP3/AAC via external encoders
- **Video Integration**: Extract audio from video files

## Quick Start

```typescript
import { Audio, Sfx, whip, glitchHit } from './Audio';

// Create audio from registry
const whipSound = Sfx('whip', { from: 30, volume: 0.8 });

// Create custom audio
const customAudio = Audio({
  asset: { id: 'myAudio', src: '/path/to/audio.wav' },
  from: 0,
  trimBefore: 100,
  trimAfter: 500,
  playbackRate: 1.5,
});

// Use convenience functions
const impact = whip({ from: 60 });
const glitch = glitchHit({ volume: 0.5 });
```

## Structure

```
Audio/
├── core/           # Core classes (AudioClip, AudioTrack, AudioTimeline)
├── assets/         # Asset registry and management
├── import/         # Audio import from files and video
├── timing/         # Trim, delay, speed operations
├── mix/            # Volume, fades, pan, normalization
├── nodes/          # High-level API nodes
├── sfx/            # Sound effects library
├── analysis/       # Waveform and spectrum analysis
├── render/         # Offline rendering
├── export/         # Audio export utilities
└── utils/          # Utility functions
```

## Order of Operations

Audio processing follows a strict order (inspired by Remotion):

1. **Trim**: Cut the source audio
2. **Delay/Offset**: Position on timeline
3. **PlaybackRate**: Adjust speed

```typescript
// The timing is resolved in this order:
resolveAudioTime(frame, config, fps, assetDuration)
```

## Sound Effects

Access built-in sound effects by category:

```typescript
import { sfx } from './Audio';

// By category
const whoosh = sfx.transitions.whip();
const impact = sfx.impacts.deep();

// By name
const glitch = sfx.byName('glitchHit');

// Helpers
const quickWhoosh = Whoosh('fast', { from: 30 });
const boom = Impact('deep', { volume: 0.8 });
```

### Categories

- **Transitions**: whip, whooshFast, whooshSlow, swoosh
- **Impacts**: impactShort, impactDeep, punch, thud
- **Glitch**: glitchHit, glitchShort, static
- **UI**: click, pop, tap
- **Notifications**: notification, alert, ding
- **Risers**: riser, buildup
- **Drops**: drop, boom
- **Misc**: sparkle, shimmer, blip, boop

## Analysis

```typescript
import { getWaveform, getSpectrum, calculateRMS } from './Audio';

// Get waveform data
const waveform = getWaveform(audioData, { samples: 1000 });

// Get spectrum
const spectrum = getSpectrum(audioData);

// Calculate RMS
const rms = calculateRMS(audioData);
```

## Export

```typescript
import { exportWav, downloadAudio } from './Audio';

// Export to WAV
const blob = exportWav(audioData, {
  sampleRate: 48000,
  bitDepth: 16,
  channels: 2,
});

// Download
downloadAudio(blob, 'my-audio.wav');
```

## Video Audio

```typescript
import { importAudioFromVideo } from './Audio';

// Extract audio from video
const audioData = await importAudioFromVideo('/path/to/video.mp4');
```

## TypeScript Support

Full TypeScript support with exported types:

- `AudioAsset`
- `AudioClipConfig`
- `AudioData`
- `WaveformData`
- `AudioExportConfig`
- And more...

## License

MIT