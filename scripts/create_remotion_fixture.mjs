#!/usr/bin/env node
import fs from 'node:fs/promises';
import sharp from 'sharp';

await fs.mkdir('video_assets', {recursive: true});
const windows = [
  '<rect x="365" y="438" width="80" height="55" fill="#ffc16b"/>',
  '<rect x="710" y="350" width="78" height="58" fill="#ffd89b"/>',
  '<rect x="1230" y="500" width="88" height="62" fill="#ffb657"/>',
  '<rect x="1515" y="400" width="76" height="54" fill="#ffe1aa"/>',
].join('');
const svg = `<svg width="1920" height="1080" xmlns="http://www.w3.org/2000/svg">
  <rect width="1920" height="1080" fill="#0b1220"/>
  <rect y="650" width="1920" height="430" fill="#08090d"/>
  ${windows}
</svg>`;
await sharp(Buffer.from(svg)).png().toFile('video_assets/background.png');
