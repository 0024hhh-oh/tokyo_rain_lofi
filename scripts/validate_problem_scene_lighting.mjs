#!/usr/bin/env node
import sharp from 'sharp';
import fs from 'node:fs/promises';

const [steadyFile, boostFile] = process.argv.slice(2);
if (!steadyFile || !boostFile) {
  throw new Error('usage: validate_problem_scene_lighting.mjs STEADY BOOST');
}

const lighting = JSON.parse(await fs.readFile('src/generated-light-zones.json', 'utf8'));
const safeZones = lighting.zones
  .filter((zone) =>
    zone.hasLightCore &&
    zone.isCompactEmitter &&
    zone.warmth >= 0.75 &&
    zone.y < 0.72)
  .slice(0, 3);
if (safeZones.length !== 1) {
  throw new Error(`Expected one compact problem-scene emitter; got ${safeZones.length}`);
}

const falseWall = {x: 0.51265, y: 0.59972};
const wallSelected = safeZones.some((zone) =>
  Math.hypot(zone.x - falseWall.x, zone.y - falseWall.y) < 0.06);
if (wallSelected) {
  throw new Error('The diffuse tunnel pillar was selected as an animated light.');
}

const boostZone = safeZones[0];

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
const emitterWidth = Math.max(16, Math.floor(boostZone.width * 1920 * 0.5));
const emitterHeight = Math.max(16, Math.floor(boostZone.height * 1080 * 0.5));
const emitterDelta = await meanDelta({
  left: Math.max(0, Math.floor(boostZone.x * 1920 - emitterWidth / 2)),
  top: Math.max(0, Math.floor(boostZone.y * 1080 - emitterHeight / 2)),
  width: emitterWidth,
  height: emitterHeight,
});

if (emitterDelta < 1) {
  throw new Error(`Selected emitter change is too weak: ${emitterDelta.toFixed(2)}`);
}
if (wallDelta > Math.min(2.5, emitterDelta * 0.12)) {
  throw new Error(
    `Wall changed too much: wall=${wallDelta.toFixed(2)} emitter=${emitterDelta.toFixed(2)}`,
  );
}

console.log(
  `Problem scene verified: wall=${wallDelta.toFixed(2)} emitter=${emitterDelta.toFixed(2)} ` +
  `ratio=${(wallDelta / emitterDelta).toFixed(3)}`,
);
