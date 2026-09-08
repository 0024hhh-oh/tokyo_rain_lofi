import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateProfile} from './prepare-profile.mjs';
test('street source is image-specific, one light at a time, no reflections',async()=>{
  const profile=JSON.parse(await readFile(new URL('./profiles/street-night.json',import.meta.url)));
  const image=await readFile(new URL('../../test_assets/street-night.jpg',import.meta.url));
  await validateProfile(profile,image);
  for(let f=0;f<900;f++) assert.ok(profile.scheduledLights.filter(l=>f>l.pulseWindow[0] && f<l.pulseWindow[1]).length<=1);
  const invalid=structuredClone(profile);
  invalid.scheduledLights[1].building=invalid.scheduledLights[0].building;
  invalid.scheduledLights[1].pulseWindow=invalid.scheduledLights[0].pulseWindow;
  await assert.rejects(validateProfile(invalid,image),/simultaneous/);
});
