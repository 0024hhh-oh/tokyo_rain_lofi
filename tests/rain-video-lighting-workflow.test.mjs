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

test('the supplied rain video is looped, center-cropped, and always muted in Remotion', () => {
  assert.match(component, /OffthreadVideo/);
  assert.match(component, /<Loop durationInFrames=\{SOURCE_DURATION_IN_FRAMES\}>/);
  assert.match(component, /muted/);
  assert.match(component, /objectFit: 'cover'/);
  assert.match(component, /staticFile\('rain-video\.mp4'\)/);
  assert.doesNotMatch(component, /volume=/);
});

test('the approved three-light behavior is preserved over the moving background', () => {
  assert.match(component, /const MAX_LIGHTS = 3/);
  assert.match(component, /SAFE_MIN_WARMTH = 0\.55/);
  assert.match(component, /SAFE_MAX_Y = 0\.72/);
  assert.match(component, /safeLightZones\.length === MAX_LIGHTS/);
  assert.match(component, /level: 0\.76/);
  assert.match(component, /level: 0\.72/);
  assert.match(component, /level: 1\.35/);
  assert.match(component, /level: 1\.28/);
});

test('CI renders a silent 30-second 1080p artifact', () => {
  assert.match(workflow, /--frames=0-899/);
  assert.match(workflow, /--muted/);
  assert.match(workflow, /Expected a 30-second MP4/);
  assert.match(workflow, /Output must not contain an audio stream/);
  assert.match(workflow, /path: dist\/rain-video-lighting-test\.mp4/);
  assert.match(workflow, /if: always\(\)/);
});
