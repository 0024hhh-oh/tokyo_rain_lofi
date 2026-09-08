import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {prepareApprovedLighting} from '../scripts/prepare_approved_lighting.mjs';

test('production selects exact approved images and removes stale props for unknown images',async()=>{
  const dir=await fs.mkdtemp(path.join(os.tmpdir(),'approved-lighting-'));
  try {
    const props=path.join(dir,'props.json'), publicDir=path.join(dir,'public');
    for(const name of ['three-layer-tokyo-scene','river-night','street-night']) {
      await fs.copyFile(`test_assets/${name}.jpg`,path.join(dir,'background.jpg'));
      assert.equal(await prepareApprovedLighting(dir,publicDir,props),true);
      const {profile}=JSON.parse(await fs.readFile(props));
      assert.deepEqual(await fs.readFile(path.join(publicDir,profile.source.file)),await fs.readFile(path.join(dir,'background.jpg')));
    }
    await fs.writeFile(path.join(dir,'background.jpg'),'unregistered image');
    assert.equal(await prepareApprovedLighting(dir,publicDir,props),false);
    await assert.rejects(fs.access(props));
  } finally { await fs.rm(dir,{recursive:true,force:true}); }
});
