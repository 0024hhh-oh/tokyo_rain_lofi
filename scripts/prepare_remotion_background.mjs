#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import sharp from 'sharp';

const WIDTH = 160;
const HEIGHT = 90;
const MAX_ZONES = 50;

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export const analyzeLightZones = ({data, width, height}) => {
  const pixels = [];
  for (let index = 0; index < width * height; index += 1) {
    const offset = index * 3;
    const red = data[offset];
    const green = data[offset + 1];
    const blue = data[offset + 2];
    const luma = red * 0.2126 + green * 0.7152 + blue * 0.0722;
    pixels.push({red, green, blue, luma});
  }

  const sortedLuma = pixels.map((pixel) => pixel.luma).sort((a, b) => a - b);
  const averageLuma = sortedLuma.reduce((sum, value) => sum + value, 0) /
    sortedLuma.length;
  const p90 = sortedLuma[Math.floor(sortedLuma.length * 0.9)];
  const threshold = clamp(Math.max(145, p90 + 10), 145, 225);
  const isNight = averageLuma < 142;
  const active = new Uint8Array(width * height);

  for (let y = Math.floor(height * 0.06); y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const index = y * width + x;
      const pixel = pixels[index];
      const warmEnough = pixel.red >= pixel.blue * 0.88;
      const unmistakablyBright = pixel.luma >= 225;
      const saturatedWarmCore = pixel.red >= 150 &&
        pixel.red - Math.max(pixel.green, pixel.blue) >= 45 &&
        pixel.luma >= 80;
      if (
        (pixel.luma >= threshold && (warmEnough || unmistakablyBright)) ||
        saturatedWarmCore
      ) {
        active[index] = 1;
      }
    }
  }

  const seen = new Uint8Array(width * height);
  const components = [];
  const neighbors = [
    [-1, -1], [0, -1], [1, -1],
    [-1, 0], [1, 0],
    [-1, 1], [0, 1], [1, 1],
  ];

  for (let start = 0; start < active.length; start += 1) {
    if (!active[start] || seen[start]) continue;
    const queue = [start];
    seen[start] = 1;
    let cursor = 0;
    let minX = width;
    let minY = height;
    let maxX = 0;
    let maxY = 0;
    let weightedX = 0;
    let weightedY = 0;
    let totalWeight = 0;
    let warmthTotal = 0;
    let peakLuma = 0;
    let warmCorePixels = 0;
    let weightedRed = 0;
    let weightedGreen = 0;
    let weightedBlue = 0;

    while (cursor < queue.length) {
      const index = queue[cursor++];
      const x = index % width;
      const y = Math.floor(index / width);
      const pixel = pixels[index];
      const weight = Math.max(1, pixel.luma - threshold + 4);
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
      weightedX += x * weight;
      weightedY += y * weight;
      totalWeight += weight;
      weightedRed += pixel.red * weight;
      weightedGreen += pixel.green * weight;
      weightedBlue += pixel.blue * weight;
      warmthTotal += clamp((pixel.red - pixel.blue + 30) / 110, 0, 1);
      peakLuma = Math.max(peakLuma, pixel.luma);
      if (
        pixel.red >= 150 &&
        pixel.red - Math.max(pixel.green, pixel.blue) >= 45
      ) {
        warmCorePixels += 1;
      }

      for (const [dx, dy] of neighbors) {
        const nx = x + dx;
        const ny = y + dy;
        if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue;
        const next = ny * width + nx;
        if (active[next] && !seen[next]) {
          seen[next] = 1;
          queue.push(next);
        }
      }
    }

    const boxWidth = maxX - minX + 1;
    const boxHeight = maxY - minY + 1;
    const area = queue.length;
    if (area < 2 || boxWidth / width > 0.34 || boxHeight / height > 0.3) {
      continue;
    }

    const averageRed = weightedRed / totalWeight;
    const averageGreen = weightedGreen / totalWeight;
    const averageBlue = weightedBlue / totalWeight;
    const aspectRatio = boxWidth / boxHeight;
    const isCompactRedSignal =
      area <= 14 &&
      boxWidth <= 4 &&
      boxHeight <= 4 &&
      aspectRatio >= 0.55 &&
      aspectRatio <= 1.8 &&
      averageRed >= 145 &&
      averageRed >= averageGreen * 1.5 &&
      averageRed >= averageBlue * 1.7;

    components.push({
      area,
      animationEligible: !isCompactRedSignal,
      x: weightedX / totalWeight / width,
      y: weightedY / totalWeight / height,
      width: clamp((boxWidth + 7) / width, 0.045, 0.2),
      height: clamp((boxHeight + 5) / height, 0.055, 0.22),
      warmth: warmthTotal / area,
      hasLightCore: peakLuma >= 205 || warmCorePixels >= 2,
      color: [
        Math.round(averageRed),
        Math.round(averageGreen),
        Math.round(averageBlue),
      ],
      score: totalWeight * Math.sqrt(area),
    });
  }

  const selected = [];
  for (const component of components.sort((a, b) => b.score - a.score)) {
    const overlaps = selected.some((zone) => {
      const dx = (component.x - zone.x) / Math.max(component.width, zone.width);
      const dy = (component.y - zone.y) / Math.max(component.height, zone.height);
      return dx * dx + dy * dy < 0.42;
    });
    if (!overlaps) selected.push(component);
    if (selected.length >= MAX_ZONES) break;
  }

  const zones = selected.map((zone, index) => ({
    id: `light-${index + 1}`,
    x: Number(zone.x.toFixed(5)),
    y: Number(zone.y.toFixed(5)),
    width: Number(zone.width.toFixed(5)),
    height: Number(zone.height.toFixed(5)),
    warmth: Number(zone.warmth.toFixed(4)),
    hasLightCore: zone.hasLightCore,
    animationEligible: zone.animationEligible,
    color: zone.color,
    strength: Number(clamp(0.62 + Math.log2(zone.area + 1) * 0.08, 0.62, 1).toFixed(4)),
  }));

  return {
    animate: isNight && zones.length > 0,
    averageLuma: Number(averageLuma.toFixed(2)),
    threshold: Number(threshold.toFixed(2)),
    zones,
  };
};

