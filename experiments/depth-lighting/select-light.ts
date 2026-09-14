import type {Depth} from './timing';

export type LightCandidate = {
  id: string;
  kind: 'vending_machine' | 'phone_booth' | 'sign' | 'shop_light' | 'streetlamp' | 'station_light' | 'convenience_store_light' | 'window' | 'neon' | 'artificial_light';
  depth: Depth;
  sourceMask: string;
  // Bounds of the actual emitter, in source-image pixels; never include reflections.
  sourceRoi: [number, number, number, number];
  prominence: number; // Image-specific human review: 0..1.
  clipRisk: number; // Image-specific human review: 0..1; 1 is blown out.
  isEmitter: true;
};

export type LightSelectionProfile = {
  source: {width: number; height: number};
  localLightCandidates?: LightCandidate[];
  localLightSearch?: {thirdsRadiusX?: number; thirdsRadiusY?: number; centerRadiusX?: number; centerRadiusY?: number};
};

const defaults = {thirdsRadiusX: 0.08, thirdsRadiusY: 0.08, centerRadiusX: 0.12, centerRadiusY: 0.12};
const allowed = new Set(['vending_machine', 'phone_booth', 'sign', 'shop_light', 'streetlamp', 'station_light', 'convenience_store_light', 'window', 'neon', 'artificial_light']);

export function validateLightSource(candidate: LightCandidate, width: number, height: number): boolean {
  if (!candidate || !allowed.has(candidate.kind) || candidate.isEmitter !== true ||
      !['back', 'middle', 'front'].includes(candidate.depth) ||
      typeof candidate.sourceMask !== 'string' || !candidate.sourceMask.trim() ||
      !Array.isArray(candidate.sourceRoi) || candidate.sourceRoi.length !== 4 ||
      !candidate.sourceRoi.every(Number.isFinite) || !Number.isFinite(candidate.prominence) ||
      candidate.prominence < 0 || candidate.prominence > 1 || !Number.isFinite(candidate.clipRisk) ||
      candidate.clipRisk < 0 || candidate.clipRisk > 0.2 || width <= 0 || height <= 0) return false;
  const [x1, y1, x2, y2] = candidate.sourceRoi;
  return x1 >= 0 && y1 >= 0 && x2 <= width && y2 <= height && x2 > x1 && y2 > y1 &&
    ((x2 - x1) * (y2 - y1)) / (width * height) <= 0.035;
}

function near(candidate: LightCandidate, width: number, height: number, targets: readonly (readonly [number, number])[], radiusX: number, radiusY: number) {
  const [x1, y1, x2, y2] = candidate.sourceRoi;
  const cx = (x1 + x2) / (2 * width);
  const cy = (y1 + y2) / (2 * height);
  let distance = Infinity;
  for (const [x, y] of targets) {
    const dx = Math.abs(cx - x), dy = Math.abs(cy - y);
    if (dx <= radiusX && dy <= radiusY) distance = Math.min(distance, Math.hypot(dx, dy));
  }
  return distance;
}

export function getRuleOfThirdsCandidates(profile: LightSelectionProfile) {
  const {width, height} = profile.source;
  const x = profile.localLightSearch?.thirdsRadiusX ?? defaults.thirdsRadiusX;
  const y = profile.localLightSearch?.thirdsRadiusY ?? defaults.thirdsRadiusY;
  const points: [number, number][] = [[1/3, 1/3], [2/3, 1/3], [1/3, 2/3], [2/3, 2/3]];
  return (profile.localLightCandidates ?? []).filter(c => validateLightSource(c, width, height))
    .map(candidate => ({candidate, distance: near(candidate, width, height, points, x, y)}))
    .filter(result => Number.isFinite(result.distance));
}

export function getCenterCandidate(profile: LightSelectionProfile) {
  const {width, height} = profile.source;
  const x = profile.localLightSearch?.centerRadiusX ?? defaults.centerRadiusX;
  const y = profile.localLightSearch?.centerRadiusY ?? defaults.centerRadiusY;
  return (profile.localLightCandidates ?? []).filter(c => validateLightSource(c, width, height))
    .map(candidate => ({candidate, distance: near(candidate, width, height, [[0.5, 0.5]], x, y)}))
    .filter(result => Number.isFinite(result.distance));
}

export function selectBestLightCandidate(results: ReturnType<typeof getRuleOfThirdsCandidates>): LightCandidate | null {
  // Nearest anchor wins; visual prominence resolves near-equal positions.
  return [...results].sort((a, b) => a.distance - b.distance ||
    b.candidate.prominence - a.candidate.prominence ||
    a.candidate.clipRisk - b.candidate.clipRisk ||
    a.candidate.id.localeCompare(b.candidate.id))[0]?.candidate ?? null;
}

export function selectLightingMode(profile: LightSelectionProfile):
  {mode: 'local'; candidate: LightCandidate; region: 'thirds' | 'center'} | {mode: 'three-layer'} {
  const thirds = selectBestLightCandidate(getRuleOfThirdsCandidates(profile));
  if (thirds) return {mode: 'local', candidate: thirds, region: 'thirds'};
  const center = selectBestLightCandidate(getCenterCandidate(profile));
  if (center) return {mode: 'local', candidate: center, region: 'center'};
  return {mode: 'three-layer'};
}
