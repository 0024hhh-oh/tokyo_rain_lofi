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
};

const THIRDS_RADIUS_X = 0.11;
const THIRDS_RADIUS_Y = 0.11;
const CENTER_RADIUS_X = 0.14;
const CENTER_RADIUS_Y = 0.14;
const MAX_LIGHTS = 3;
const SAFE_MIN_WARMTH = 0.4;
// Video inputs already contain wet-road motion. Keep automatic candidates
// above the lower street/reflection band; source-only masks remain the route
// for reviewed lights lower in the frame.
const SAFE_MAX_Y = 0.74;

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
  zone.width * zone.height <= 0.025;

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

export const selectVideoLightZones = (zones: VideoLightZone[]) => {
  const safe = zones.filter(isSafeEmitter);
  const thirdsCandidate = bestNear(
    safe,
    thirds,
    THIRDS_RADIUS_X,
    THIRDS_RADIUS_Y,
  );
  if (thirdsCandidate) {
    return {mode: 'thirds' as const, zones: [thirdsCandidate]};
  }
  const centerCandidate = bestNear(
    safe,
    [[0.5, 0.5]],
    CENTER_RADIUS_X,
    CENTER_RADIUS_Y,
  );
  if (centerCandidate) {
    return {mode: 'center' as const, zones: [centerCandidate]};
  }
  return {mode: 'fallback' as const, zones: safe.slice(0, MAX_LIGHTS)};
};
