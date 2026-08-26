import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const workflow = fs.readFileSync('.github/workflows/remotion_lighting_ci.yml', 'utf8');

test('the accepted night sample uses the supplied moving-rain background directly', () => {
  assert.match(workflow, /shinsuna-rain-background\.mp4/);
  assert.match(workflow, /cp test_assets\/shinsuna-rain-background\.mp4 video_assets\/background\.mp4/);
  assert.doesNotMatch(workflow, /tblend=all_mode=difference/);
  assert.doesNotMatch(workflow, /rain-motion\.mp4/);
});
