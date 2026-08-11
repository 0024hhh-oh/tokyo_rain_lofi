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

test('lighting changes once from all-off to all-on at four seconds', () => {
  const component = fs.readFileSync('tests/LightingVisualTest.tsx', 'utf8');
  assert.match(component, /frame >= fps \* 4/);
  assert.doesNotMatch(component, /random\(|Math\.sin|cycle/i);
});

test('off-state masks are feathered and never use visible clipped rectangles', () => {
  const component = fs.readFileSync('tests/LightingVisualTest.tsx', 'utf8');
  assert.match(component, /featheredMask/);
  assert.match(component, /rgba\(0, 0, 0, 0\.56\).*transparent 100%/);
  assert.match(component, /!lightsOn/);
  assert.doesNotMatch(component, /clipPath|inset\(/);
  assert.doesNotMatch(component, /zone\.strength \* 0\.7/);
});
