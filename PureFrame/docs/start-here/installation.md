# Installation

This page explains how to install PureFrame and run the first render.

## Requirements

Before installing PureFrame, make sure you have:

- Node.js 20 or newer
- pnpm
- FFmpeg available on your system path

## Install dependencies

From the root of the repository:

```bash
pnpm install
```

## Build the workspace

```bash
pnpm build
```

## Validate the first scene

```bash
./apps/cli/bin/pureframe validate examples/hello-world/scene.json
```

## Render the first scene

```bash
./apps/cli/bin/pureframe render examples/hello-world/scene.json -o output.mp4
```

## What gets installed

PureFrame is organized as a monorepo.

Main packages:

* `@pureframe/schema` — scene definitions, validation, normalization
* `@pureframe/core` — timeline, animation primitives, deterministic engine logic
* `@pureframe/visuals` — layout, text, effects, presets
* `@pureframe/media` — video, audio, captions, metadata
* `@pureframe/render` — renderer backends, export pipeline, frame scheduling
* `@pureframe/remotion-importer` — migration helpers from old Remotion projects

## Troubleshooting

### FFmpeg not found

Make sure FFmpeg is installed and available in your system path.

### Native rendering backend issues

PureFrame uses a renderer backend that may depend on platform-specific binaries. Check the package-level README if rendering fails during startup.

## Related files

* `apps/cli/src/commands/render.ts`
* `apps/cli/src/commands/validate.ts`
* `examples/hello-world/scene.json`
