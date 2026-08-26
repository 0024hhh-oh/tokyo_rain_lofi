#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import sharp from 'sharp';

const luma = (data, offset) =>
  data[offset] * 0.2126 + data[offset + 1] * 0.7152 + data[offset + 2] * 0.0722;

export const scoreVisibleChanges = ({frames, width, height, zones}) => {
  if (frames.length < 2) throw new Error('at least two validation frames are required');

  return zones.map((zone) => {
    const halfWidth = Math.max(2, Math.floor(zone.width * width * 0.34));
    const halfHeight = Math.max(2, Math.floor(zone.height * height * 0.34));
    const centerX = Math.floor(zone.x * width);
    const centerY = Math.floor(zone.y * height);
    const left = Math.max(0, centerX - halfWidth);
    const right = Math.min(width, centerX + halfWidth);
    const top = Math.max(0, centerY - halfHeight);
    const bottom = Math.min(height, centerY + halfHeight);
    let best = 0;

    for (let first = 0; first < frames.length - 1; first += 1) {
      for (let second = first + 1; second < frames.length; second += 1) {
        let difference = 0;
        let pixels = 0;
        for (let y = top; y < bottom; y += 1) {
          for (let x = left; x < right; x += 1) {
            const offset = (y * width + x) * 3;
            difference += Math.abs(luma(frames[first], offset) - luma(frames[second], offset));
            pixels += 1;
          }
        }
        best = Math.max(best, pixels ? difference / pixels : 0);
      }
    }
    return {id: zone.id, difference: best};
  });
};

const loadFrame = async (filename) => {
  const {data, info} = await sharp(filename)
    .removeAlpha()
    .raw()
    .toBuffer({resolveWithObject: true});
  return {data, width: info.width, height: info.height};
};

const main = async () => {
  const [zonesFile, ...frameFiles] = process.argv.slice(2);
  if (!zonesFile || frameFiles.length < 2) {
    throw new Error('usage: validate_visible_lighting.mjs ZONES_JSON FRAME.png FRAME.png [...]');
  }
  const lighting = JSON.parse(await fs.readFile(zonesFile, 'utf8'));
  const safeZones = (lighting.zones ?? [])
    .filter((zone) =>
      zone.hasLightCore &&
      zone.isCompactEmitter &&
      zone.warmth >= 0.75 &&
      zone.y < 0.40)
    .sort((first, second) => first.y - second.y)
    .slice(0, 1);
  if (!lighting.animate || !safeZones.length) {
    throw new Error('visible-lighting validation requires at least one animated light zone');
  }
  const loaded = await Promise.all(frameFiles.map(loadFrame));
  const {width, height} = loaded[0];
  if (loaded.some((frame) => frame.width !== width || frame.height !== height)) {
    throw new Error('validation frames must have identical dimensions');
  }

  const scores = scoreVisibleChanges({
    frames: loaded.map((frame) => frame.data),
    width,
    height,
    zones: safeZones,
  }).sort((a, b) => b.difference - a.difference);
  // Positive-only glow has a smaller pixel delta than the removed black dim
  // overlay. The current experiment intentionally animates one rear-area light.
  const strongThreshold = Number(process.env.LIGHTING_ZONE_MIN_DELTA ?? 6);
  const peakThreshold = Number(process.env.LIGHTING_PEAK_MIN_DELTA ?? 12);
  const requiredStrongZones = Math.min(1, scores.length);
  const strongZones = scores.filter((score) => score.difference >= strongThreshold);
  const peak = scores[0]?.difference ?? 0;

  console.log(
    `night-test visible lighting scores: ${scores
      .map((score) => `${score.id}=${score.difference.toFixed(2)}`)
      .join(' ')}`,
  );
  if (peak < peakThreshold || strongZones.length < requiredStrongZones) {
    throw new Error(
      `lighting is not visibly changing: peak=${peak.toFixed(2)} ` +
      `(required ${peakThreshold}), strong_zones=${strongZones.length} ` +
      `(required ${requiredStrongZones} at delta ${strongThreshold})`,
    );
  }
  console.log(
    `night-test visible lighting verified: peak=${peak.toFixed(2)} ` +
    `strong_zones=${strongZones.length}`,
  );
};

const isDirectRun = process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isDirectRun) await main();
