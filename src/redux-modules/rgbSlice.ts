import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import { debounce, get, merge } from "lodash";
import type { RootState } from "./store";
import { setCurrentGameId, setInitialState } from "./extraActions";
import {
  extractCurrentGameId,
  saveRgbPerGameProfilesEnabled,
  saveRgbSettingsBackend,
  setPowerLed,
  syncRgbSettings,
} from "../backend/utils";
import { ControllerType, RgbModes } from "../backend/constants";
import { Router } from "@decky/ui";

const DEFAULT_RGB_LIGHT_VALUES: RgbLight = {
  enabled: false,
  mode: RgbModes.SOLID,
  speed: 50,
  red: 255,
  green: 255,
  blue: 255,
  brightness: 50,
  hue: 50,
};

enum Colors {
  RED = "red",
  GREEN = "green",
  BLUE = "blue",
}

type RgbLight = {
  enabled: boolean;
  mode: RgbModes;
  speed: number;
  red: number;
  green: number;
  blue: number;
  brightness: number;
  hue: number;
};

type RgbProfile = { LEFT: RgbLight; RIGHT: RgbLight };

type RgbProfiles = {
  [gameId: string]: RgbProfile;
};

type RgbState = {
  rgbProfiles: RgbProfiles;
  perGameProfilesEnabled: boolean;
  enableRgbControl: boolean;
  forceEnableSeparateLedManagement: boolean;
  powerLedEnabled: boolean;
};

const initialState: RgbState = {
  rgbProfiles: {
    default: {
      LEFT: { ...DEFAULT_RGB_LIGHT_VALUES },
      RIGHT: { ...DEFAULT_RGB_LIGHT_VALUES },
    },
  },
  perGameProfilesEnabled: false,
  enableRgbControl: false,
  forceEnableSeparateLedManagement: false,
  powerLedEnabled: true,
};

const bootstrapRgbProfile = (state: RgbState, newGameId: string) => {
  if (!state.rgbProfiles) {
    state.rgbProfiles = {};
  }
  if (
    (!state.rgbProfiles[newGameId] && state.perGameProfilesEnabled) ||
    newGameId === "default"
  ) {
    if (!state.rgbProfiles[newGameId]) {
      const defaultProfile = get(state, "rgbProfiles.default", {}) as RgbProfile;
      const newRgbProfile = {
        LEFT: defaultProfile.LEFT
          ? { ...DEFAULT_RGB_LIGHT_VALUES, ...defaultProfile.LEFT }
          : { ...DEFAULT_RGB_LIGHT_VALUES },
        RIGHT: defaultProfile.RIGHT
          ? { ...DEFAULT_RGB_LIGHT_VALUES, ...defaultProfile.RIGHT }
          : { ...DEFAULT_RGB_LIGHT_VALUES },
      };

      state.rgbProfiles[newGameId] = newRgbProfile;
    }
  }
};

export const rgbSlice = createSlice({
  name: "rgb",
  initialState,
  reducers: {
    setEnableRgbControl: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;
      state.enableRgbControl = enabled;
      if (enabled) {
        bootstrapRgbProfile(state, extractCurrentGameId());
      }
    },
    setPerGameProfilesEnabled: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;
      state.perGameProfilesEnabled = enabled;
      if (enabled) {
        bootstrapRgbProfile(state, extractCurrentGameId());
      }
    },
    setRgbMode: (
      state,
      action: PayloadAction<{ controller: ControllerType; mode: RgbModes }>,
    ) => {
      const { controller, mode } = action.payload;
      setStateValue({
        sliceState: state,
        controller,
        key: "mode",
        value: mode,
      });
    },
    setSpeed: (
      state,
      action: PayloadAction<{ controller: ControllerType; speed: number }>,
    ) => {
      const { controller, speed } = action.payload;
      setStateValue({
        sliceState: state,
        controller,
        key: "speed",
        value: speed,
      });
    },
    updateRgbProfiles: (state, action: PayloadAction<RgbProfiles>) => {
      merge(state.rgbProfiles, action.payload);
    },
    setColor: (
      state,
      action: PayloadAction<{
        controller: ControllerType;
        color: Colors;
        value: number;
      }>,
    ) => {
      const { controller, color, value } = action.payload;
      setStateValue({
        sliceState: state,
        controller,
        key: color,
        value,
      });
    },
    setRgbColor: (
      state,
      action: PayloadAction<{
        controller: ControllerType;
        red: number;
        green: number;
        blue: number;
        hue: number;
      }>,
    ) => {
      const { controller, red, green, blue, hue } = action.payload;
      const currentGameId = state.perGameProfilesEnabled
        ? extractCurrentGameId()
        : "default";
      bootstrapRgbProfile(state, currentGameId);
      state.rgbProfiles[currentGameId][controller].red = red;
      state.rgbProfiles[currentGameId][controller].green = green;
      state.rgbProfiles[currentGameId][controller].blue = blue;
      state.rgbProfiles[currentGameId][controller].hue = hue;
    },
    setEnabled: (
      state,
      action: PayloadAction<{
        controller: ControllerType;
        enabled: boolean;
      }>,
    ) => {
      const { controller, enabled } = action.payload;

      setStateValue({
        sliceState: state,
        controller,
        key: "enabled",
        value: enabled,
      });
    },
    setBrightness: (
      state,
      action: PayloadAction<{
        controller: ControllerType;
        brightness: number;
      }>,
    ) => {
      const { controller, brightness } = action.payload;

      setStateValue({
        sliceState: state,
        controller,
        key: "brightness",
        value: brightness,
      });
    },
    setHue: (
      state,
      action: PayloadAction<{
        controller: ControllerType;
        hue: number;
      }>,
    ) => {
      const { controller, hue } = action.payload;
      setStateValue({
        sliceState: state,
        controller,
        key: "hue",
        value: hue,
      });
    },
    setPowerLedEnabled: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;
      state.powerLedEnabled = enabled;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(setInitialState, (state, action) => {
      const rgbProfiles = (action.payload?.rgb || {}) as RgbProfiles;
      const perGameProfilesEnabled = Boolean(
        action.payload?.rgbPerGameProfilesEnabled,
      );
      const powerLedEnabled = action.payload?.powerLedEnabled;
      const enableRgbControl = Boolean(action.payload?.enableRgbControl);

      if (typeof powerLedEnabled === "boolean") {
        state.powerLedEnabled = powerLedEnabled;
      }

      merge(state.rgbProfiles, rgbProfiles);
      bootstrapRgbProfile(state, "default");
      state.enableRgbControl = enableRgbControl;
      state.perGameProfilesEnabled = perGameProfilesEnabled;
      state.forceEnableSeparateLedManagement = Boolean(
        action.payload?.forceEnableSeparateLedManagement,
      );
    });
    builder.addCase(setCurrentGameId, (state, action) => {
      const newGameId = action.payload as string;
      bootstrapRgbProfile(state, newGameId);
    });
  },
});

