import assert from 'node:assert/strict';
import test from 'node:test';

import {analyzeLightZones} from '../scripts/prepare_remotion_background.mjs';

const WIDTH = 64;
const HEIGHT = 36;

const makeScene = () => {
  const data = Buffer.alloc(WIDTH * HEIGHT * 3);
  for (let index = 0; index < WIDTH * HEIGHT; index += 1) {
    data[index * 3] = 20;
    data[index * 3 + 1] = 20;
    data[index * 3 + 2] = 24;
  }

  const paint = (left, top, width, height, [red, green, blue]) => {
    for (let y = top; y < top + height; y += 1) {
      for (let x = left; x < left + width; x += 1) {
        const offset = (y * WIDTH + x) * 3;
        data[offset] = red;
        data[offset + 1] = green;
        data[offset + 2] = blue;
      }
    }
  };

  // A diffuse warm concrete face: bright enough for the old detector, but
  // without either a white-hot or saturated warm light core.
  paint(28, 13, 9, 9, [175, 160, 145]);

  // Two compact bright sources and one compact red signal.
  paint(7, 6, 2, 2, [250, 235, 215]);
  // Deliberately sits between the rejected 220 boundary and the compressed-video-safe 205 boundary.
  paint(45, 8, 2, 2, [220, 205, 185]);
  paint(52, 15, 2, 2, [230, 70, 50]);

  return data;
};

test('diffuse walls and compact red signals stay observable but are not animated', () => {
  const analysis = analyzeLightZones({
    data: makeScene(),
    width: WIDTH,
    height: HEIGHT,
  });

  const wall = analysis.zones.find((zone) =>
    Math.abs(zone.x - 0.5) < 0.12 && Math.abs(zone.y - 0.47) < 0.15);
  assert.ok(wall, 'expected the diffuse wall to remain observable in detector output');
  assert.equal(wall.hasLightCore, false);
  assert.equal(wall.color.length, 3);

  const signal = analysis.zones.find((zone) =>
    zone.x > 0.75 && zone.warmth > 0.9);
  assert.ok(signal, 'expected the compact red signal to remain observable');
  assert.equal(signal.hasLightCore, true);
  assert.equal(signal.animationEligible, false);

  const animatedLights = analysis.zones
    .filter((zone) =>
      zone.animationEligible &&
      zone.hasLightCore &&
      zone.warmth >= 0.4 &&
      zone.y < 0.72)
    .slice(0, 3);
  assert.equal(animatedLights.length, 2);
  assert.ok(animatedLights.every((zone) => zone.animationEligible));
});
