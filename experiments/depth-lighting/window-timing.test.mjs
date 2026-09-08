import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const source=fs.readFileSync(new URL('./window-timing.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {splitWindows,windowIntensity}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const p=JSON.parse(fs.readFileSync(new URL('./profiles/river-night.json',import.meta.url)));
test('28 original masks, staggered within each building, no more than three windows',()=>{
  const windows=splitWindows(p.emitters);
  assert.equal(windows.length,28);
  assert.deepEqual(windows.map(w=>w.sourceMask),p.emitters.flatMap(g=>g.sourceMask.match(/<path\s[^>]+\/>/g)));
  let idle=0,max=0;
  for(let frame=0;frame<900;frame++){
    const active=windows.filter(w=>windowIntensity(frame,w.pulseWindow)>0);
    assert.ok(active.length<=3);
    assert.equal(new Set(active.map(w=>w.group)).size,active.length);
    max=Math.max(max,active.length);if(!active.length)idle++;
  }
  assert.ok(idle>30);
  for(const w of windows){assert.equal(windowIntensity(0,w.pulseWindow),0);assert.equal(windowIntensity(899,w.pulseWindow),0);assert.equal(windowIntensity((w.pulseWindow[0]+w.pulseWindow[1])/2,w.pulseWindow),1);}
  console.log({maxSimultaneousWindows:max,idleFrames:idle});
});
