import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const workflowPath = '.github/workflows/lighting_visual_test.yml';
const workflow = fs.readFileSync(workflowPath, 'utf8');

test('lighting visual test is manual-only and isolated from production services', () => {
  assert.match(workflow, /^on:\n  workflow_dispatch:\s*$/m);
  assert.doesNotMatch(workflow, /^  schedule:/m);
  assert.doesNotMatch(workflow, /^  pull_request:/m);
  assert.doesNotMatch(workflow, /youtube/i);
  assert.doesNotMatch(workflow, /google|drive/i);
  assert.doesNotMatch(workflow, /completed|failed/i);
  assert.doesNotMatch(workflow, /secrets\./i);
});

test('lighting visual test uses the supplied real scene at native 1080p', () => {
  assert.match(workflow, /test_assets\/lighting-real-scene\.jpg\.b64\.\*/);
  assert.match(workflow, /prepare_remotion_background\.mjs/);
  assert.match(workflow, /tests\/lighting-visual-index\.tsx/);
  assert.match(workflow, /--frames=0-239/);
  assert.match(workflow, /--crf=14/);
  assert.match(workflow, /Expected 1920x1080/);
  assert.match(workflow, /Expected an 8-second MP4/);
  assert.match(workflow, /uses: actions\/upload-artifact@v4/);
  assert.match(workflow, /path: dist\/lighting-visual-test\.mp4/);
});

test('two lights dim and one brightens on sparse irregular schedules', () => {
  const component = fs.readFileSync('tests/LightingVisualTest.tsx', 'utf8');
  assert.match(component, /generated-light-zones\.json/);
  assert.match(component, /const MAX_LIGHTS = 3/);
  assert.match(component, /SAFE_MIN_WARMTH = 0\.55/);
  assert.match(component, /SAFE_MAX_Y = 0\.72/);
  assert.match(component, /zone\.hasLightCore/);
  assert.match(component, /slice\(0, MAX_LIGHTS\)/);
  assert.match(component, /safeLightZones\.length === MAX_LIGHTS/);
  assert.match(component, /lighting\.animate && hasThreeSafeLights/);
  assert.match(component, /interpolate\(/);
  assert.match(component, /start: 0\.85, end: 0\.99, level: 0\.76/);
  assert.match(component, /start: 5\.95, end: 6\.28, level: 0\.80/);
  assert.match(component, /start: 3\.45, end: 4\.05, level: 0\.72/);
  assert.match(component, /start: 2\.90, end: 3\.10, level: 1\.35/);
  assert.match(component, /start: 7\.15, end: 7\.56, level: 1\.28/);
  assert.match(component, /Math\.abs\(level - 1\)/);
  assert.doesNotMatch(component, /Math\.min\(brightness, level\)/);
  assert.doesNotMatch(component, /lanternMask|52\.6% 48\.2%/);
  assert.doesNotMatch(component, /random\(|Math\.random|Math\.sin|cycle/i);
});

test('three masks are feathered and never change global light regions', () => {
  const component = fs.readFileSync('tests/LightingVisualTest.tsx', 'utf8');
  assert.match(component, /zone\.width \* 50/);
  assert.match(component, /zone\.height \* 50/);
  assert.match(component, /rgba\(0, 0, 0, 0\.48\) 80%, transparent 100%/);
  assert.match(component, /windows, street lamps, and wet-road reflections/);
  assert.match(component, /non-overlapping/);
  assert.doesNotMatch(component, /clipPath|inset\(/);
  assert.doesNotMatch(component, /mixBlendMode|screen|glowOpacity/);
});

test('production night renderer accepts zero to three prominent video lights', () => {
  const component = fs.readFileSync('src/NightLightingLoop.tsx', 'utf8');
  const renderer = fs.readFileSync('scripts/render_night_background.sh', 'utf8');
  assert.match(component, /const MAX_LIGHTS = 3/);
  assert.match(component, /SAFE_MIN_WARMTH = 0\.55/);
  assert.match(component, /SAFE_MAX_Y = 0\.72/);
  assert.match(component, /zone\.hasLightCore/);
  assert.match(component, /safeLightZones\.length === MAX_LIGHTS/);
  assert.match(component, /level: 0\.76/);
  assert.match(component, /level: 0\.72/);
  assert.match(component, /level: 1\.35/);
  assert.match(component, /level: 1\.28/);
  assert.match(component, /interpolate\(/);
  assert.doesNotMatch(component, /random\(|Math\.random|Math\.sin|cycle/i);
  assert.doesNotMatch(component, /clipPath|mixBlendMode|glowOpacity/);
  assert.match(renderer, /safe_zone_count/);
  assert.match(renderer, /z\.isCompactSource/);
  assert.doesNotMatch(renderer, /safe_zone_count" != "3"/);
});
