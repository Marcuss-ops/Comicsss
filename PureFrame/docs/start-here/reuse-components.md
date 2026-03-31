# Reuse components

PureFrame reuses motion logic through presets, compositions, and templates.

## Reusable building blocks

In PureFrame, reusable content usually belongs to one of these categories:

### Presets
A preset is a reusable visual pattern.

Examples:
- clean typewriter
- lower third
- glow title
- subtitle highlight
- news ticker

### Compositions
A composition is a reusable scene entry point with props.

A composition defines:
- width
- height
- fps
- duration
- default props
- accepted input props

### Templates
A template is a higher-level reusable scene package intended for repeated rendering with different inputs.

## Example preset

```ts
cleanTypewriter({
  sentences: [
    "The global economy continues to show signs of recovery.",
    "Experts predict significant growth in the technology sector."
  ],
  focusIndex: 1,
  seed: 42
});
```

## Why reuse matters

Reusability helps PureFrame avoid duplication across:

* examples
* video templates
* imported Remotion projects
* CLI renders with different inputs

## Good reuse strategy

Prefer this order:

1. primitive
2. preset
3. composition
4. template

If something is repeated in multiple files, it should probably become a preset.

## Related files

* `packages/visuals/src/presets/`
* `packages/schema/src/`
* `packages/remotion-importer/src/`
* `examples/clean-typewriter.ts`
