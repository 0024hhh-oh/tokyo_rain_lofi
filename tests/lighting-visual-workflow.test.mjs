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

test('three compact emitters use positive-only sparse schedules', () => {
  const component = fs.readFileSync('tests/LightingVisualTest.tsx', 'utf8');
  assert.match(component, /generated-light-zones\.json/);
  assert.match(component, /const MAX_LIGHTS = 3/);
  assert.match(component, /SAFE_MIN_WARMTH = 0\.75/);
  assert.match(component, /SAFE_MAX_Y = 0\.72/);
  assert.match(component, /zone\.hasLightCore/);
  assert.match(component, /zone\.isCompactEmitter/);
  assert.match(component, /slice\(0, 1\)/);
  assert.doesNotMatch(component, /safeLightZones\.length === MAX_LIGHTS|hasThreeSafeLights/);
  assert.match(component, /lighting\.animate && safeLightZones\.map/);
  assert.match(component, /interpolate\(/);
  assert.match(component, /start: 0\.85, end: 0\.99, level: 1\.18/);
  assert.match(component, /start: 5\.95, end: 6\.28, level: 1\.15/);
  assert.match(component, /start: 3\.45, end: 4\.05, level: 1\.16/);
  assert.match(component, /start: 2\.90, end: 3\.10, level: 1\.35/);
  assert.match(component, /start: 7\.15, end: 7\.56, level: 1\.28/);
  assert.match(component, /Math\.abs\(level - 1\)/);
  assert.doesNotMatch(component, /Math\.min\(brightness, level\)/);
  assert.doesNotMatch(component, /lanternMask|52\.6% 48\.2%/);
  assert.doesNotMatch(component, /random\(|Math\.random|Math\.sin|cycle/i);
});

test('three overlays are source-colored and can never darken the image', () => {
  const component = fs.readFileSync('tests/LightingVisualTest.tsx', 'utf8');
  assert.match(component, /zone\.color/);
  assert.match(component, /mixBlendMode: 'screen'/);
  assert.match(component, /Math\.max\(0, brightness - 1\)/);
  assert.doesNotMatch(component, /rgba\(0, 0, 0|level: 0\./);
  assert.doesNotMatch(component, /clipPath|inset\(/);
  assert.doesNotMatch(component, /backdropFilter|brightness\(/);
});

test('production night renderer animates zero to three safe lights without blocking video generation', () => {
  const component = fs.readFileSync('src/NightLightingLoop.tsx', 'utf8');
  const renderer = fs.readFileSync('scripts/render_night_background.sh', 'utf8');
  assert.match(component, /const MAX_LIGHTS = 3/);
  assert.match(component, /zone\.eligible/);
  assert.match(component, /selectionMode/);
  assert.doesNotMatch(component, /safeLightZones\.length === MAX_LIGHTS|hasThreeSafeLights/);
  assert.match(component, /level: 1\.18/);
  assert.match(component, /level: 1\.16/);
  assert.match(component, /level: 1\.35/);
  assert.match(component, /level: 1\.28/);
  assert.match(component, /interpolate\(/);
  assert.doesNotMatch(component, /random\(|Math\.random|Math\.sin|cycle/i);
  assert.doesNotMatch(component, /clipPath|rgba\(0, 0, 0|level: 0\./);
  assert.match(renderer, /safe_zone_count/);
  assert.doesNotMatch(renderer, /safe_zone_count" != "3"|requires exactly three/);
  assert.match(renderer, /rendering continues with zero to three lights/);
});

test('static scenes never use negative exposure', () => {
  const component = fs.readFileSync('src/NightLightingLoop.tsx', 'utf8');
  assert.doesNotMatch(component, /isBrightLightingScene|adaptBrightnessForScene/);
  assert.doesNotMatch(component, /brightness\(|rgba\(0, 0, 0|level: 0\./);
});
