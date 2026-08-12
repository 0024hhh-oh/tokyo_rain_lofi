import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const workflow = fs.readFileSync('.github/workflows/rain_video_lighting_ci.yml', 'utf8');
const component = fs.readFileSync('tests/RainVideoLightingTest.tsx', 'utf8');

test('rain-video lighting CI stays isolated from production services', () => {
  assert.match(workflow, /^on:\n  pull_request:/m);
  assert.doesNotMatch(workflow, /youtube/i);
  assert.doesNotMatch(workflow, /google|drive/i);
  assert.doesNotMatch(workflow, /completed|failed/i);
  assert.doesNotMatch(workflow, /secrets\./i);
});

test('the supplied rain video is slowed, looped, center-cropped, and always muted in Remotion', () => {
  assert.match(component, /OffthreadVideo/);
  assert.match(component, /const SOURCE_PLAYBACK_RATE = 0\.5/);
  assert.match(component, /<Loop durationInFrames=\{LOOP_DURATION_IN_FRAMES\}>/);
  assert.match(component, /playbackRate=\{SOURCE_PLAYBACK_RATE\}/);
  assert.match(component, /muted/);
  assert.match(component, /objectFit: 'cover'/);
  assert.match(component, /staticFile\('rain-video\.mp4'\)/);
  assert.doesNotMatch(component, /volume=/);
});

test('lighting uses gentle overlays instead of replaying and filtering the rain video', () => {
  assert.match(component, /const MAX_LIGHTS = 3/);
  assert.match(component, /SAFE_MIN_WARMTH = 0\.55/);
  assert.match(component, /SAFE_MAX_Y = 0\.72/);
  assert.match(component, /safeLightZones\.length === MAX_LIGHTS/);
  assert.match(component, /level: 0\.76/);
  assert.match(component, /level: 0\.72/);
  assert.match(component, /level: 1\.35/);
  assert.match(component, /level: 1\.28/);
  assert.match(component, /Math\.min\(0\.18/);
  assert.match(component, /background: glow/);
  assert.doesNotMatch(component, /filter: `brightness/);
  assert.equal(component.match(/<MutedRainVideo \/>/g)?.length, 1);
});

test('CI renders a silent 30-second 1080p artifact', () => {
  assert.match(workflow, /--crf=14/);
  assert.match(workflow, /--frames=0-899/);
  assert.match(workflow, /--muted/);
  assert.match(workflow, /Expected a 30-second MP4/);
  assert.match(workflow, /Output must not contain an audio stream/);
  assert.match(workflow, /path: dist\/rain-video-lighting-test\.mp4/);
  assert.match(workflow, /if: always\(\)/);
});
