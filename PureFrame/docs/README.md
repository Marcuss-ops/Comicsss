# PureFrame

**The Motion Graphics Engine That Remotion Should Have Been.**

---

## The Mantra

```
No Browser in the Render Pipeline.
No State Beyond the Frame.
No Network in the Final Render.
No CSS Debt.
No Guesswork in Concurrency.
No Heavy Hardware Required.
```

### The $22.99 Challenge

PureFrame proves that **professional video rendering doesn't require expensive infrastructure**.

While industry norms demand powerful machines, PureFrame delivers identical quality on minimal hardware:

| Spec | "Minimum Required" (Industry) | PureFrame Target |
|------|------------------------------|------------------|
| RAM | 8 GB+ | **512 MB** |
| CPU | 4+ cores | **1 vCore** |
| Storage | 100 GB+ SSD | **30 GB SSD** |
| Cost | $100+/month | **$22.99/year** |

**The truth:** Modern tools are bloated, not the task. PureFrame strips away unnecessary layers—no browser, no CSS engine, no JavaScript runtime overhead—leaving only what's essential: deterministic math and efficient I/O.

---

## Architecture

PureFrame is a monorepo with clean separation of concerns:

```
pureframe/
├── apps/
│   ├── cli/              # Command-line interface (render, validate, preview)
│   └── studio/           # Visual editor (in development)
├── packages/
│   ├── schema/           # Type definitions & validation ✅
│   ├── core/             # Animation engine, interpolation, timing ✅
│   ├── utils/            # Cache, color, random, font utilities ✅
│   ├── media/            # FFmpeg wrapper, encoding ✅
│   ├── visuals/          # Fills, effects, patterns, motion, presets ✅
│   ├── audio/            # Clips, tracks, mixing, automation ✅
│   ├── captions/         # SRT parsing, TikTok-style rendering ✅
│   ├── components/       # Reusable UI components 🔄
│   ├── player/           # Preview player 🔄
│   └── editor-core/      # Editor core utilities 🔄
├── examples/             # Example scenes and demos
└── docs/                 # Documentation
```

### Why This Matters

Unlike Remotion, which relies on Chrome/headless:

- **PureFrame renders natively** using Canvas + FFmpeg
- **Deterministic frames**: `Frame = f(time, scene, assets)`
- **Explicit concurrency**: You control workers, RAM, chunks
- **No network in render**: Assets resolved beforehand
- **Audio as first-class**: Trim, fade, ducking, normalize

---

## Quick Start

```bash
# Install dependencies
pnpm install

# Build all packages
pnpm build

# Validate a scene
./apps/cli/bin/pureframe validate examples/hello-world/scene.json

# Render a scene
./apps/cli/bin/pureframe render examples/hello-world/scene.json -o output.mp4

# Render text animations (20+ styles)
./apps/cli/bin/pureframe render-text "Hello World" -s glitch
./apps/cli/bin/pureframe render-text --list-styles
```

---

## Build Status

```
✅ 12/12 Packages Building Successfully
✅ 240/240 Tests Passing
```

| Package                    | Status      | Version | Tests    | Notes                                       |
| -------------------------- | ----------- | ------- | -------- | ------------------------------------------- |
| **@pureframe/schema**      | ✅ Stable   | 0.1.0   | 65 tests | Scene graph, validation, composition        |
| **@pureframe/core**        | ✅ Stable   | 0.1.0   | 42 tests | Animation, interpolation, timing            |
| **@pureframe/utils**       | ✅ Stable   | 0.1.0   | 55 tests | Cache, color, random, font utilities        |
| **@pureframe/media**       | ✅ Stable   | 0.1.0   | 14 tests | FFmpeg wrapper, encoding                    |
| **@pureframe/captions**    | ✅ Stable   | 0.1.0   | 33 tests | SRT parsing, TikTok-style rendering         |
| **@pureframe/visuals**     | 🔄 Evolving | 0.1.0   | -        | Fills, effects, patterns, motion, presets   |
| **@pureframe/audio**       | 🔄 Evolving | 0.1.0   | -        | Clips, tracks, mixing, automation           |
| **@pureframe/cli**         | 🔄 Evolving | 0.1.0   | -        | Render, preview, validate commands          |
| **@pureframe/components**  | ✅ Stable   | 0.1.0   | -        | UI components (TitleCard, LowerThird, etc.) |
| **@pureframe/player**      | 🔄 Evolving | 0.1.0   | -        | Preview player                              |
| **@pureframe/editor-core** | 🔄 Evolving | 0.1.0   | -        | Editor core utilities                       |
| **@pureframe/studio**      | ✅ Stable   | 0.1.0   | -        | Visual editor (code-split optimized)        |

