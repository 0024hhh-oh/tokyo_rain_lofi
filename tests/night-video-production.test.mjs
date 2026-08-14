import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const component = fs.readFileSync('src/NightVideoLightingLoop.tsx', 'utf8');
const renderer = fs.readFileSync('scripts/render_night_background.sh', 'utf8');
const workflow = fs.readFileSync('.github/workflows/generate_lofi_video.yml', 'utf8');
const detector = fs.readFileSync('scripts/drive_incoming_queue.py', 'utf8');

test('production night video keeps the accepted v10 lighting behavior', () => {
  assert.match(component, /SOURCE_PLAYBACK_RATE = 0\.5/);
  assert.match(component, /SAFE_MIN_WARMTH = 0\.4/);
  assert.match(component, /DIM_FLICKER_PATTERN = \[1, 0\.58, 0\.90, 0\.42, 1\]/);
  assert.match(component, /DIM_ZONE_SCALES = \[1\.15, 1\.30\]/);
  assert.match(component, /level: 1\.80/);
  assert.match(component, /level: 1\.70/);
  assert.match(component, /const sizeScale = isBrightening \? 0\.6/);
  assert.match(component, /filter: isBrightening \? 'blur\(4px\)' : 'blur\(8px\)'/);
  assert.match(component, /<OffthreadVideo/);
  assert.match(component, /muted/);
  assert.equal(component.match(/<OffthreadVideo/g)?.length, 1);
});

test('night renderer makes one silent 30-second CRF14 Remotion loop from video', () => {
  assert.match(renderer, /public\/night-source\.mp4/);
  assert.match(renderer, /z\.warmth >= 0\.4/);
  assert.match(renderer, /-map 0:v:0 -an -c:v copy/);
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
