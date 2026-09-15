import assert from 'node:assert/strict';
import test from 'node:test';
import {scorePositiveLocalChange} from '../scripts/validate_video_lighting_pair.mjs';

const pixels = (values) => Uint8Array.from(values.flatMap((value) => [value, value, value]));

test('scores a visible positive local glow', () => {
  const baseline = pixels(new Array(100).fill(20));
  const values = new Array(100).fill(20);
  for (const index of [44, 45, 54, 55]) values[index] = 80;
  const result = scorePositiveLocalChange({
    baseline,
    lit: pixels(values),
    width: 10,
    height: 10,
  });
  assert.equal(result.changedPixels, 4);
  assert.equal(result.negativePixels, 0);
  assert.ok(result.meanPositiveDelta >= 59);
  assert.ok(result.bboxRatio <= 0.04);
});

test('counts dimming separately from positive glow', () => {
  const result = scorePositiveLocalChange({
    baseline: pixels([30, 30, 30, 30]),
    lit: pixels([20, 30, 30, 80]),
    width: 2,
    height: 2,
  });
  assert.equal(result.changedPixels, 1);
  assert.equal(result.negativePixels, 1);
});
