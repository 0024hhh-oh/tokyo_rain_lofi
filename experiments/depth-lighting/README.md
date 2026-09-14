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
are unchanged. Registered night still images are rendered through this scene by `scripts/render_night_background.sh`.

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
not visual quality on a second real scene. Automatic mask generation remains separate work. The Drive night still-image path uses registered profiles; day and video-source paths remain unchanged.

## Second scene: river at night

`profiles/river-night.json` uses the supplied 1536x864 image unchanged. Selected
background building windows, middle waterfront windows/lamps, and foreground
street/boat lamps plus limited reflections share the same compositing and timing.
These coordinates were authored by the assistant from visual inspection; this is
not an unattended AI mask-detection pipeline. The Tokyo profile remains unchanged.
The PR workflow renders and validates both scenes as separate matrix jobs.

## Optional thirds → center → existing-lighting selection

For a new, reviewed image profile, add `localLightCandidates` (maximum 30). Each candidate needs a unique `id`, `kind` (for example `vending_machine`, `phone_booth`, `sign`, `window`), `depth`, source-only SVG `sourceMask`, pixel `sourceRoi: [left, top, right, bottom]`, `isEmitter: true`, `prominence` (0..1), and `clipRisk` (0..0.2). Only include objects confirmed visually to emit artificial light; never add reflections, white patches, wall glare, or a mask covering them. The source image hash and mask registration remain mandatory. The metadata cannot establish from pixels whether an object truly emits light: a person must inspect the original and a rendered sample.

Candidate centers inside a fraction of the image width/height around any of the four thirds intersections are considered first (default 8% horizontally and vertically). If none are valid, consider the center (default 12% per axis). `localLightSearch` may set `thirdsRadiusX`, `thirdsRadiusY`, `centerRadiusX`, and `centerRadiusY` between .01 and .20. The nearest valid candidate wins and only its source mask is lit, with existing staggered per-depth fade timing and a reduced local opacity. Masks above 3.5% of image area or with clipRisk over .20 are ineligible. If neither region has an eligible candidate, the entire old lighting-unit selection and timing remain in effect, including the existing scheduled light behavior of the street scene.

The registered `street-thirds.json` selects one previously masked window for the exact street-night JPEG in the normal night still-image video flow. Tokyo and river profiles retain their original lighting; the legacy `street-night.json` remains available for regression checks. New images need image-specific masks, SHA-256 and registration in `prepare_approved_lighting.mjs`; an unregistered image stays unchanged. Selection is isolated in `select-light.ts`, with cases A–F, invalid-profile checks and production path coverage. This change does not add automatic image understanding.

## Street scene comparison for the new selection mode

`street-thirds.json` reuses a previously masked left white window on the exact street-night source with 9%-width thirds tolerance. The PR workflow checks frames 0, 285 and 899 for local brightening, no distant changes and no dimming, then renders a 30-second comparison. Automated checks cannot establish aesthetic quality; the five additional images were not evaluated.
