import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const component = fs.readFileSync('src/NightVideoLightingLoop.tsx', 'utf8');
const renderer = fs.readFileSync('scripts/render_night_background.sh', 'utf8');
const workflow = fs.readFileSync('.github/workflows/generate_lofi_video.yml', 'utf8');
const detector = fs.readFileSync('scripts/drive_incoming_queue.py', 'utf8');
const profile = fs.readFileSync('src/lightingProfile.ts', 'utf8');

test('production night video uses positive-only glow on eligible emitters', () => {
  assert.match(component, /zone\.eligible/);
  assert.match(component, /const REAR_MAX_Y = 0\.72/);
  assert.match(component, /zone\.y < REAR_MAX_Y/);
  assert.match(component, /slice\(0, 1\)/);
  assert.match(component, /selectionMode/);
  assert.match(component, /zone\.color/);
  assert.doesNotMatch(component, /hasThreeSafeLights/);
  assert.doesNotMatch(component, /DIM_FLICKER_PATTERN/);
  assert.doesNotMatch(component, /MAX_DIM_OPACITY|DIM_ZONE_SCALES/);
  assert.doesNotMatch(component, /level: 0\./);
  assert.doesNotMatch(component, /rgba\(0, 0, 0/);
  assert.match(component, /level: 1\.38/);
  assert.match(component, /level: 1\.34/);
  assert.match(component, /isDaylightAccent \? 0\.46 : 0\.86/);
  assert.match(component, /filter: 'blur\(1px\)'/);
  assert.match(component, /<Img/);
  assert.match(component, /night-frames\/frame-/);
  assert.doesNotMatch(component, /<OffthreadVideo/);
});

test('legacy brightness helper also forbids negative exposure', () => {
  assert.match(profile, /BRIGHT_SCENE_LUMA = 110/);
  assert.match(profile, /Math\.max\(1, brightness\)/);
  assert.doesNotMatch(profile, /brightness < 1/);
});

test('night renderer normalizes the source for frame-accurate Remotion looping', () => {
  assert.match(renderer, /z\.eligible/);
  assert.match(renderer, /public\/night-frames\/frame-%04d\.jpg/);
  assert.match(renderer, /find public\/night-frames/);
  assert.doesNotMatch(renderer, /-stream_loop -1 -i "\$source_copy"/);
  assert.match(component, /<Img/);
  assert.match(component, /night-frames\/frame-/);
  assert.doesNotMatch(component, /<OffthreadVideo/);
  assert.match(renderer, /sourceDurationInFrames/);
  assert.match(renderer, /NightVideoLightingLoop/);
  assert.match(renderer, /--crf=14/);
  assert.match(renderer, /--muted/);
  assert.match(renderer, /--frames=0-899/);
  assert.match(renderer, /Rendered night background must not contain audio/);
});

test('production boundaries remain unchanged around the new night renderer', () => {
  assert.match(workflow, /if \[\[ "\$\{project_mode\}" == "night" \]\]; then/);
  assert.match(workflow, /bash scripts\/render_night_background\.sh/);
  assert.match(workflow, /Day project: keeping the supplied background unchanged/);
  assert.match(workflow, /scripts\/generate_lofi_video\.sh/);
  assert.match(workflow, /python scripts\/upload_youtube_video\.py/);
  assert.match(workflow, /--destination completed/);
  assert.match(workflow, /--destination failed/);
  assert.match(detector, /require_exactly_20_tracks=True/);
});
