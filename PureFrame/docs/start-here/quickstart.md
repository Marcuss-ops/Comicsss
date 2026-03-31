# Quick Start

Get your first PureFrame video rendering in under 5 minutes.

## Installation

```bash
# Install globally
npm install -g @pureframe/cli

# Or locally in your project
npm install @pureframe/core @pureframe/render @pureframe/visuals
```

Verify installation:
```bash
pureframe info
```

## Your First Video

Create a file called `hello.ts`:

```typescript
import { defineComposition } from '@pureframe/schema';
import { fullscreen, text } from '@pureframe/visuals';
import { interpolate } from '@pureframe/core';

// Define your composition
export const Hello = defineComposition((ctx) => {
  // Animate opacity from 0 to 1 over frames 0-30
  const opacity = interpolate(ctx.frame, [0, 30], [0, 1], { 
    clamp: true 
  });

  // Return a scene tree
  return fullscreen({
    background: '#1a1a2e',
    children: [
      text({
        content: 'Hello PureFrame',
        x: 960,
        y: 540,
        opacity,
        fontSize: 72,
        color: '#ffffff',
        textAlign: 'center',
      }),
    ],
  });
});
```

## Render Your Video

```bash
pureframe render hello.ts -o hello.mp4
```

You'll see:
```
🎬 PureFrame Render

  FFmpeg: 6.0
  Scene loaded: hello
  Resolution: 1920x1080
  FPS: 30
  Frames: 150 (5.0s)
  Output: hello.mp4

📸 Rendering frames...
  ████████████████████████████████████████ 100% | 150/150 frames | 45 fps | ETA: 0s
  ✓ Rendered 150 frames at 45.2 fps

🎞️  Encoding video...
  ✓ Video encoded

✨ Render complete!
  Output: C:\Projects\hello.mp4
  Size: 1.2 MB
  Duration: 5.0s
  Total time: 3.5s
  Avg speed: 45.2 fps
```

## What's Happening?

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Scene     │────▶│   Engine     │────▶│   Skia      │────▶│   FFmpeg     │
│   (JSON)    │     │  (evaluate)  │     │  (render)   │     │   (export)   │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                          │
                          ▼
                    ┌──────────────┐
                    │  frame 0-149 │
                    │  opacity 0-1 │
                    └──────────────┘
```

1. **Define**: You write a pure function that returns a scene tree
2. **Evaluate**: PureFrame calculates every frame's properties
3. **Render**: Skia Canvas draws each frame to PNG
4. **Export**: FFmpeg encodes frames + audio into MP4

## Add Animation

Let's make it more interesting:

```typescript
import { defineComposition } from '@pureframe/schema';
import { fullscreen, text, rect } from '@pureframe/visuals';
import { interpolate, spring, Easing } from '@pureframe/core';

export const AnimatedHello = defineComposition((ctx) => {
  const { frame, scene } = ctx;
  const centerX = scene.width / 2;
  const centerY = scene.height / 2;

  // Slide up animation
  const yOffset = interpolate(frame, [0, 30], [100, 0], {
    easing: Easing.easeOutCubic,
    clamp: true,
  });

  // Spring animation for scale
  const scale = spring(frame, {
    startFrame: 10,
    from: 0.8,
    to: 1,
    stiffness: 100,
    damping: 10,
  });

  // Fade out at the end
  const opacity = interpolate(frame, [120, 150], [1, 0], {
    clamp: true,
  });

  return fullscreen({
    background: '#0f0f23',
    children: [
      // Background gradient effect
      rect({
        x: 0,
        y: 0,
        width: '100%',
        height: '100%',
        fill: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
      }),
      // Animated text
      text({
        content: 'Hello PureFrame',
        x: centerX,
        y: centerY + yOffset,
        scale,
        opacity,
        fontSize: 96,
        fontWeight: 700,
        color: '#ffffff',
        textAlign: 'center',
      }),
    ],
  });
});
```

## Preview While Editing

Instead of rendering every time, use the preview server:

```bash
pureframe preview hello.ts
```

This starts a dev server at `http://localhost:3000` with:
- Real-time preview
- Hot reload on file changes
- Frame-by-frame scrubbing

## Next Steps

- **Fundamentals**: Learn the [core concepts](./fundamentals.md)
- **Animation**: Deep dive into [animating properties](./animating-properties.md)
- **Components**: Learn to [reuse and compose](./reuse-components.md)
- **From Remotion**: [Migration guide](./from-remotion.md)

## Common Patterns

### Fade In
```typescript
const opacity = interpolate(frame, [0, 30], [0, 1], { clamp: true });
```

### Slide Up
```typescript
const y = interpolate(frame, [0, 30], [100, 0], { 
  easing: Easing.easeOutCubic,
  clamp: true 
});
```

### Pulse
```typescript
const scale = 1 + Math.sin(frame * 0.1) * 0.05;
```

### Typewriter
```typescript
const charsToShow = Math.floor(interpolate(frame, [0, 60], [0, text.length]));
const visibleText = text.slice(0, charsToShow);
```

## Troubleshooting

### FFmpeg not found
```bash
# macOS
brew install ffmpeg

# Windows
choco install ffmpeg

# Ubuntu
sudo apt-get install ffmpeg
```

### Slow render
- Lower resolution: `-w 1280 -h 720`
- Reduce duration: shorter `durationInFrames`
- Use faster preset: `-p ultrafast`

### Fonts not loading
Ensure fonts are installed on your system or use web fonts with `fontFamily`.

---

Ready to dive deeper? Check out the [core concepts](../core-concepts/scene.md) next.
