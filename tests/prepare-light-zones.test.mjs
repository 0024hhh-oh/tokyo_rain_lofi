import assert from 'node:assert/strict';
import test from 'node:test';
import {analyzeLightZones} from '../scripts/prepare_remotion_background.mjs';

const image = (width, height, rgb) => {
  const data = Buffer.alloc(width * height * 3);
  for (let index = 0; index < width * height; index += 1) {
    data[index * 3] = rgb[0];
    data[index * 3 + 1] = rgb[1];
    data[index * 3 + 2] = rgb[2];
  }
  return data;
};

const paint = (data, width, x0, y0, boxWidth, boxHeight, rgb) => {
  for (let y = y0; y < y0 + boxHeight; y += 1) {
    for (let x = x0; x < x0 + boxWidth; x += 1) {
      const offset = (y * width + x) * 3;
      data[offset] = rgb[0];
      data[offset + 1] = rgb[1];
      data[offset + 2] = rgb[2];
    }
  }
};

test('detects only compact warm lights in a dark scene', () => {
  const width = 160;
  const height = 90;
  const data = image(width, height, [9, 14, 24]);
  paint(data, width, 18, 30, 6, 5, [255, 225, 150]);
  paint(data, width, 62, 42, 10, 7, [245, 211, 150]);
  paint(data, width, 112, 34, 9, 8, [255, 178, 72]);
  paint(data, width, 138, 56, 6, 5, [255, 235, 170]);

  const result = analyzeLightZones({data, width, height});
  assert.equal(result.animate, true);
  assert.ok(result.zones.length >= 4);
  assert.ok(result.zones.length <= 14);
  assert.ok(result.zones.every((zone) => zone.strength <= 1));
  const safe = result.zones.filter((zone) =>
    zone.hasLightCore &&
    zone.isCompactEmitter &&
    zone.warmth >= 0.75 &&
    zone.y < 0.72);
  assert.equal(safe.length, 2);
});

test('bright daytime surfaces fail closed when no warm emitter is certain', () => {
  const width = 160;
  const height = 90;
  const data = image(width, height, [205, 210, 216]);
  paint(data, width, 50, 35, 8, 8, [255, 245, 225]);
  const result = analyzeLightZones({data, width, height});
  assert.equal(result.animate, false);
  assert.ok(result.zones.length >= 1);
});
