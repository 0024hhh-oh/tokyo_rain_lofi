import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const prepare = fs.readFileSync('scripts/prepare_remotion_background.mjs', 'utf8');
const still = fs.readFileSync('src/NightLightingLoop.tsx', 'utf8');
const video = fs.readFileSync('src/NightVideoLightingLoop.tsx', 'utf8');
const renderer = fs.readFileSync('scripts/render_night_background.sh', 'utf8');

test('lighting is controlled only by an explicit transparent overlay asset', () => {
  assert.match(prepare, /light_overlay\.png/);
  assert.match(prepare, /animate: Boolean\(overlaySource\)/);
  assert.doesNotMatch(prepare, /analyzeLightZones|isCompactEmitter|warmth|threshold/);
  assert.match(still, /staticFile\('light_overlay\.png'\)/);
  assert.match(video, /staticFile\('light_overlay\.png'\)/);
  assert.match(renderer, /overlay=/);
});

test('the source is never darkened and overlay opacity returns to zero', () => {
  for (const component of [still, video]) {
    assert.doesNotMatch(component, /rgba\(0, 0, 0|brightness\(|filter:|mixBlendMode/);
    assert.match(component, /\[0, [^\]]+, [^\]]+, 0\]/);
    assert.match(component, /opacity/);
  }
});

test('normal generation remains unchanged when no overlay exists', () => {
  assert.match(prepare, /else await fs\.rm\('public\/light_overlay\.png'/);
  assert.match(still, /const opacity = lighting\.animate \? getOverlayOpacity/);
  assert.match(video, /const opacity = lighting\.animate \? getOverlayOpacity/);
  assert.doesNotMatch(renderer, /safe_zone_count|requires exactly three|detected lights/);
});

test('production workflow boundaries remain untouched', () => {
  const workflow = fs.readFileSync('.github/workflows/generate_lofi_video.yml', 'utf8');
  assert.match(workflow, /Projects\/day|project_mode.*day|Day project/);
  assert.match(workflow, /completed/);
  assert.match(workflow, /failed/);
  assert.match(workflow, /upload_youtube_video\.py/);
  assert.match(workflow, /drive_incoming_queue\.py/);
});
