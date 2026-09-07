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
  assert.doesNotMatch(workflow,/secrets\.|pull_request_target:|push:|schedule:|workflow_run:|upload_youtube|upload_drive|generate_lofi/);
  assert.doesNotMatch(fs.readFileSync('src/Root.tsx','utf8'),/depth-lighting|DepthLighting/);
});