// -------------
// selectors
// -------------

export const selectRgbInfo =
  (controller: ControllerType) => (state: RootState) => {
    const currentGameId = extractCurrentGameId();
    if (state.rgb.perGameProfilesEnabled) {
      return (
        state.rgb.rgbProfiles[currentGameId]?.[controller] ||
        state.rgb.rgbProfiles["default"]?.[controller] ||
        DEFAULT_RGB_LIGHT_VALUES
      );
    } else {
      return (
        state.rgb.rgbProfiles["default"]?.[controller] ||
        DEFAULT_RGB_LIGHT_VALUES
      );
    }
  };

export const selectRgbMode =
  (controller: ControllerType) => (state: RootState) => {
    const info = selectRgbInfo(controller)(state);
    return info?.mode || RgbModes.SOLID;
  };

export const selectPerGameProfilesEnabled = (state: RootState) => {
  return state.rgb.perGameProfilesEnabled;
};

export const selectRgbProfileDisplayName = (state: RootState) => {
  if (state.rgb.perGameProfilesEnabled) {
    return Router.MainRunningApp?.display_name || "Default";
  } else {
    return "Default";
  }
};

export const selectEnableRgbControl = (state: RootState) => {
  return Boolean(state.rgb.enableRgbControl);
};

export const selectPowerLedEnabled = (state: RootState) => {
  return Boolean(state.rgb.powerLedEnabled);
};

export const selectSeparateRgbManagementEnabled = (state: RootState) => {
  return Boolean(state.rgb.forceEnableSeparateLedManagement);
};

// -------------
// middleware
// -------------

const mutatingActionTypes = [
  rgbSlice.actions.updateRgbProfiles.type,
  rgbSlice.actions.setColor.type,
  rgbSlice.actions.setEnabled.type,
  rgbSlice.actions.setPerGameProfilesEnabled.type,
  rgbSlice.actions.setRgbMode.type,
  rgbSlice.actions.setRgbColor.type,
  rgbSlice.actions.setSpeed.type,
  rgbSlice.actions.setBrightness.type,
  rgbSlice.actions.setHue.type,
  rgbSlice.actions.setEnableRgbControl.type,
  setCurrentGameId.type,
];

const saveRgbSettings = (store: any) => {
  const {
    rgb: { rgbProfiles, perGameProfilesEnabled, enableRgbControl },
  } = store.getState();
  const currentGameId = perGameProfilesEnabled
    ? extractCurrentGameId()
    : "default";

  let syncCt = false;
  try {
    syncCt = window.localStorage.getItem("LEGO_SYNC_COLORED_TOGGLES") === "true";
  } catch (e) {}

  const payload = {
    rgbProfiles,
    currentGameId,
    enableRgbControl,
    syncColoredToggles: syncCt,
  };

  saveRgbSettingsBackend(payload);
};

const debouncedSaveRgbSettings = debounce(saveRgbSettings, 300);

export const saveRgbSettingsMiddleware =
  (store: any) => (next: any) => (action: any) => {
    const { type } = action;
    const result = next(action);

    if (type === rgbSlice.actions.setPowerLedEnabled.type) {
      setPowerLed(action.payload);
    }

    if (mutatingActionTypes.includes(type)) {
      debouncedSaveRgbSettings(store);
    }
    if (type === setInitialState.type || type === setCurrentGameId.type) {
      const {
        rgb: { perGameProfilesEnabled, enableRgbControl },
      } = store.getState();
      if (enableRgbControl) {
        const currentGameId = perGameProfilesEnabled
          ? extractCurrentGameId()
          : "default";
        syncRgbSettings(currentGameId);
      }
    }
    if (type === rgbSlice.actions.setPerGameProfilesEnabled.type) {
      saveRgbPerGameProfilesEnabled(Boolean(action.payload));
      if (action.payload) {
        syncRgbSettings(extractCurrentGameId());
      } else {
        syncRgbSettings("default");
      }
    }

    return result;
  };

function setStateValue({
  sliceState,
  controller,
  key,
  value,
}: {
  sliceState: RgbState;
  controller: ControllerType;
  key: string;
  value: any;
}) {
  const targetId = sliceState.perGameProfilesEnabled
    ? extractCurrentGameId()
    : "default";
  bootstrapRgbProfile(sliceState, targetId);
  (sliceState.rgbProfiles[targetId][controller] as any)[key] = value;
}
