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

test('video combines thirds, center, and depth-layer candidates without duplicates', () => {
  const result = selectVideoLightZones([
    zone('thirds-a', 1 / 3 + 0.03, 1 / 3),
    zone('thirds-b', 2 / 3, 1 / 3),
    zone('center', 0.5, 0.5),
    zone('foreground', 0.82, 0.66),
  ]);
  assert.equal(result.mode, 'expanded');
  assert.deepEqual(result.zones.map(({id}) => id), [
    'thirds-a',
    'thirds-b',
    'center',
    'foreground',
  ]);
});

test('video rejects unsafe wall-sized, cold, and reflection-only regions', () => {
  const result = selectVideoLightZones([
    zone('large', 1 / 3, 1 / 3, {width: 0.3, height: 0.2}),
    zone('broad-wall', 2 / 3, 1 / 3, {width: 0.2, height: 0.1}),
    zone('cold', 2 / 3, 1 / 3, {warmth: 0.1}),
    zone('low', 1 / 3, 2 / 3, {y: 0.82}),
    zone('center', 0.52, 0.48),
  ]);
  assert.equal(result.mode, 'expanded');
  assert.deepEqual(result.zones.map(({id}) => id), ['center']);
});

test('video contributes one strongest safe source from each depth layer', () => {
  const result = selectVideoLightZones([
    zone('background-weak', 0.1, 0.2, {strength: 0.7}),
    zone('background-strong', 0.9, 0.2),
    zone('midground', 0.1, 0.5),
    zone('foreground', 0.9, 0.65),
  ]);
  assert.equal(result.mode, 'expanded');
  assert.deepEqual(result.zones.map(({id}) => id), [
    'background-strong',
    'midground',
    'foreground',
    'background-weak',
  ]);
});

test('video expands beyond anchor points while capping the safe source pool', () => {
  const candidates = Array.from({length: 16}, (_, index) =>
    zone(`safe-${index}`, 0.05 + index * 0.055, 0.45),
  );
  const result = selectVideoLightZones(candidates);
  assert.equal(result.zones.length, 12);
  assert.equal(new Set(result.zones.map(({id}) => id)).size, 12);
});
