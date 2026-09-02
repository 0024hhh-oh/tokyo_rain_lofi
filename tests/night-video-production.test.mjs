import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const component = fs.readFileSync('src/NightVideoLightingLoop.tsx', 'utf8');
const renderer = fs.readFileSync('scripts/render_night_background.sh', 'utf8');
const workflow = fs.readFileSync('.github/workflows/generate_lofi_video.yml', 'utf8');
const detector = fs.readFileSync('scripts/drive_incoming_queue.py', 'utf8');

test('production night video uses positive-only glow on eligible emitters', () => {
  assert.match(component, /SOURCE_PLAYBACK_RATE = 0\.5/);
  assert.match(component, /SAFE_MIN_WARMTH = 0\.4/);
  assert.match(component, /zone\.hasLightCore/);
  assert.match(component, /zone\.color/);
  assert.match(component, /Math\.max\(0, brightness - 1\)/);
  assert.match(component, /if \(brightness <= 1\) return null/);
  assert.doesNotMatch(component, /MAX_DIM_OPACITY|DIM_ZONE_SCALES/);
  assert.doesNotMatch(component, /level: 0\./);
  assert.doesNotMatch(component, /rgba\(0, 0, 0/);
  assert.doesNotMatch(component, /brightness < 1/);
  assert.match(component, /<OffthreadVideo/);
  assert.match(component, /muted/);
  assert.equal(component.match(/<OffthreadVideo/g)?.length, 1);
});
test('night renderer makes one silent 30-second CRF14 Remotion loop from video', () => {
  assert.match(renderer, /public\/night-source\.mp4/);
  assert.match(renderer, /z\.warmth >= 0\.4/);
  assert.match(renderer, /z\.hasLightCore/);
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
  assert.match(detector, /SUPPORTED_TRACK_COUNTS = \(20, 30\)/);
  assert.match(detector, /require_supported_track_count=True/);
});