const findBackgroundImage = async (assetDir) => {
  for (const filename of ['background.png', 'background.jpg', 'background.jpeg']) {
    const candidate = path.join(assetDir, filename);
    try {
      const stat = await fs.stat(candidate);
      if (stat.size > 0) return candidate;
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }
  return null;
};

export const prepareBackground = async (assetDir = process.env.ASSET_DIR ?? 'video_assets') => {
  const source = await findBackgroundImage(assetDir);
  if (!source) {
    console.log('Remotion lighting skipped: no static background image found.');
    return {animate: false, skipped: 'no-static-image', zones: []};
  }

  await fs.mkdir('public', {recursive: true});
  const normalized = sharp(source).rotate().resize(1920, 1080, {
    fit: 'cover',
    position: 'centre',
  });
  await normalized.clone().png().toFile('public/background.png');
  const {data, info} = await normalized
    .clone()
    .resize(WIDTH, HEIGHT, {fit: 'fill'})
    .removeAlpha()
    .raw()
    .toBuffer({resolveWithObject: true});
  const analysis = analyzeLightZones({data, width: info.width, height: info.height});
  await fs.writeFile(
    'src/generated-light-zones.json',
    `${JSON.stringify(analysis, null, 2)}\n`,
    'utf8',
  );
  console.log(
    `Remotion lighting analysis: animate=${analysis.animate} ` +
    `average_luma=${analysis.averageLuma} threshold=${analysis.threshold} ` +
    `zones=${analysis.zones.length}`,
  );
  return analysis;
};

const isDirectRun = process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isDirectRun) {
  await prepareBackground(process.argv[2]);
}
