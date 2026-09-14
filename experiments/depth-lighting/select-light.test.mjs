import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import ts from 'typescript';
import {validateProfile} from './prepare-profile.mjs';

const source = fs.readFileSync(new URL('./select-light.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.ESNext}}).outputText;
const {selectLightingMode, getRuleOfThirdsCandidates} = await import('data:text/javascript;base64,' + Buffer.from(js).toString('base64'));
const mask = '<path d="M1 1 L5 1 L5 5 L1 5Z"/>';
const profile = (...lights) => ({source: {width: 1200, height: 900}, localLightCandidates: lights});
const light = (id, kind, x, y, overrides = {}) => ({
  id, kind, depth: 'middle', sourceMask: mask,
  sourceRoi: [x - 12, y - 12, x + 12, y + 12],
  prominence: .8, clipRisk: 0, isEmitter: true, ...overrides,
});
test('A: vending machine at a thirds intersection is the only local light', () => {
  const result = selectLightingMode(profile(light('vending','vending_machine',400,300)));
  assert.equal(result.mode, 'local'); assert.equal(result.candidate.id, 'vending');
});
test('B: off-center sign qualifies within configurable 5–10% image-relative radius', () => {
  const p = profile(light('sign','sign',490,354));
  p.localLightSearch = {thirdsRadiusX: .08, thirdsRadiusY: .08, centerRadiusX: .05, centerRadiusY: .05};
  assert.equal(selectLightingMode(p).candidate.id, 'sign');
  p.localLightSearch.thirdsRadiusX = .05;
  assert.equal(selectLightingMode(p).mode, 'three-layer');
});
test('C: river reflection or clipped non-emitter cannot become a source', () => {
  const reflection = light('river','reflection',400,300,{isEmitter:false});
  const blown = light('blown','sign',800,300,{clipRisk:.8});
  assert.equal(selectLightingMode(profile(reflection,blown)).mode, 'three-layer');
});
test('D: center phone booth wins when thirds have no suitable source', () => {
  const result = selectLightingMode(profile(light('booth','phone_booth',600,450)));
  assert.equal(result.region,'center'); assert.equal(result.candidate.id,'booth');
});
test('E: no suitable lights retains existing three-layer fallback', () => {
  assert.deepEqual(selectLightingMode(profile()),{mode:'three-layer'});
  const old = JSON.parse(fs.readFileSync(new URL('./profiles/tokyo-approved.json',import.meta.url)));
  assert.deepEqual(selectLightingMode(old),{mode:'three-layer'});
});
test('F: multiple windows and signs produce exactly one source; thirds precede center', () => {
  const p = profile(light('center','sign',600,450), light('window','window',400,300),
    light('other','sign',800,310));
  assert.equal(getRuleOfThirdsCandidates(p).length,2);
  const result = selectLightingMode(p);
  assert.equal(result.mode,'local'); assert.equal(result.candidate.id,'window');
  assert.equal(Object.keys(result).filter(k=>k==='candidate').length,1);
});
test('oversized light fails safely and existing source stays unchanged', () => {
  const big = light('large','sign',400,300,{sourceRoi:[200,100,700,500]});
  assert.equal(selectLightingMode(profile(big)).mode,'three-layer');
  const scene=fs.readFileSync(new URL('./Scene.tsx',import.meta.url),'utf8');
  assert.match(scene,/choice.mode === 'local'/);
  assert.match(scene,/fallbackToExistingThreeLayerMode/);
});
test('profile validation rejects unsafe or reflective candidate masks before rendering', async () => {
  const approved=JSON.parse(fs.readFileSync(new URL('./profiles/street-night.json',import.meta.url)));
  const image=fs.readFileSync('test_assets/street-night.jpg');
  approved.localLightCandidates=[light('safe','window',638,347, {
    sourceRoi:[630,333,646,361],
    sourceMask:approved.layers.middle,
  })];
  await validateProfile(approved,image);
  for (const change of [
    p=>p.localLightCandidates[0].sourceMask='<image href="x"/>',
    p=>p.localLightCandidates[0].isEmitter=false,
    p=>p.localLightCandidates[0].kind='reflection',
    p=>p.localLightCandidates[0].sourceRoi=[0,0,1000,800],
    p=>p.localLightSearch={thirdsRadiusX:1},
  ]) {
    const bad=structuredClone(approved); change(bad);
    await assert.rejects(validateProfile(bad,image));
  }
});