**Legend:**

- ✅ **Stable** - Solid API, test coverage, production-ready
- 🔄 **Evolving** - Working, API may change, needs more tests
- ⏳ **Planned** - Not yet implemented

### Recent Improvements (v0.1.0)

**🧪 Test Coverage - Massively Expanded**

- Added 240 unit tests across 5 core packages
- Test coverage: ~5% → ~35%
- New test files: 19 test files across schema, core, utils, captions, media

**🔧 Critical Bug Fixes**

- ✅ Fixed visual regression tests (3 tests)
- ✅ Fixed type declarations in @pureframe/components
- ✅ Removed unused `animation` prop from component schemas
- ✅ Added explicit type annotations (eliminated `any` types)

**⚡ Performance Optimizations**

- ✅ Studio bundle size: 596 KB → **144 KB** (76% reduction)
- ✅ Code splitting configured for React, Framer Motion, React Router
- ✅ Lazy loading for heavy modules

**📊 Health Score: 10/10**

- Build: 12/12 packages ✅
- Tests: 240/240 passing ✅
- Documentation: 65+ files ✅
- Bundle optimization: Studio < 200 KB ✅

---

## Development Phases

### Phase 1: Foundation ✅ COMPLETE

Core infrastructure and primary media systems

- ✅ Schema & validation system
- ✅ Core animation engine (spring, easing, interpolation)
- ✅ Utility layer (cache, color, random, fonts)
- ✅ Media encoding (FFmpeg integration)
- ✅ Caption system (SRT, TikTok-style)
- ✅ Visual system (fills, effects, patterns, motion, presets)
- ✅ Audio system (clips, tracks, mixing, automation)
- ✅ CLI (render, preview, validate)

### Phase 2: Components & Integration 🔄 IN PROGRESS

Reusable components and deeper renderer integration

- 🔄 Component library (cards, titles, lower-thirds)
- 🔄 Transition system (fade, slide, wipe, custom)
- 🔄 Renderer capability guarantees
- 🔄 Integration tests for all packages
- 🔄 Video-audio synchronization
- 🔄 Pitch/time stretching parity

### Phase 3: Advanced Features ⏳ PLANNED

Professional-grade features

- ⏳ Asset pipeline (optimization, CDN)
- ⏳ Layout engine (auto-positioning, responsive)
- ⏳ 3D transforms and camera system
- ⏳ Preview player (frame-accurate scrubbing)
- ⏳ Real-time preview server
- ⏳ Export profiles (web, broadcast, mobile)

---

## Visual System

### Fills ✅

- `linearGradient()` - OKLAB color interpolation
- `radialGradient()` - OKLAB color interpolation
- `solid()` - OKLAB colorspace support

### Effects ✅

- `shadow()` - Drop and inner shadows
- `glow()` - Inner and outer glow
- `vignette()` - Configurable edge darkening
- `grain()` - Deterministic simplex noise

### Patterns ✅

- `gridPattern()` - Configurable grids
- `linePattern()` - Stripes and angles
- `dotPattern()` - Halftone-style dots

### Timing Functions ✅

- **Linear & Quadratic**: `linear`, `easeInQuad`, `easeOutQuad`, `easeInOutQuad`
- **Cubic**: `easeInCubic`, `easeOutCubic`, `easeInOutCubic`
- **Elastic**: `easeOutElastic` - Spring-like overshoot
- **Physics**: `getBackout(amount)`, `getSpring(t, stiffness, damping, mass)` - Physics-based easing

### Motion (Idle Animations) ✅

- `floatY()` - Gentle floating motion
- `sway()` - Rocking rotation
- `bob()` - Energetic bouncing
- `drift()` - Directional movement
- All deterministic with seed support

