import { call } from "@decky/api";
import { logInfo, readAls, setGamescopeBrightnessPct } from './utils';






const BRIGHTNESS_THRESHOLDS = [
  [0, 28],
  [1, 38],
  [2, 45],
  [4, 52],
  [7, 60],
  [12, 68],
  [20, 75],
  [35, 82],
  [60, 90],
  [100, 96],
  [150, 100]
];

let steamRegistration: any;
let enableAdaptiveBrightness = false;
let isLegionGo2Device = false;

export const sensitivityInfo = {
  range: [25, 100],
  step: 25
};

export const pollInfo = {
  range: [100, 500],
  step: 50
};

export const smoothTimeInfo = {
  range: [100, 1000],
  step: 50
};

export const brightnessOffsetInfo = {
  range: [-30, 30],
  step: 5
};

export const DEFAULT_POLLING_RATE = 100;
export const DEFAULT_SMOOTH_TIME = 500;
export const DEFAULT_SENSITIVITY = 50;
export const DEFAULT_BRIGHTNESS_OFFSET = 0;

let pollingRate = DEFAULT_POLLING_RATE; 
let smoothTime = DEFAULT_SMOOTH_TIME; 
const stepCount = 10; 
let brightnessOffset = DEFAULT_BRIGHTNESS_OFFSET;

let previousAlsValues = Array(DEFAULT_SENSITIVITY).fill(-1);
let currentBrightness = 50;

const handleAls = async () => {
  const sleep = (ms: number) =>
    new Promise((resolve) => setTimeout(resolve, ms));

  while (enableAdaptiveBrightness) {
    await sleep(pollingRate);

    const alsValue = await readAls();
    if (typeof alsValue !== 'number' || isNaN(alsValue)) {
      continue;
    }

    
    previousAlsValues.push(alsValue);
    previousAlsValues.shift();

    
    if (previousAlsValues.includes(-1)) {
      continue;
    }

    
    const averageAlsValue =
      previousAlsValues.reduce((acc, val) => acc + val, 0) /
      previousAlsValues.length;

    
    let targetBrightness = currentBrightness;
    for (let i = 0; i < BRIGHTNESS_THRESHOLDS.length; i++) {
      if (averageAlsValue <= BRIGHTNESS_THRESHOLDS[i][0]) {
        targetBrightness = BRIGHTNESS_THRESHOLDS[i][1];
        break;
      }

      if (i === BRIGHTNESS_THRESHOLDS.length - 1) {
        targetBrightness = BRIGHTNESS_THRESHOLDS[i][1];
      }
    }

    
    targetBrightness = Math.min(100, Math.max(20, targetBrightness + brightnessOffset));

    if (Math.abs(targetBrightness - currentBrightness) < 2) {
      continue;
    }

    let localCurrentBrightness = currentBrightness;
    const numSteps = smoothTime / stepCount;

    let brightnessPerStep = (targetBrightness - currentBrightness) / numSteps;

    for (let i = 0; i < numSteps; i++) {
      await sleep(numSteps);

      localCurrentBrightness = localCurrentBrightness + brightnessPerStep;

      localCurrentBrightness = Math.min(
        100,
        Math.max(0, localCurrentBrightness)
      );

      logInfo(
        `Setting brightness to ${localCurrentBrightness}, target: ${targetBrightness}, brightnessPerStep: ${brightnessPerStep}`
      );

      try {
        await call("set_screen_brightness", Math.round(localCurrentBrightness));
      } catch {}
      if (isLegionGo2Device) {
        await setGamescopeBrightnessPct(localCurrentBrightness);
      } else if ((window as any).SteamClient?.System?.Display?.SetBrightness) {
        (window as any).SteamClient?.System?.Display?.SetBrightness(
          localCurrentBrightness / 100
        );
      }
    }

    currentBrightness = targetBrightness;
    previousAlsValues.fill(-1);
  }
};

export const enableAlsListener = () => {
  enableAdaptiveBrightness = true;
  new Promise(async () => {
    await handleAls();
  });

  if (!steamRegistration)
    steamRegistration =
      (window as any).SteamClient?.System?.Display?.RegisterForBrightnessChanges(
        async (data: { flBrightness: number }) => {
          currentBrightness = data.flBrightness * 100;
        }
      );
};

export const setPollRate = (newRate: number) => {
  pollingRate = newRate;
};

export const setSmoothTime = (newTime: number) => {
  smoothTime = newTime;
};

export const clearAlsListener = () => {
  enableAdaptiveBrightness = false;

  previousAlsValues.fill(-1);
};

export const setSensitivity = (arrSize: number) => {
  previousAlsValues = Array(arrSize).fill(-1);
};

export const setBrightnessOffset = (offset: number) => {
  const delta = offset - brightnessOffset;
  brightnessOffset = offset;
  if (!enableAdaptiveBrightness || delta === 0) return;

  const newTarget = Math.min(100, Math.max(0, currentBrightness + delta));
  if (newTarget === currentBrightness) return;

  currentBrightness = newTarget;

  try {
    call("set_screen_brightness", Math.round(newTarget));
  } catch {}
  if (isLegionGo2Device) {
    setGamescopeBrightnessPct(newTarget);
  } else if ((window as any).SteamClient?.System?.Display?.SetBrightness) {
    (window as any).SteamClient?.System?.Display?.SetBrightness(newTarget / 100);
  }
};

export const setIsLegionGo2 = (val: boolean) => {
  isLegionGo2Device = val;
};
