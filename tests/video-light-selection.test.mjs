import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import ts from 'typescript';

const source = fs.readFileSync('src/video-light-selection.ts', 'utf8');
const js = ts.transpileModule(source, {
  compilerOptions: {module: ts.ModuleKind.ESNext},
}).outputText;
const {selectVideoLightZones} = await import(
  `data:text/javascript;base64,${Buffer.from(js).toString('base64')}`
);

const zone = (id, x, y, extra = {}) => ({
  id,
  x,
  y,
  width: 0.05,
  height: 0.06,
  warmth: 0.8,
  strength: 0.9,
  hasLightCore: true,
  color: [230, 190, 120],
  ...extra,
});

test('case A: vending-machine-like source near a thirds point is the only local light', () => {
  const result = selectVideoLightZones([
    zone('vending-machine', 1 / 3 + 0.01, 1 / 3 + 0.01, {strength: 0.95}),
    zone('window-farther', 1 / 3 + 0.06, 1 / 3 + 0.05, {strength: 1}),
    zone('center-light', 0.5, 0.5, {strength: 1}),
  ]);
  assert.equal(result.mode, 'rule-of-thirds');
  assert.deepEqual(result.zones.map(({id}) => id), ['vending-machine']);
});

test('case B: a sign slightly offset from a thirds point is accepted inside tolerance', () => {
  const result = selectVideoLightZones([
    zone('offset-sign', 2 / 3 + 0.075, 1 / 3 - 0.04),
  ]);
  assert.equal(result.mode, 'rule-of-thirds');
  assert.deepEqual(result.zones.map(({id}) => id), ['offset-sign']);
});

test('case C: reflection near a thirds point is rejected', () => {
  const result = selectVideoLightZones([
    zone('river-reflection', 1 / 3, 2 / 3, {isReflection: true, strength: 1}),
    zone('fallback-background', 0.12, 0.2),
  ]);
  assert.equal(result.mode, 'three-layer-fallback');
  assert.deepEqual(result.zones.map(({id}) => id), ['fallback-background']);
});

test('case D: center source is used only when thirds has no valid emitter', () => {
  const result = selectVideoLightZones([
    zone('phone-box', 0.52, 0.49, {strength: 0.95}),
    zone('unsafe-thirds', 1 / 3, 1 / 3, {hasLightCore: false}),
  ]);
  assert.equal(result.mode, 'center');
  assert.deepEqual(result.zones.map(({id}) => id), ['phone-box']);
});

test('case E: no thirds or center source falls back to existing three depth layers', () => {
  const result = selectVideoLightZones([
    zone('background', 0.08, 0.2),
    zone('midground', 0.12, 0.5),
    zone('foreground', 0.9, 0.65),
  ]);
  assert.equal(result.mode, 'three-layer-fallback');
  assert.deepEqual(result.zones.map(({id}) => id), [
    'background',
    'midground',
    'foreground',
  ]);
});

test('case F: multiple windows and signs still select only the best thirds candidate', () => {
  const result = selectVideoLightZones([
    zone('nearest-small-sign', 1 / 3 + 0.01, 1 / 3 + 0.005, {
      width: 0.03,
      height: 0.03,
      strength: 0.85,
    }),
    zone('stronger-but-farther-window', 1 / 3 + 0.045, 1 / 3 + 0.03, {
      strength: 1,
    }),
    zone('other-third-window', 2 / 3 + 0.04, 1 / 3 + 0.03, {
      strength: 1,
    }),
  ]);
  assert.equal(result.mode, 'rule-of-thirds');
  assert.equal(result.zones.length, 1);
  assert.deepEqual(result.zones.map(({id}) => id), ['nearest-small-sign']);
});

test('regression: wall-sized, cold, low, and core-less regions remain unsafe', () => {
  const result = selectVideoLightZones([
    zone('large', 1 / 3, 1 / 3, {width: 0.3, height: 0.2}),
    zone('broad-wall', 2 / 3, 1 / 3, {width: 0.2, height: 0.1}),
    zone('cold', 2 / 3, 1 / 3, {warmth: 0.1}),
    zone('low', 1 / 3, 2 / 3, {y: 0.82}),
    zone('core-less', 1 / 3, 1 / 3, {hasLightCore: false}),
  ]);
  assert.equal(result.mode, 'none');
  assert.deepEqual(result.zones, []);
});

test('regression: strongest safe source is retained per fallback layer', () => {
  const result = selectVideoLightZones([
    zone('background-weak', 0.1, 0.2, {strength: 0.7}),
    zone('background-strong', 0.9, 0.2),
    zone('midground', 0.1, 0.5),
    zone('foreground', 0.9, 0.65),
  ]);
  assert.equal(result.mode, 'three-layer-fallback');
  assert.deepEqual(result.zones.map(({id}) => id), [
    'background-strong',
    'midground',
    'foreground',
  ]);
});
