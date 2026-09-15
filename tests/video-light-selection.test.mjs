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

test('video selects exactly one safe emitter near a thirds intersection', () => {
  const result = selectVideoLightZones([
    zone('thirds', 1 / 3 + 0.03, 1 / 3),
    zone('center', 0.5, 0.5),
    zone('other', 0.8, 0.5),
  ]);
  assert.equal(result.mode, 'thirds');
  assert.deepEqual(result.zones.map(({id}) => id), ['thirds']);
});

test('video uses center after thirds and rejects unsafe reflection-like regions', () => {
  const result = selectVideoLightZones([
    zone('large', 1 / 3, 1 / 3, {width: 0.3, height: 0.2}),
    zone('cold', 2 / 3, 1 / 3, {warmth: 0.1}),
    zone('low', 1 / 3, 2 / 3, {y: 0.82}),
    zone('center', 0.52, 0.48),
  ]);
  assert.equal(result.mode, 'center');
  assert.deepEqual(result.zones.map(({id}) => id), ['center']);
});

test('video retains up to three existing safe zones as fallback', () => {
  const result = selectVideoLightZones([
    zone('a', 0.1, 0.2),
    zone('b', 0.9, 0.2),
    zone('c', 0.1, 0.5),
    zone('d', 0.9, 0.5),
  ]);
  assert.equal(result.mode, 'fallback');
  assert.deepEqual(result.zones.map(({id}) => id), ['a', 'b', 'c']);
});
