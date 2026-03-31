# Preview your video

PureFrame currently focuses on deterministic rendering through the CLI.

At this stage, preview is primarily done through:

- scene validation
- rendering frame ranges
- rendering short outputs
- visual test generation

## Validate before rendering

```bash
./apps/cli/bin/pureframe validate examples/hello-world/scene.json
```

## Render a short output

```bash
./apps/cli/bin/pureframe render examples/hello-world/scene.json -o preview.mp4
```

## Render only a range of frames

When supported by the active render command, use frame ranges to preview motion quickly instead of rendering the full composition.

Example:

```bash
./apps/cli/bin/pureframe render examples/hello-world/scene.json --frames 0-60 -o preview.mp4
```

## Visual debugging

PureFrame can also support preview through:

* image sequence rendering
* visual snapshots
* test fixtures
* generated comparison outputs

## Current status

PureFrame does not rely on a browser-based preview pipeline for final rendering.

A dedicated interactive player may exist in the future, but the current model prioritizes correctness, determinism, and render fidelity.

## Related files

* `apps/cli/src/commands/render.ts`
* `apps/cli/src/commands/validate.ts`
* `test/visual/`
* `scripts/generate-visual-test.mjs`
