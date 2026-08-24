import assert from 'node:assert/strict';
import test from 'node:test';
import sharp from 'sharp';

import {analyzeLightZones} from '../scripts/prepare_remotion_background.mjs';

const safeZonesFor = async (batch) => {
  const {data, info} = await sharp(`test_assets/problem-night-batch-${batch}.png`)
    .removeAlpha()
    .raw()
    .toBuffer({resolveWithObject: true});
  const lighting = analyzeLightZones({data, width: info.width, height: info.height});
  return lighting.zones
    .filter((zone) =>
      zone.hasLightCore &&
      zone.isCompactEmitter &&
      zone.warmth >= 0.75 &&
      zone.y < 0.72)
    .slice(0, 3);
};

test('problem night scenes fail closed instead of animating walls and roads', async () => {
  assert.deepEqual(await safeZonesFor(20), []);
  assert.deepEqual(await safeZonesFor(21), []);
});

test('tram scene selects the street lamp instead of the tram or road', async () => {
  const safe = await safeZonesFor(24);
  assert.equal(safe.length, 1);
  assert.ok(Math.abs(safe[0].x - 0.447) < 0.015);
  assert.ok(Math.abs(safe[0].y - 0.433) < 0.015);
});

test('river scene selects three lamps and excludes the river reflection', async () => {
  const safe = await safeZonesFor(25);
  assert.equal(safe.length, 3);
  assert.ok(safe.every((zone) =>
    Math.hypot(zone.x - 0.447, zone.y - 0.581) > 0.12));
});
