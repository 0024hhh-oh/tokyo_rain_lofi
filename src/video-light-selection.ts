export type VideoLightZone = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  warmth: number;
  strength: number;
  hasLightCore: boolean;
  color: [number, number, number];
  maskCells?: [number, number][];
};

const THIRDS_RADIUS_X = 0.11;
const THIRDS_RADIUS_Y = 0.11;
const CENTER_RADIUS_X = 0.14;
const CENTER_RADIUS_Y = 0.14;
const SAFE_MIN_WARMTH = 0.4;
const SAFE_MAX_AREA = 0.018;
const MAX_CANDIDATES = 12;
// Video inputs already contain wet-road motion. Keep automatic candidates
// above the lower street/reflection band; source-only masks remain the route
// for reviewed lights lower in the frame.
const SAFE_MAX_Y = 0.74;

const depthLayers = [
  {name: 'background', minY: 0.06, maxY: 0.4},
  {name: 'midground', minY: 0.4, maxY: 0.58},
  {name: 'foreground', minY: 0.58, maxY: SAFE_MAX_Y},
] as const;

const thirds = [
  [1 / 3, 1 / 3],
  [2 / 3, 1 / 3],
  [1 / 3, 2 / 3],
  [2 / 3, 2 / 3],
] as const;

const isSafeEmitter = (zone: VideoLightZone) =>
  zone.hasLightCore &&
  zone.warmth >= SAFE_MIN_WARMTH &&
  zone.y < SAFE_MAX_Y &&
  zone.width * zone.height <= SAFE_MAX_AREA;

const distanceWithin = (
  zone: VideoLightZone,
  targets: readonly (readonly [number, number])[],
  radiusX: number,
  radiusY: number,
) => {
  let best = Number.POSITIVE_INFINITY;
  for (const [x, y] of targets) {
    const dx = Math.abs(zone.x - x);
    const dy = Math.abs(zone.y - y);
    if (dx <= radiusX && dy <= radiusY) {
      best = Math.min(best, Math.hypot(dx / radiusX, dy / radiusY));
    }
  }
  return best;
};

const bestNear = (
  zones: VideoLightZone[],
  targets: readonly (readonly [number, number])[],
  radiusX: number,
  radiusY: number,
) =>
  zones
    .map((zone) => ({
      zone,
      distance: distanceWithin(zone, targets, radiusX, radiusY),
    }))
    .filter(({distance}) => Number.isFinite(distance))
    .sort(
      (a, b) =>
        a.distance - b.distance ||
        b.zone.strength - a.zone.strength ||
        a.zone.width * a.zone.height - b.zone.width * b.zone.height ||
        a.zone.id.localeCompare(b.zone.id),
    )[0]?.zone;

const bestInLayer = (
  zones: VideoLightZone[],
  minY: number,
  maxY: number,
) =>
  zones
    .filter((zone) => zone.y >= minY && zone.y < maxY)
    .sort(
      (a, b) =>
        b.strength - a.strength ||
        b.warmth - a.warmth ||
        a.width * a.height - b.width * b.height ||
        a.id.localeCompare(b.id),
    )[0];

const uniqueZones = (zones: Array<VideoLightZone | undefined>) => {
  const seen = new Set<string>();
  return zones.filter((zone): zone is VideoLightZone => {
    if (!zone || seen.has(zone.id)) return false;
    seen.add(zone.id);
    return true;
  });
};

export const selectVideoLightZones = (zones: VideoLightZone[]) => {
  const safe = zones.filter(isSafeEmitter);
  const thirdsCandidates = thirds.map((target) =>
    bestNear(safe, [target], THIRDS_RADIUS_X, THIRDS_RADIUS_Y),
  );
  const centerCandidate = bestNear(
    safe,
    [[0.5, 0.5]],
    CENTER_RADIUS_X,
    CENTER_RADIUS_Y,
  );
  const layerCandidates = depthLayers.map(({minY, maxY}) =>
    bestInLayer(safe, minY, maxY),
  );
  const remainingSafeCandidates = [...safe].sort(
    (a, b) =>
      b.strength - a.strength ||
      b.warmth - a.warmth ||
      a.width * a.height - b.width * b.height ||
      a.id.localeCompare(b.id),
  );
  const selected = uniqueZones([
    ...thirdsCandidates,
    centerCandidate,
    ...layerCandidates,
    ...remainingSafeCandidates,
  ]).slice(0, MAX_CANDIDATES);

  return {
    mode: selected.length > 0 ? 'expanded' as const : 'none' as const,
    zones: selected,
  };
};