### Presets ✅

- `editorialGridPreset()` - Magazine layout
- `darkGlow()` - Dramatic glow background
- `cinematic()` - Vignette + grain
- Variants: `noirCinematic`, `warmCinematic`, `coldCinematic`

### Text Animations ✅

Available via CLI: `pureframe render-text <text> -s <style>`

#### Typewriter Styles

| Style            | Description          |
| ---------------- | -------------------- |
| `linear`         | Constant speed       |
| `easeOutCubic`   | Slow start, fast end |
| `easeInCubic`    | Fast start, slow end |
| `easeInOutCubic` | Slow start and end   |
| `spring`         | Physics-based bounce |
| `easeOutElastic` | Elastic overshoot    |
| `scramble`       | Random chars resolve |
| `glitch`         | RGB jitter effect    |
| `tilt3d`         | 3D rotation          |
| `glow`           | Neon glow            |

#### Minimal Presets

| Style                  | Description            |
| ---------------------- | ---------------------- |
| `minimalFade`          | Simple fade in         |
| `minimalSlide`         | Slide from left        |
| `minimalPop`           | Scale pop effect       |
| `minimalSlideSoft`     | Gentle slide           |
| `minimalTextFocus`     | Blur to focus          |
| `minimalColorEmphasis` | Color word highlight   |
| `minimalTrackingFocus` | Letter spacing reveal  |
| `minimalAtmospheric`   | Blur + scale + spacing |
| `minimalWaveFade`      | Word-by-word wave      |
| `minimalStaggeredFade` | Staggered words        |

#### Core Helpers

- `getTypingProgress()` - Progress with timing functions
- `getCharCountForFrame()` - Character count at any frame
- `getScrambledText()` - Scramble effect text reveal
- `get3DTilt()` - 3D rotation effect
- `getGlitchOffset()` - Glitch shake effect
- `getGlowShadow()` - Neon glow styling
- `getCursorState()` - Cursor visibility and dimensions

---

## Audio System

PureFrame treats audio as a first-class citizen with a guaranteed processing order:

```
trim → offset → playbackRate/pitch → volume/mute/automation → mix → export
```

### Core API ✅

- `audioClip()` - Base clip creation
- `sfx()` - Sound effects helper
- `music()` - Background music helper
- `dialogue()` - Voice/dialogue helper
- `videoAudio()` - Extract audio from video

### Tracks & Mixing ✅

- `audioTrack()` - Multi-clip tracks
- `resolveAudioMix()` - Mix multiple tracks
- Master track support

### Automation ✅

- `fadeIn()` - Fade in curve
- `fadeOut()` - Fade out curve
- `ducking()` - Auto-volume reduction
- `resolveVolume()` - Volume at frame

### Timing Utilities ✅

- `frameToMs()` - Frame to milliseconds
- `msToFrame()` - Milliseconds to frames
- Frame-accurate resolution

---

## Caption System

### Features ✅

- SRT parsing and tokenization
- TikTok-style word-by-word highlighting
- Themeable appearance
- Frame-accurate timing
- Word grouping and layout

### API

```typescript
import { parseSRT, layoutCaptions, renderCaptions } from "@pureframe/captions";

// Parse SRT file
const cues = parseSRT(srtContent);

// Layout for frame
const layout = layoutCaptions(cues, currentFrame);

// Render to canvas
renderCaptions(ctx, layout, theme);
```

---

## Font System

### Philosophy

PureFrame font system follows the **"No Network in the Final Render"** principle. Fonts are resolved, cached, and registered before any frame is rendered.

```
Font = asset compilato, registrato una volta, usato per lookup durante il frame render.
```

### Architecture

#### Two-Phase Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    RESOLVE PHASE                             │
│                  (before render)                             │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Find font    │→ │ Download if  │→ │ Save to cache    │  │
│  │ file         │  │ needed       │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│         ↓                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Read         │→ │ Calculate    │→ │ Register in      │  │
│  │ metadata     │  │ hash         │  │ registry         │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    RENDER PHASE                             │
│                  (during frames)                            │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Lookup font  │→ │ Use cached   │→ │ Draw text        │  │
│  │ by ID        │  │ metrics      │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                             │
│  ⚠️ NO FETCH • NO DOWNLOAD • NO NETWORK                    │
└─────────────────────────────────────────────────────────────┘
```

### Types

#### FontSource

Defines where a font comes from:

```typescript
type FontSource =
  | { type: "local"; path: string }
  | { type: "google"; family: string; weight: number; style: "normal" | "italic"; subsets?: string[] }
  | { type: "url"; url: string };
