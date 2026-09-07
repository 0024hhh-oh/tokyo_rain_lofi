# Isolated three-depth lighting experiment

Uses the supplied Tokyo night JPEG, unchanged. All masks use the original 1536x869 coordinate plane. Foreground means near-house lamps/windows/reflections, not the non-emissive staircase. Midground covers existing train windows/signals; background covers selected station and skyline windows. No automatic light detection, global exposure/saturation/contrast animation, camera motion, or production imports.

Screen-blended source-aligned light cores and a soft halo only add light. Three depth groups have two staggered pulses each, with 0.8-second smooth fades. Frames 0 and 899 return to the untouched source for looping. The independent source groups are manually authored for THIS image; the timing/compositing pattern is reusable, but a new image needs new masks.

The clean MP4 has no labels. The comparison MP4 puts the untouched original on the left, the animated result on the right, with a separate status caption. The caption is diagnostic only, not evidence that the scene changed.

Run: `node --test experiments/depth-lighting/timing.test.mjs`, `npx tsc -p experiments/depth-lighting/tsconfig.json`. Copy `test_assets/three-layer-tokyo-scene.jpg` to `public/depth-lighting/source.jpg`, then render `experiments/depth-lighting/index.tsx` with `DepthLightingClean` or `DepthLightingCompare` (30fps, 900 frames).

New workflow is PR/path-filtered and manually runnable only, with contents:read and credential persistence disabled. It uploads two MP4s for 7 days. Existing workflows and production Root are unchanged. No Drive/YouTube calls, production queues, Secrets or automatic merge. Visual acceptance is required before any later integration.
