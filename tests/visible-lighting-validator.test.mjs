import assert from 'node:assert/strict';
import test from 'node:test';
import {scoreVisibleChanges} from '../scripts/validate_visible_lighting.mjs';

const solidFrame = (width, height, value) => Buffer.alloc(width * height * 3, value);

test('scores strong local light changes inside a detected zone', () => {
  const width = 20;
  const height = 10;
  const dark = solidFrame(width, height, 20);
  const lit = Buffer.from(dark);
  for (let y = 3; y < 7; y += 1) {
    for (let x = 7; x < 13; x += 1) {
      const offset = (y * width + x) * 3;
      lit[offset] = 220;
      lit[offset + 1] = 180;
      lit[offset + 2] = 100;
    }
  }
  const [score] = scoreVisibleChanges({
    frames: [dark, lit],
    width,
    height,
    zones: [{id: 'window', x: 0.5, y: 0.5, width: 0.4, height: 0.6}],
  });
  assert.ok(score.difference > 100);
});

test('rejectable static frames have zero local change', () => {
  const frame = solidFrame(20, 10, 80);
  const [score] = scoreVisibleChanges({
    frames: [frame, Buffer.from(frame)],
    width: 20,
    height: 10,
    zones: [{id: 'window', x: 0.5, y: 0.5, width: 0.4, height: 0.6}],
  });
  assert.equal(score.difference, 0);
});
