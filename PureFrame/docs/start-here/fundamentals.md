# The fundamentals

PureFrame is a deterministic motion graphics engine.

Its main model is:

**Scene -> Evaluation -> Render -> Export**

## Core ideas

### Scene
A scene is a structured description of what should appear over time.

A scene contains:

- dimensions
- fps
- duration
- children
- optional props and metadata

### Node
A node is a visual or media element inside a scene.

Typical nodes include:

- group
- rect
- text
- image
- video
- audio
- effect nodes or preset-generated nodes

### Timeline
PureFrame evaluates every frame explicitly.

A frame is not produced by a browser repaint.
A frame is calculated by the engine from the scene and its inputs.

### Determinism
PureFrame follows this rule:

**Frame = f(time, scene, props, assets, seed)**

This means:
- no hidden browser state
- no runtime layout surprises
- no random output unless a seed is provided

## Example mental model

A title animation is not a React component.
It is:

- a group
- containing text
- with transform and opacity
- animated over a frame range

## Example scene

```json
{
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "durationInFrames": 150,
  "children": [
    {
      "type": "text",
      "text": "Hello PureFrame",
      "x": 300,
      "y": 400,
      "style": {
        "fontSize": 72,
        "color": "#ffffff"
      }
    }
  ]
}
```

## Why No Hooks?

If you're coming from React (or Remotion), you might wonder: **why doesn't PureFrame use hooks?**

### The Problem with Hooks for Video

Hooks like `useCurrentFrame()` seem convenient, but create hidden problems:

1. **Hidden State**: `useState`, `useEffect` create implicit dependencies that make your animation non-deterministic
2. **Lifecycle Complexity**: Components mount/unmount affects timing in unpredictable ways
3. **Testing Difficulty**: Need to render a React tree just to test an animation
4. **Browser Dependency**: Hooks require a browser environment
5. **Performance Overhead**: React reconciliation runs for every single frame

### The PureFrame Solution

```typescript
// ❌ Remotion: Hidden state, hard to test
const MyVideo = () => {
  const frame = useCurrentFrame(); // Where does this come from?
  const [opacity, setOpacity] = useState(0); // Hidden state!
  
  useEffect(() => {
    setOpacity(frame / 30); // Side effect
  }, [frame]);
  
  return <div style={{ opacity }}>Hello</div>;
};

// ✅ PureFrame: Explicit, testable, deterministic
const getScene = (frame: number) => {
  const opacity = frame / 30; // Pure calculation
  
  return text({
    content: 'Hello',
    opacity, // Explicit value
  });
};

// Test without browser
expect(getScene(15).opacity).toBe(0.5);
```

### Benefits of "No Hooks"

| Aspect | With Hooks | Without Hooks (PureFrame) |
|--------|-----------|---------------------------|
| **Determinism** | ❌ Side effects | ✅ Same input = same output |
| **Testing** | ❌ Need React DOM | ✅ Pure functions |
| **Performance** | ❌ Reconciliation overhead | ✅ Direct calculation |
| **Debugging** | ❌ Trace through lifecycle | ✅ Look at the function |
| **Portability** | ❌ Requires browser | ✅ Runs anywhere |

### The Rule

PureFrame follows one simple rule:

> **Frame = f(time, scene, props, assets, seed)**

Your animation is a pure function. Give it frame 30, you get the same result every time.

## Related files

* `packages/schema/src/scene.ts`
* `packages/schema/src/nodes.ts`
* `packages/core/src/engine/`
* `packages/core/src/timeline/`
