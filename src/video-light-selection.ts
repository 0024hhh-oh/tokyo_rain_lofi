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
  isReflection?: boolean;
};

export const LIGHT_SELECTION_CONFIG = {
  thirdsRadiusX: 0.09,
  thirdsRadiusY: 0.09,
  centerRadiusX: 0.14,
  centerRadiusY: 0.14,
} as const;

const SAFE_MIN_WARMTH = 0.4;
const SAFE_MAX_AREA = 0.018;
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

export const validateLightSource = (zone: VideoLightZone) =>
  !zone.isReflection &&
  zone.hasLightCore &&
  zone.warmth >= SAFE_MIN_WARMTH &&
  zone.y < SAFE_MAX_Y &&
  zone.width * zone.height <= SAFE_MAX_AREA;

const normalizedDistance = (
  zone: VideoLightZone,
  target: readonly [number, number],
  radiusX: number,
  radiusY: number,
) => {
  const dx = Math.abs(zone.x - target[0]);
  const dy = Math.abs(zone.y - target[1]);
  if (dx > radiusX || dy > radiusY) return Number.POSITIVE_INFINITY;
  return Math.hypot(dx / radiusX, dy / radiusY);
};

const distanceToTargets = (
  zone: VideoLightZone,
  targets: readonly (readonly [number, number])[],
  radiusX: number,
  radiusY: number,
) => Math.min(
  ...targets.map((target) => normalizedDistance(zone, target, radiusX, radiusY)),
);

export const getRuleOfThirdsCandidates = (
  zones: VideoLightZone[],
  radiusX = LIGHT_SELECTION_CONFIG.thirdsRadiusX,
  radiusY = LIGHT_SELECTION_CONFIG.thirdsRadiusY,
) =>
  zones
    .filter(validateLightSource)
    .filter((zone) =>
      Number.isFinite(distanceToTargets(zone, thirds, radiusX, radiusY)),
    );

export const getCenterCandidate = (
  zones: VideoLightZone[],
  radiusX = LIGHT_SELECTION_CONFIG.centerRadiusX,
  radiusY = LIGHT_SELECTION_CONFIG.centerRadiusY,
) => {
  const candidates = zones
    .filter(validateLightSource)
    .filter((zone) =>
      Number.isFinite(
        normalizedDistance(zone, [0.5, 0.5], radiusX, radiusY),
      ),
    );
  return selectBestLightCandidate(
    candidates,
    [[0.5, 0.5]],
    radiusX,
    radiusY,
  );
};

export const selectBestLightCandidate = (
  zones: VideoLightZone[],
  targets: readonly (readonly [number, number])[] = thirds,
  radiusX = LIGHT_SELECTION_CONFIG.thirdsRadiusX,
  radiusY = LIGHT_SELECTION_CONFIG.thirdsRadiusY,
) =>
  zones
    .filter(validateLightSource)
    .map((zone) => ({
      zone,
      distance: distanceToTargets(zone, targets, radiusX, radiusY),
    }))
    .filter(({distance}) => Number.isFinite(distance))
    .sort(
      (a, b) =>
        a.distance - b.distance ||
        b.zone.strength - a.zone.strength ||
        b.zone.warmth - a.zone.warmth ||
        a.zone.width * a.zone.height - b.zone.width * b.zone.height ||
        a.zone.id.localeCompare(b.zone.id),
    )[0]?.zone;

const bestInLayer = (
  zones: VideoLightZone[],
  minY: number,
  maxY: number,
) =>
  zones
    .filter(validateLightSource)
    .filter((zone) => zone.y >= minY && zone.y < maxY)
    .sort(
      (a, b) =>
        b.strength - a.strength ||
        b.warmth - a.warmth ||
        a.width * a.height - b.width * b.height ||
        a.id.localeCompare(b.id),
    )[0];

export const fallbackToExistingThreeLayerMode = (
  zones: VideoLightZone[],
) => {
  const layerCandidates = depthLayers
    .map(({minY, maxY}) => bestInLayer(zones, minY, maxY))
    .filter((zone): zone is VideoLightZone => Boolean(zone));

  return {
    mode: layerCandidates.length > 0 ? 'three-layer-fallback' as const : 'none' as const,
    zones: layerCandidates,
  };
};

export const selectVideoLightZones = (zones: VideoLightZone[]) => {
  const thirdsCandidates = getRuleOfThirdsCandidates(zones);
  const bestThirds = selectBestLightCandidate(thirdsCandidates);
  if (bestThirds) {
    return {
      mode: 'rule-of-thirds' as const,
      zones: [bestThirds],
    };
  }

  const centerCandidate = getCenterCandidate(zones);
  if (centerCandidate) {
    return {
      mode: 'center' as const,
      zones: [centerCandidate],
    };
  }

  return fallbackToExistingThreeLayerMode(zones);
};