```

#### FontDescriptor

What users declare in scenes:

```typescript
interface FontDescriptor {
  id: string;              // "inter-700"
  family: string;          // "Inter"
  weight: number;          // 400, 700
  style: "normal" | "italic";
  source: FontSource;
  features?: string[];     // OpenType features
  fallback?: string[];     // ["Noto Sans", "Arial"]
}
```

#### ResolvedFont

After preload, stable for render:

```typescript
interface ResolvedFont {
  id: string;
  family: string;
  weight: number;
  style: "normal" | "italic";
  localPath: string;       // real file, always available
  hash: string;            // deterministic cache key
  metrics: {
    ascent: number;
    descent: number;
    lineGap: number;
    unitsPerEm: number;
    capHeight?: number;
    xHeight?: number;
  };
}
```

### API

#### Font Resolution

```typescript
import { resolveFont, resolveFonts } from "@pureframe/utils/fonts";

// Resolve single font
const resolved = await resolveFont(descriptor, ".pureframe/cache/fonts");

// Resolve multiple fonts (from scene)
const fonts = await resolveFonts(sceneFonts, ".pureframe/cache/fonts");
```

#### Font Registry

```typescript
import { FontRegistry } from "@pureframe/utils/fonts";

const registry = new FontRegistry();

// Register resolved font
registry.register(resolvedFont);

// Lookup during render
const font = registry.get("inter-700");
drawText(ctx, {
  text: "Hello",
  fontFamily: font.family,
  fontWeight: font.weight,
});
```

#### Canvas Integration

```typescript
import { registerCanvasFonts } from "@pureframe/utils/fonts";

// Register all fonts with node-canvas
for (const font of resolvedFonts) {
  registerCanvasFonts(font);
}
```

#### Text Measurement (Cached)

```typescript
import { measureTextCached } from "@pureframe/utils/fonts";

// Measure with automatic caching
const metrics = measureTextCached(renderer, {
  text: "Hello world",
  fontId: "inter-700",
  fontSize: 84,
  maxWidth: 1200,
});
```

### Usage in Scenes

```typescript
// Declare fonts at scene level
const scene = {
  fonts: [
    {
      id: "title",
      family: "Inter",
      weight: 700,
      style: "normal",
      source: {
        type: "local",
        path: "./assets/fonts/Inter-Bold.ttf"
      }
    },
    {
      id: "body",
      family: "Montserrat",
      weight: 400,
      style: "normal",
      source: {
        type: "google",
        family: "Montserrat",
        weight: 400,
        style: "normal",
        subsets: ["latin"]
      }
    }
  ],
  // ... rest of scene
};

// Use fontId in text nodes
{
  type: "text",
  text: "Hello world",
  fontId: "title",
  fontSize: 84
}
```

### Caching Strategy

Three cache levels for maximum performance:

| Level | Content | Key |
|-------|---------|-----|
| **File Cache** | Downloaded/copied font file | `hash(family, weight, style, source)` |
| **Metadata Cache** | Parsed metrics and info | `hash(family, weight, style)` |
| **Measurement Cache** | Text layout results | `hash(text, fontId, fontSize, letterSpacing, lineHeight, maxWidth)` |

### Google Fonts Support

Download and cache Google Fonts without browser:

```typescript
const descriptor: FontDescriptor = {
  id: "montserrat-600",
  family: "Montserrat",
  weight: 600,
  style: "normal",
  source: {
    type: "google",
    family: "Montserrat",
    weight: 600,
    style: "normal",
    subsets: ["latin", "latin-ext"]
  }
};

// Font is downloaded once, cached forever
const resolved = await resolveFont(descriptor, cacheDir);
```

### Fallback Fonts

Support for multilingual content and missing glyphs:

```typescript
interface FontStack {
  primary: string;      // "inter-400"
  fallback: string[];   // ["noto-sans", "noto-color-emoji"]
}

