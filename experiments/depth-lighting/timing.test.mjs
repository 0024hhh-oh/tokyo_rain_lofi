import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import ts from 'typescript';
const source=fs.readFileSync(new URL('./timing.ts', import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {intensity,layers,windows,FRAMES}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
test('three independent layers; two pulses each; seamless return to baseline',()=>{
  assert.equal(FRAMES,900);
  assert.deepEqual(layers,['back','middle','front']);
  for(const d of layers){
    assert.equal(windows[d].length,2);
    assert.equal(intensity(0,d),0);
    assert.equal(intensity(899,d),0);
    for(const [a,b] of windows[d]) assert.equal(intensity((a+b)/2,d),1);
  }
});
test('bounded, reproducible, smooth pulses without overlapping depth flashes',()=>{
  for(let f=0;f<FRAMES;f++){
    assert.ok(layers.filter(d=>intensity(f,d)>0).length<=1);
    for(const d of layers){
      const value=intensity(f,d);
      assert.ok(value>=0&&value<=1);
      assert.equal(value,intensity(f+900,d));
      assert.ok(Math.abs(value-intensity(f-1,d))<0.07);
    }
  }
});
test('isolated workflow and no production registration',()=>{
  const workflow=fs.readFileSync('.github/workflows/three_layer_lighting_artifact.yml','utf8');
  assert.match(workflow,/pull_request:/);
  assert.match(workflow,/contents: read/);
  assert.match(workflow,/persist-credentials: false/);
  assert.match(workflow,/retention-days: 7/);
  const renders=workflow.split('\n').filter(line=>line.includes('run: npx remotion render'));
  assert.equal(renders.length,1);
  assert.match(workflow,/ASSET_DIR=dist\/production-assets bash scripts\/render_night_background.sh/);
  const renderer=fs.readFileSync('scripts/render_night_background.sh','utf8');
  assert.match(renderer,/--frames=0-899 --muted/);
  for(const line of renders) assert.match(line,/--muted\s*$/,'Lighting-only MP4s must not acquire AAC padding');
  assert.doesNotMatch(workflow,/secrets\.|pull_request_target:|push:|schedule:|workflow_run:|upload_youtube|upload_drive|generate_lofi/);
  assert.doesNotMatch(fs.readFileSync('src/Root.tsx','utf8'),/depth-lighting|DepthLighting/);
});

test('river motion starts in first second and remains loop-safe',()=>{
  const p=JSON.parse(fs.readFileSync('experiments/depth-lighting/profiles/river-night.json'));
  const sample=(f,d)=>intensity(f,d,p.timing.windows,p.timing.fadeFrames);
  assert.equal(sample(15,'back'),1);
  for(const d of layers){assert.equal(sample(0,d),0);assert.equal(sample(899,d),0);}
  for(const [f,d] of [[120,'back'],[285,'middle'],[450,'front']]) assert.equal(sample(f,d),1);
});
