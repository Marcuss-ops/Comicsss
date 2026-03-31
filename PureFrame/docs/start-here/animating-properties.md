# Animating properties

In PureFrame, animation is based on deterministic functions.

Instead of relying on browser-driven UI updates, PureFrame evaluates property values for each frame.

## Typical animated properties

Common animated properties include:

- opacity
- translateX
- translateY
- scale
- rotate
- blur
- glow intensity
- letter reveal progress

## Core primitives

PureFrame provides reusable animation primitives such as:

- `progress()`
- `interpolate()`
- `spring()`
- `fadeIn()`
- `fadeOut()`
- `slideUp()`
- `zoomIn()`
- `pulse()`

## Example

```ts
import {interpolate, spring} from '@pureframe/core';

const opacity = interpolate(frame, [0, 20], [0, 1], {clamp: true});

const scale = spring(frame, {
  startFrame: 10,
  from: 0.95,
  to: 1,
  damping: 20,
});
```

## Animation strategy

PureFrame uses two levels of animation:

### Low-level primitives

These are pure functions:

* interpolate
* spring
* lerp
* oscillation helpers

### High-level presets

These combine primitives into reusable behaviors:

* fade in
* slide in
* typewriter reveal
* pulse zoom
* subtitle highlight

## Best practices

* Keep animations pure
* Base everything on `frame`
* Avoid hidden state
* Use seeded randomness when variation is needed
* Prefer presets for repeated motion patterns

## Related files

* `packages/core/src/animation/`
* `packages/visuals/src/motion/`
* `packages/visuals/src/presets/`
* `examples/animation-primitives.ts`
