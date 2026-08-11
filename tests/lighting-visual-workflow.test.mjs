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

test('lighting visual test renders eight seconds and uploads only an artifact', () => {
  assert.match(workflow, /--frames=0-239/);
  assert.match(workflow, /Expected an 8-second MP4/);
  assert.match(workflow, /LIGHTING_ZONE_MIN_DELTA=18/);
  assert.match(workflow, /LIGHTING_PEAK_MIN_DELTA=28/);
  assert.match(workflow, /uses: actions\/upload-artifact@v4/);
  assert.match(workflow, /path: dist\/lighting-visual-test\.mp4/);
});
