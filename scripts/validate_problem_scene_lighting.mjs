#!/usr/bin/env node
import sharp from 'sharp';
import fs from 'node:fs/promises';

const [steadyFile, boostFile] = process.argv.slice(2);
if (!steadyFile || !boostFile) {
  throw new Error('usage: validate_problem_scene_lighting.mjs STEADY BOOST');
}

const lighting = JSON.parse(await fs.readFile('src/generated-light-zones.json', 'utf8'));
const safeZones = lighting.zones
  .filter((zone) => zone.hasLightCore && zone.warmth >= 0.4 && zone.y < 0.72)
  .slice(0, 3);
if (safeZones.length !== 3) {
  throw new Error(`Expected three safe problem-scene lights; got ${safeZones.length}`);
}

const falseWall = {x: 0.51265, y: 0.59972};
const wallSelected = safeZones.some((zone) =>
  Math.hypot(zone.x - falseWall.x, zone.y - falseWall.y) < 0.06);
if (wallSelected) {
  throw new Error('The diffuse tunnel pillar was selected as an animated light.');
}

const boostZone = safeZones[2];
if (!(boostZone.x > 0.52 && boostZone.x < 0.57 && boostZone.y > 0.45 && boostZone.y < 0.54)) {
  throw new Error(`Expected the central signal as boost target; got x=${boostZone.x} y=${boostZone.y}`);
}

const decode = async (file, roi) => sharp(file)
  .extract(roi)
  .removeAlpha()
  .raw()
  .toBuffer();

const meanDelta = async (roi) => {
  const [steady, changed] = await Promise.all([
    decode(steadyFile, roi),
    decode(boostFile, roi),
  ]);
  let total = 0;
  for (let index = 0; index < steady.length; index += 1) {
    total += Math.abs(steady[index] - changed[index]);
  }
  return total / steady.length;
};

const wallDelta = await meanDelta({left: 922, top: 620, width: 106, height: 136});
const signalDelta = await meanDelta({left: 998, top: 490, width: 96, height: 96});

if (signalDelta < 1) {
  throw new Error(`Central signal change is too weak: ${signalDelta.toFixed(2)}`);
}
if (wallDelta > Math.min(2.5, signalDelta * 0.12)) {
  throw new Error(
    `Wall changed too much: wall=${wallDelta.toFixed(2)} signal=${signalDelta.toFixed(2)}`,
  );
}

console.log(
  `Problem scene verified: wall=${wallDelta.toFixed(2)} signal=${signalDelta.toFixed(2)} ` +
  `ratio=${(wallDelta / signalDelta).toFixed(3)}`,
);
