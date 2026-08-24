#!/usr/bin/env node
import fs from 'node:fs/promises';
import sharp from 'sharp';

await fs.mkdir('video_assets', {recursive: true});
const windows = [
  '<rect x="330" y="420" width="72" height="60" fill="#ffebb4"/>',
  '<rect x="690" y="340" width="72" height="60" fill="#ffe0a0"/>',
  '<rect x="1180" y="480" width="72" height="60" fill="#fff0c2"/>',
  '<rect x="1500" y="390" width="72" height="60" fill="#ffe6ad"/>',
].join('');
const svg = `<svg width="1920" height="1080" xmlns="http://www.w3.org/2000/svg">
  <rect width="1920" height="1080" fill="#0b1220"/>
  <rect y="650" width="1920" height="430" fill="#08090d"/>
  ${windows}
</svg>`;
await sharp(Buffer.from(svg)).png().toFile('video_assets/background.png');
