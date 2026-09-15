#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import sharp from 'sharp';

const luma = (data, offset) =>
  data[offset] * 0.2126 + data[offset + 1] * 0.7152 + data[offset + 2] * 0.0722;

export const scorePositiveLocalChange = ({baseline, lit, width, height}) => {
  let changedPixels = 0;
  let negativePixels = 0;
  let positiveTotal = 0;
  let peak = 0;
  let left = width;
  let right = -1;
  let top = height;
  let bottom = -1;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const offset = (y * width + x) * 3;
      const delta = luma(lit, offset) - luma(baseline, offset);
      if (delta <= -2) negativePixels += 1;
      if (delta < 4) continue;
      changedPixels += 1;
      positiveTotal += delta;
      peak = Math.max(peak, delta);
      left = Math.min(left, x);
      right = Math.max(right, x);
      top = Math.min(top, y);
      bottom = Math.max(bottom, y);
    }
  }

  const framePixels = width * height;
  const bboxPixels = changedPixels
    ? (right - left + 1) * (bottom - top + 1)
    : 0;
  return {
    changedPixels,
    meanPositiveDelta: changedPixels ? positiveTotal / changedPixels : 0,
    negativePixels,
    peak,
    changedRatio: changedPixels / framePixels,
    bboxRatio: bboxPixels / framePixels,
  };
};

const loadFrame = async (filename) => {
  const {data, info} = await sharp(filename)
    .removeAlpha()
    .raw()
    .toBuffer({resolveWithObject: true});
  return {data, width: info.width, height: info.height};
};

const main = async () => {
  const [baselineFile, litFile] = process.argv.slice(2);
  if (!baselineFile || !litFile) {
    throw new Error('usage: validate_video_lighting_pair.mjs BASELINE.png LIT.png');
  }
  const [baseline, lit] = await Promise.all([
    loadFrame(baselineFile),
    loadFrame(litFile),
  ]);
  if (baseline.width !== lit.width || baseline.height !== lit.height) {
    throw new Error('baseline and lit frames must have identical dimensions');
  }

  const score = scorePositiveLocalChange({
    baseline: baseline.data,
    lit: lit.data,
    width: baseline.width,
    height: baseline.height,
  });
  console.log(`production video lighting pair: ${JSON.stringify(score)}`);

  if (score.changedPixels < 300 || score.meanPositiveDelta < 10 || score.peak < 30) {
    throw new Error('production video glow is not visibly brighter');
  }
  if (score.changedRatio > 0.04 || score.bboxRatio > 0.06) {
    throw new Error('production video glow is not local');
  }
  if (score.negativePixels > score.changedPixels * 0.02) {
    throw new Error('production video lighting must not dim the source');
  }
};

const isDirectRun = process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isDirectRun) await main();
