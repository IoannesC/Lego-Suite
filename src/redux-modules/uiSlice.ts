import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { RootState } from "./store";
import { fetchPowerControlInfo } from "./thunks";
import { PowerControlInfo } from "../utils/constants";
import { setCurrentGameId, setInitialState } from "./extraActions";
import {
  extractDisplayName,
  saveSettings,
  setAlsEnabled,
  setChargeLimit,
  setScreenBrightnessBackend,
  setScreenContrastBackend,
} from "../backend/utils";
import {
  DEFAULT_BRIGHTNESS_OFFSET,
  DEFAULT_POLLING_RATE,
  DEFAULT_SENSITIVITY,
  DEFAULT_SMOOTH_TIME,
  clearAlsListener,
  enableAlsListener,
  setBrightnessOffset,
  setIsLegionGo2,
  setPollRate,
  setSensitivity,
  setSmoothTime,
} from "../backend/alsListener";

type UiStateType = {
  powerControlInfo?: PowerControlInfo;
  isDesktop: boolean;
  initialLoading: boolean;
  currentGameId: undefined | string;
  currentDisplayName: undefined | string;
  chargeLimitEnabled?: boolean;
  chargeLimitValue: number;
  screenBrightness: number;
  screenContrast: number;
  alsEnabled?: boolean;
  pluginVersionNum?: string;
  alsInfo: {
    pollingRate: number;
    smoothTime: number;
    sensitivity: number;
    brightnessOffset: number;
  };
};

const initialState: UiStateType = {
  powerControlInfo: undefined,
  isDesktop: false,
  initialLoading: true,
  currentGameId: undefined,
  currentDisplayName: undefined,
  chargeLimitValue: 80,
  screenBrightness: 80,
  screenContrast: 100,
  pluginVersionNum: "",
  alsInfo: {
    pollingRate: DEFAULT_POLLING_RATE,
    smoothTime: DEFAULT_SMOOTH_TIME,
    sensitivity: DEFAULT_SENSITIVITY,
    brightnessOffset: DEFAULT_BRIGHTNESS_OFFSET,
  },
};

export const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    setInitialLoading: (state, action: PayloadAction<boolean>) => {
      state.initialLoading = action.payload;
    },
    setChargeLimit(state, action: PayloadAction<boolean>) {
      state.chargeLimitEnabled = action.payload;
    },
    setChargeLimitValue(state, action: PayloadAction<number>) {
      state.chargeLimitValue = action.payload;
    },
    setScreenBrightness(state, action: PayloadAction<number>) {
      state.screenBrightness = action.payload;
    },
    setScreenContrast(state, action: PayloadAction<number>) {
      state.screenContrast = action.payload;
    },
    setAlsEnabled(state, action: PayloadAction<boolean>) {
      state.alsEnabled = action.payload;
    },
    setPollingRate(state, action: PayloadAction<number>) {
      setPollRate(action.payload);
      state.alsInfo.pollingRate = action.payload;
    },
    setSmoothTime(state, action: PayloadAction<number>) {
      setSmoothTime(action.payload);
      state.alsInfo.smoothTime = action.payload;
    },
    setSensitivity(state, action: PayloadAction<number>) {
      setSensitivity(action.payload);
      state.alsInfo.sensitivity = action.payload;
    },
    setBrightnessOffset(state, action: PayloadAction<number>) {
      setBrightnessOffset(action.payload);
      state.alsInfo.brightnessOffset = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(fetchPowerControlInfo.fulfilled, (state, action) => {
      if (action.payload) {
        state.powerControlInfo = action.payload as PowerControlInfo;
      }
    });
    builder.addCase(setInitialState, (state, action) => {
      if (action) state.initialLoading = false;
      if (action.payload?.pluginVersionNum) {
        state.pluginVersionNum = `${action.payload.pluginVersionNum}`;
      }
      if (action.payload?.isLegionGo2) {
        setIsLegionGo2(true);
      }
      if (action.payload?.chargeLimitEnabled) {
        state.chargeLimitEnabled = Boolean(action.payload?.chargeLimitEnabled);
      }
      if (action.payload?.chargeLimitValue) {
        state.chargeLimitValue = Number(action.payload.chargeLimitValue);
      }
      if (action.payload?.screenBrightness !== undefined) {
        state.screenBrightness = Number(action.payload.screenBrightness);
      }
      if (action.payload?.screenContrast !== undefined) {
        state.screenContrast = Number(action.payload.screenContrast);
      }
      if (action.payload?.alsEnabled) {
        state.alsEnabled = Boolean(action.payload?.alsEnabled);
      }
      if (action.payload?.alsInfo) {
        const {
          pollingRate,
          smoothTime,
          sensitivity,
          brightnessOffset: savedOffset,
        } = action.payload.alsInfo || {};
        state.alsInfo = { ...state.alsInfo, ...action.payload.alsInfo };
        setPollRate(pollingRate || DEFAULT_POLLING_RATE);
        setSmoothTime(smoothTime || DEFAULT_SMOOTH_TIME);
        setSensitivity(sensitivity || DEFAULT_SENSITIVITY);
        setBrightnessOffset(savedOffset ?? DEFAULT_BRIGHTNESS_OFFSET);
      }
    });
    builder.addCase(setCurrentGameId, (state, action) => {
      if (action?.payload) {
        state.currentGameId = action.payload;
        state.currentDisplayName = extractDisplayName();
      }
    });
  },
});

