#!/usr/bin/env node
import sharp from 'sharp';
import fs from 'node:fs/promises';

const [steadyFile, dimFile] = process.argv.slice(2);
if (!steadyFile || !dimFile) {
  throw new Error('usage: validate_problem_scene_lighting.mjs STEADY DIM');
}

const lighting = JSON.parse(await fs.readFile('src/generated-light-zones.json', 'utf8'));
const safeZones = lighting.zones
  .filter((zone) => zone.hasLightCore && zone.isCompactSource && zone.y < 0.72)
  .slice(0, 3);
if (safeZones.length !== 3) {
  throw new Error('Expected three prominent problem-scene lights; got ' + safeZones.length);
}

const falseWall = {x: 0.51265, y: 0.59972};
const wallSelected = safeZones.some((zone) =>
  Math.hypot(zone.x - falseWall.x, zone.y - falseWall.y) < 0.06);
if (wallSelected) {
  throw new Error('The diffuse tunnel pillar was selected as an animated light.');
}

const prominentStreetlamp = safeZones[0];
if (!(
  prominentStreetlamp.x > 0.40 &&
  prominentStreetlamp.x < 0.50 &&
  prominentStreetlamp.y > 0.05 &&
  prominentStreetlamp.y < 0.16
)) {
  throw new Error(
    'Expected the obvious upper streetlamp to rank first; got x=' +
    prominentStreetlamp.x + ' y=' + prominentStreetlamp.y,
  );
}

const decode = async (file, roi) => sharp(file)
  .extract(roi)
  .removeAlpha()
  .raw()
  .toBuffer();

const meanDelta = async (roi) => {
  const [steady, changed] = await Promise.all([
    decode(steadyFile, roi),
    decode(dimFile, roi),
  ]);
  let total = 0;
  for (let index = 0; index < steady.length; index += 1) {
    total += Math.abs(steady[index] - changed[index]);
  }
  return total / steady.length;
};

const lampCenterX = Math.round(prominentStreetlamp.x * 1920);
const lampCenterY = Math.round(prominentStreetlamp.y * 1080);
const lampRoi = {
  left: Math.max(0, lampCenterX - 70),
  top: Math.max(0, lampCenterY - 70),
  width: 140,
  height: 140,
};
const wallRoi = {left: 922, top: 620, width: 106, height: 136};
const [lampDelta, wallDelta] = await Promise.all([
  meanDelta(lampRoi),
  meanDelta(wallRoi),
]);

if (lampDelta < 2) {
  throw new Error('Prominent streetlamp change is too weak: ' + lampDelta.toFixed(2));
}
if (wallDelta > Math.min(2.5, lampDelta * 0.12)) {
  throw new Error(
    'Wall changed too much: wall=' + wallDelta.toFixed(2) +
    ' lamp=' + lampDelta.toFixed(2),
  );
}

console.log(
  'Problem scene verified: wall=' + wallDelta.toFixed(2) +
  ' lamp=' + lampDelta.toFixed(2) +
  ' ratio=' + (wallDelta / lampDelta).toFixed(3) +
  ' targets=' + safeZones
    .map((zone) => zone.x.toFixed(3) + ',' + zone.y.toFixed(3))
    .join(';'),
);
