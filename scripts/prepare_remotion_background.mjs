#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import sharp from 'sharp';

const WIDTH = 1920;
const HEIGHT = 1080;
const OVERLAY_FILENAME = 'light_overlay.png';

const findAsset = async (assetDir, filenames) => {
  for (const filename of filenames) {
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

const preparePng = async (source, destination) => {
  await sharp(source).rotate().resize(WIDTH, HEIGHT, {
    fit: 'cover', position: 'centre',
  }).ensureAlpha().png().toFile(destination);
};

export const prepareBackground = async (assetDir = process.env.ASSET_DIR ?? 'video_assets') => {
  const source = await findAsset(assetDir, ['background.png', 'background.jpg', 'background.jpeg']);
  if (!source) {
    console.log('Remotion lighting skipped: no static background image found.');
    return {animate: false, overlay: null};
  }

  await fs.mkdir('public', {recursive: true});
  await preparePng(source, 'public/background.png');
  const overlaySource = await findAsset(assetDir, [OVERLAY_FILENAME]);
  if (overlaySource) await preparePng(overlaySource, 'public/light_overlay.png');
  else await fs.rm('public/light_overlay.png', {force: true});

  const result = {
    animate: Boolean(overlaySource),
    overlay: overlaySource ? OVERLAY_FILENAME : null,
    width: WIDTH,
    height: HEIGHT,
  };
  await fs.writeFile('src/generated-light-zones.json', `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  console.log(`Remotion lighting: overlay=${result.overlay ?? 'none'} animate=${result.animate} (no image light detection)`);
  return result;
};

const isDirectRun = process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isDirectRun) await prepareBackground(process.argv[2]);