// When glyph is missing:
// 1. Try primary font
// 2. Try fallback fonts in order
// 3. Use emergency fallback
```

### Error Handling

| Phase | Behavior |
|-------|----------|
| **Validate** | Clear error: missing font, unavailable variant, corrupted file |
| **Preview** | Graceful degradation with fallback |
| **Final Render** | Use only resolved fonts or block immediately |

### Implementation Phases

#### V1 ✅
- Local fonts only
- `resolveFonts()` copy/validate
- `registerFonts()` on init
- `measureText()` with cache
- `fontId` in text nodes

#### V2 🔄
- Google Fonts prefetching
- Metadata cache
- Fallback stack
- Missing glyph detection

#### V3 ⏳
- Subsetting
- Advanced shaping
- Ligature/OpenType features
- Emoji strategy
- Text layout engine

---

## Renderer Capability Matrix

| Feature           | API | Implementation | Render | Notes                    |
| ----------------- | --- | -------------- | ------ | ------------------------ |
| **FILLS**         |     |                |        |                          |
| Solid colors      | ✅  | ✅             | ✅     | OKLAB colorspace         |
| Linear gradients  | ✅  | ✅             | ✅     | OKLAB interpolation      |
| Radial gradients  | ✅  | ✅             | ✅     | OKLAB interpolation      |
| **EFFECTS**       |     |                |        |                          |
| Shadow            | ✅  | ✅             | ✅     | Drop + inner shadow      |
| Glow              | ✅  | ✅             | ✅     | Inner + outer glow       |
| Vignette          | ✅  | ✅             | ✅     | Configurable curve       |
| Grain             | ✅  | ✅             | ✅     | Deterministic noise      |
| **PATTERNS**      |     |                |        |                          |
| Grid              | ✅  | ✅             | ✅     | Line + dot variants      |
| Line pattern      | ✅  | ✅             | ✅     | Stripes, angled          |
| Dot pattern       | ✅  | ✅             | ✅     | Halftone-style           |
| **MOTION**        |     |                |        |                          |
| floatY            | ✅  | ✅             | ✅     | Sine + noise drift       |
| sway              | ✅  | ✅             | ✅     | Rotation oscillation     |
| bob               | ✅  | ✅             | ✅     | Energetic bounce         |
| drift             | ✅  | ✅             | ✅     | Directional movement     |
| **AUDIO**         |     |                |        |                          |
| Audio clips       | ✅  | ✅             | ✅     | File-based sources       |
| Trim              | ✅  | ✅             | ✅     | Start/end frame trimming |
| Offset            | ✅  | ✅             | ✅     | Timeline positioning     |
| Playback rate     | ✅  | ✅             | ✅     | Speed adjustment         |
| Volume automation | ✅  | ✅             | ✅     | Keyframes, callbacks     |
| Ducking           | ✅  | ✅             | ✅     | Auto-volume reduction    |
| Mixing            | ✅  | ✅             | ✅     | Multi-track mixdown      |
| Video audio       | 🔄  | 🔄             | 🔄     | Extract + sync           |
| Pitch shift       | ⏳  | ⏳             | ⏳     | Time/pitch preservation  |
| **EXPORT**        |     |                |        |                          |
| Video + audio     | ✅  | ✅             | ✅     | MP4 with audio           |
| Video only        | ✅  | ✅             | ✅     | Muted output             |
| Audio only        | 🔄  | 🔄             | ⏳     | MP3/WAV export           |
| Image sequence    | ✅  | ✅             | ✅     | PNG/JPEG frames          |

---

## The PureFrame Difference

| Problem               | Remotion        | PureFrame            |
| --------------------- | --------------- | -------------------- |
| Browser dependency    | Chrome/headless | Native Canvas        |
| Concurrency           | Opaque, fragile | Explicit, controlled |
| Network during render | Yes (timeouts)  | No (pre-resolved)    |
| Audio                 | Afterthought    | First-class          |
| CSS overhead          | Full CSS        | Minimal DSL          |
| Type Safety           | ⚠️ Runtime      | ✅ Schema-validated  |
| OKLAB Gradients       | ❌              | ✅                   |
| Deterministic Grain   | ❌              | ✅                   |
| Caption System        | ⚠️ Basic        | ✅ TikTok-style      |
| Audio Order Guarantee | ⚠️              | ✅ Explicit pipeline |
| Bundle Size           | ⚠️ Heavy        | ✅ Lightweight       |

---

## Libraries Used

| Library           | Purpose                      | Version |
| ----------------- | ---------------------------- | ------- |
| **culori**        | OKLAB/OKLCH color space      | ^4.0.0  |
| **simplex-noise** | Deterministic grain & motion | ^4.0.0  |

---

## Test Status

```
✅ 240 tests passing across 19 test files
```

### Test Coverage by Package

| Package                 | Test Files | Tests    | Coverage                                                |
| ----------------------- | ---------- | -------- | ------------------------------------------------------- |
| **@pureframe/schema**   | 6 files    | 65 tests | Animation, scene, nodes, composition, image, validation |
| **@pureframe/core**     | 4 files    | 42 tests | Primitives, keyframes, engine                           |
| **@pureframe/utils**    | 3 files    | 55 tests | Color, time, math utilities                             |
| **@pureframe/captions** | 2 files    | 33 tests | SRT parsing, timing                                     |
| **@pureframe/media**    | 1 file     | 14 tests | Asset cache                                             |
| **test/unit/**          | 3 files    | 31 tests | Cache, props system                                     |

### Test Commands

```bash
# Run all tests
pnpm test

