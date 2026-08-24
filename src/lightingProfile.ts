export const BRIGHT_SCENE_LUMA = 110;

export const isBrightLightingScene = (averageLuma: number) =>
  averageLuma >= BRIGHT_SCENE_LUMA;

export const adaptBrightnessForScene = (
  brightness: number,
  isBrightScene: boolean,
) => {
  if (!isBrightScene) return brightness;

  // Daylight makes a full night-style dim look like a black pasted-on disc.
  // Keep the same irregular timing but reduce the exposure swing.
  return brightness < 1
    ? 1 - (1 - brightness) * 0.18
    : 1 + (brightness - 1);
};
