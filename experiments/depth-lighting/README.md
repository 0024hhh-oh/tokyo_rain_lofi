# Isolated three-depth lighting experiment

Uses the supplied Tokyo night JPEG, unchanged. All masks use the original 1536x869 coordinate plane. Foreground means near-house lamps/windows/reflections, not the non-emissive staircase. Midground covers existing train windows/signals; background covers selected station and skyline windows. No automatic light detection, global exposure/saturation/contrast animation, camera motion, or production imports.

Screen-blended source-aligned light cores and a soft halo only add light. Three depth groups have two staggered pulses each, with 0.8-second smooth fades. Frames 0 and 899 return to the untouched source for looping. The independent source groups are manually authored for THIS image; the timing/compositing pattern is reusable, but a new image needs new masks.

The clean MP4 has no labels. The comparison MP4 puts the untouched original on the left, the animated result on the right, with a separate status caption. The caption is diagnostic only, not evidence that the scene changed.

Run: `node --test experiments/depth-lighting/timing.test.mjs`, `npx tsc -p experiments/depth-lighting/tsconfig.json`. Copy `test_assets/three-layer-tokyo-scene.jpg` to `public/depth-lighting/source.jpg`, then render `experiments/depth-lighting/index.tsx` with `DepthLightingClean` or `DepthLightingCompare` (30fps, 900 frames).

New workflow is PR/path-filtered and manually runnable only, with contents:read and credential persistence disabled. It uploads two MP4s for 7 days. Existing workflows and production Root are unchanged. No Drive/YouTube calls, production queues, Secrets or automatic merge. Visual acceptance is required before any later integration.

## Image-specific profiles

The accepted Tokyo mask is in `profiles/tokyo-approved.json`. `Scene` and
`Comparison` now accept a `profile` prop: source dimensions, local source path,
three SVG light masks and glow settings. Timing and the accepted Tokyo settings
are unchanged. No production integration is enabled.

For each new image, author masks around its actual emitters (not horizontal
bands), record its exact SHA-256 and dimensions, and tune only that profile.
Masks are not automatically detected. Do not reuse the Tokyo coordinates for
another scene. Review a rendered comparison before accepting a new profile.

Prepare and render from the repository root:

```sh
node experiments/depth-lighting/prepare-profile.mjs PROFILE.json IMAGE.jpg public dist/depth-lighting/props.json
npx remotion render experiments/depth-lighting/index.tsx DepthLightingCompare dist/depth-lighting/comparison.mp4 --props=dist/depth-lighting/props.json --muted
```

Preparation rejects image/profile mismatches, invalid dimensions/orientation,
unsafe paths, active SVG and invalid glow settings before writing outputs.
The hash binds a profile to a file; it does not prove the mask is visually correct.
New compositions may use different image aspect ratios; image and mask always
share one plane. The synthetic alternate-image test checks configuration handling,
not visual quality on a second real scene. AI mask generation and production
Drive/Day/Night integration remain separate follow-up work.

## Second scene: river at night

`profiles/river-night.json` uses the supplied 1536x864 image unchanged. Selected
background building windows, middle waterfront windows/lamps, and foreground
street/boat lamps plus limited reflections share the same compositing and timing.
These coordinates were authored by the assistant from visual inspection; this is
not an unattended AI mask-detection pipeline. The Tokyo profile remains unchanged.
The PR workflow renders and validates both scenes as separate matrix jobs.