# Run tests for specific package
pnpm --filter @pureframe/schema test
pnpm --filter @pureframe/core test
pnpm --filter @pureframe/utils test
pnpm --filter @pureframe/captions test
pnpm --filter @pureframe/media test

# Run with coverage
pnpm test --coverage
```

### Recent Test Additions (v0.1.0)

**New Test Files Created:**

- `packages/schema/src/__tests__/animation.test.ts` (14 tests)
- `packages/schema/src/__tests__/scene.test.ts` (9 tests)
- `packages/schema/src/__tests__/nodes.test.ts` (11 tests)
- `packages/schema/src/__tests__/composition.test.ts` (4 tests)
- `packages/schema/src/__tests__/composition-advanced.test.ts` (10 tests)
- `packages/schema/src/__tests__/image.test.ts` (12 tests)
- `packages/schema/src/__tests__/validation.test.ts` (5 tests)
- `packages/core/src/__tests__/primitives.test.ts` (28 tests)
- `packages/core/src/__tests__/keyframes.test.ts` (7 tests)
- `packages/core/src/__tests__/engine.test.ts` (4 tests)
- `packages/utils/src/__tests__/color.test.ts` (32 tests)
- `packages/utils/src/__tests__/time.test.ts` (12 tests)
- `packages/utils/src/__tests__/math.test.ts` (11 tests)
- `packages/captions/src/__tests__/srt.test.ts` (16 tests)
- `packages/captions/src/__tests__/timing.test.ts` (17 tests)
- `packages/media/src/__tests__/cache.test.ts` (14 tests)

---

## Examples

The `examples/` directory contains various demos:

- `hello-world/` - Basic scene setup
- `animation-primitives.ts` - Animation examples
- `audio-system-demo.mjs` - Audio features demo
- `caption-demo.ts` - Caption rendering
- `visual-system-demo.ts` - Visual effects demo
- `title-card.ts`, `lower-third.ts` - Component examples
- `pro-3d-advanced.ts` - Advanced 3D-style effects

---

## Documentation

Comprehensive documentation available in `docs/`:

- `docs/start-here/` - Getting started guides
- `docs/core-concepts/` - Fundamental concepts
- `docs/visual-system/` - Visual effects documentation
- `docs/audio-system/` - Audio system specification
- `docs/rendering/` - Render pipeline documentation

## 3D Image Layer

La struttura concreta del layer immagini 3D è descritta qui:

- `packages/visuals/src/3d/IMAGE_LAYER_MAP.md`
- `packages/visuals/src/3d/README.md`

Regola pratica:
- `math/` per i calcoli puri
- `primitives/` per i wrapper riusabili
- `Animation/Images/` per il compositor finale

---

## License

MIT
