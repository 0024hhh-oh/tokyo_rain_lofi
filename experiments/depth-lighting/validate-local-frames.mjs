import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import sharp from 'sharp';

async function pixels(file) {
  const {data, info} = await sharp(file).removeAlpha().raw().toBuffer({resolveWithObject:true});
  assert.equal(info.width,1920); assert.equal(info.height,1080); assert.equal(info.channels,3);
  return data;
}
const [baseline, start, lit, end] = await Promise.all(
  ['baseline','local-start','local-lit','local-end'].map(n=>pixels(`dist/depth-lighting/${n}.png`)));
assert.deepEqual(start,baseline,'frame 0 must match untouched original');
assert.deepEqual(end,baseline,'frame 899 must return to untouched original');
let changed=0;
for(let y=0;y<1080;y++)for(let x=0;x<1920;x++) {
  const idx=(y*1920+x)*3;
  const difference=Math.max(0,lit[idx]-baseline[idx],lit[idx+1]-baseline[idx+1],lit[idx+2]-baseline[idx+2]);
  if (x>=775 && x<=820 && y>=403 && y<=466 && difference>2) changed++;
  if ((x<690 || x>925 || y<320 || y>535) && difference>1)
    throw new Error(`Light leaked far outside designated source at ${x},${y}`);
  for(let c=0;c<3;c++) assert.ok(lit[idx+c]>=baseline[idx+c], 'No original pixel may dim');
}
assert.ok(changed>20,`Expected visible local brightening; changed ${changed} pixels`);
console.log(`Verified one source: ${changed} brighter pixels near window, no distant changes or dimming`);
