import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs/promises';
import sharp from 'sharp';
import {createHash} from 'node:crypto';
import {validateProfile} from './prepare-profile.mjs';
const profile = JSON.parse(await fs.readFile(new URL('./profiles/tokyo-approved.json', import.meta.url)));
const image = await fs.readFile('test_assets/three-layer-tokyo-scene.jpg');
test('accepted Tokyo masks match original image', async()=> {
  await validateProfile(profile, image);
});
test('another image cannot silently reuse approved Tokyo masks', async()=> {
  const other = await sharp({create:{width:32,height:18,channels:3,background:'#102030'}}).png().toBuffer();
  await assert.rejects(validateProfile(profile, other), /does not match/);
  const own = structuredClone(profile);
  own.source = {file:'depth-lighting/other.png',width:32,height:18,sha256:createHash('sha256').update(other).digest('hex')};
  own.layers = Object.fromEntries(['back','middle','front'].map(d=>[d,'<ellipse cx="10" cy="10" rx="2" ry="2"/>']));
  await validateProfile(own, other);
});
test('rejects wrong dimensions, unsafe paths, active SVG and invalid strength', async()=> {
  for (const mutate of [p=>p.source.width++, p=>p.source.file='../source.jpg', p=>p.layers.front='<image href="https://example.com"/>', p=>p.style.coreOpacity=2]) {
    const bad = structuredClone(profile); mutate(bad);
    await assert.rejects(validateProfile(bad, image));
  }
});
test('river profile matches its source and cannot use the Tokyo image', async()=> {
  const river = JSON.parse(await fs.readFile(new URL('./profiles/river-night.json', import.meta.url)));
  await validateProfile(river, await fs.readFile('test_assets/river-night.jpg'));
  await assert.rejects(validateProfile(river, image), /does not match/);
});
test('paired reflections reject detached source and excessive reflection strength', async()=> {
  const p=JSON.parse(await fs.readFile(new URL('./profiles/river-night.json',import.meta.url)));
  const image=await fs.readFile('test_assets/river-night.jpg');
  for(const change of [p=>p.pairs[0].sourceMask='',p=>p.pairs[0].reflectionGain=.9,p=>p.pairs[0].reflectionMask='<image href="x"/>']) {
    const bad=structuredClone(p);change(bad);await assert.rejects(validateProfile(bad,image));
  }
});
