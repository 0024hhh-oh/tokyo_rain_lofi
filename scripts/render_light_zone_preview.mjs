#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const [sourceFile = 'public/background.png', outputFile = 'dist/problem-light-targets.png'] =
  process.argv.slice(2);

const lighting = JSON.parse(
  await fs.readFile('src/generated-light-zones.json', 'utf8'),
);
const selected = lighting.zones
  .filter((zone) => zone.hasLightCore && zone.isCompactSource && zone.y < 0.72)
  .slice(0, 3);

const image = sharp(sourceFile);
const metadata = await image.metadata();
const width = metadata.width;
const height = metadata.height;
if (!width || !height) throw new Error('Could not read preview image dimensions.');

const escapeXml = (value) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;');

const boxes = selected.map((zone, index) => {
  const boxWidth = zone.width * width;
  const boxHeight = zone.height * height;
  const left = zone.x * width - boxWidth / 2;
  const top = zone.y * height - boxHeight / 2;
  const labelX = Math.max(24, left);
  const labelY = Math.max(32, top);
  return `
    <rect x="${left}" y="${top}" width="${boxWidth}" height="${boxHeight}"
      rx="16" fill="none" stroke="#00f5ff" stroke-width="7"/>
    <circle cx="${labelX}" cy="${labelY}" r="23" fill="#00f5ff"/>
    <text x="${labelX}" y="${labelY + 9}" text-anchor="middle"
      font-family="sans-serif" font-size="28" font-weight="700" fill="#001014">${index + 1}</text>
  `;
}).join('');

const details = selected.map((zone, index) =>
  `#${index + 1} x=${zone.x.toFixed(3)} y=${zone.y.toFixed(3)} contrast=${zone.contrast.toFixed(1)}`,
).join('   ');

const svg = `
<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
  ${boxes}
  <rect x="0" y="${height - 76}" width="${width}" height="76" fill="rgba(0,0,0,0.76)"/>
  <text x="28" y="${height - 42}" font-family="sans-serif" font-size="28"
    font-weight="700" fill="#ffffff">Selected light targets: ${selected.length}</text>
  <text x="28" y="${height - 12}" font-family="monospace" font-size="20"
    fill="#00f5ff">${escapeXml(details)}</text>
</svg>`;

await fs.mkdir(path.dirname(outputFile), {recursive: true});
await image
  .composite([{input: Buffer.from(svg)}])
  .png()
  .toFile(outputFile);

console.log(`Light target preview: ${outputFile} (${selected.length} selected)`);
