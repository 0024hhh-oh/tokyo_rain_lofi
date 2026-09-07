export const FPS = 30;
export const FRAMES = 900;
export const layers = ['back', 'middle', 'front'] as const;
export type Depth = typeof layers[number];
export const windows: Record<Depth, readonly (readonly [number, number])[]> = {
  back: [[60, 180], [555, 645]],
  middle: [[225, 345], [675, 750]],
  front: [[390, 510], [780, 870]],
};
const smooth = (n: number) => { const x = Math.min(1, Math.max(0, n)); return x*x*(3-2*x); };
export function intensity(frame: number, depth: Depth): number {
  const f = ((frame % FRAMES) + FRAMES) % FRAMES;
  return Math.max(0, ...windows[depth].map(([start, end]) =>
    smooth((f-start)/24) * smooth((end-f)/24)));
}
