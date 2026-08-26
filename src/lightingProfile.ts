export const BRIGHT_SCENE_LUMA = 110;

export const isBrightLightingScene = (averageLuma: number) =>
  averageLuma >= BRIGHT_SCENE_LUMA;

export const adaptBrightnessForScene = (
  brightness: number,
  _isBrightScene: boolean,
) => {
  // Negative exposure changes are forbidden: they create pasted-on dark discs.
  return Math.max(1, brightness);
};