export const selectPowerControlInfo = (state: RootState) => {
  return state.ui.powerControlInfo;
};

export const selectScalingDriver = (state: RootState) => {
  return state.ui.powerControlInfo?.scalingDriver || "";
};

export const selectIsDesktop = (state: RootState) => {
  return state.ui.isDesktop;
};

export const getPluginVersionNumSelector = (state: RootState) =>
  state.ui.pluginVersionNum;

export const getInitialLoading = (state: RootState) => state.ui.initialLoading;

export const selectCurrentGameId = (state: RootState) =>
  state.ui?.currentGameId || "default";

export const selectCurrentGameDisplayName = (state: RootState) =>
  state.ui?.currentDisplayName || "default";

export const selectChargeLimitEnabled = (state: RootState) =>
  Boolean(state.ui?.chargeLimitEnabled);

export const selectChargeLimitValue = (state: RootState) =>
  state.ui?.chargeLimitValue || 80;

export const selectScreenBrightness = (state: RootState) =>
  state.ui?.screenBrightness ?? 80;

export const selectScreenContrast = (state: RootState) =>
  state.ui?.screenContrast ?? 100;

export const selectAlsEnabled = (state: RootState) =>
  Boolean(state.ui?.alsEnabled);

export const selectAlsPollingRate = (state: RootState) =>
  state.ui.alsInfo.pollingRate;
export const selectSmoothTime = (state: RootState) =>
  state.ui.alsInfo.smoothTime;
export const selectSensitivity = (state: RootState) =>
  state.ui.alsInfo.sensitivity;
export const selectBrightnessOffset = (state: RootState) =>
  state.ui.alsInfo.brightnessOffset;

export const uiSliceMiddleware =
  (_store: any) => (next: any) => (action: any) => {
    const { type } = action;
    const result = next(action);

    if (type === setInitialState.type) {
      if (action.payload?.alsEnabled) {
        enableAlsListener();
      }
    }

    if (type === uiSlice.actions.setPollingRate.type) {
      const alsInfo = { pollingRate: action.payload };
      saveSettings({ alsInfo });
    }
    if (type === uiSlice.actions.setSmoothTime.type) {
      const alsInfo = { smoothTime: action.payload };
      saveSettings({ alsInfo });
    }
    if (type === uiSlice.actions.setSensitivity.type) {
      const alsInfo = { sensitivity: action.payload };
      saveSettings({ alsInfo });
    }
    if (type === uiSlice.actions.setBrightnessOffset.type) {
      const alsInfo = { brightnessOffset: action.payload };
      saveSettings({ alsInfo });
    }

    if (type === uiSlice.actions.setChargeLimit.type) {
      const state = _store.getState();
      setChargeLimit(action.payload, state.ui?.chargeLimitValue || 80);
    }
    if (type === uiSlice.actions.setChargeLimitValue.type) {
      const state = _store.getState();
      setChargeLimit(
        Boolean(state.ui?.chargeLimitEnabled),
        Number(action.payload),
      );
    }
    if (type === uiSlice.actions.setScreenBrightness.type) {
      setScreenBrightnessBackend(Number(action.payload));
    }
    if (type === uiSlice.actions.setScreenContrast.type) {
      setScreenContrastBackend(Number(action.payload));
    }
    if (type === uiSlice.actions.setAlsEnabled.type) {
      const enabled = action.payload;
      setAlsEnabled(enabled);
      if (enabled) {
        enableAlsListener();
      } else {
        clearAlsListener();
      }
    }

    return result;
  };
