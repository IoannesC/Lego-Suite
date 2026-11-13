import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import { set, merge, cloneDeep } from "lodash";
import { setCurrentGameId, setInitialState } from "./extraActions";
import {
  disableFanProfiles,
  extractCurrentGameId,
  saveFanSettings,
} from "../backend/utils";
import { RootState } from "./store";

const DEFAULT_FAN_VALUES: FanProfile = {
  10: 5,
  20: 5,
  30: 5,
  40: 10,
  50: 15,
  60: 35,
  70: 70,
  80: 80,
  90: 95,
  100: 100,
  fullFanSpeedEnabled: false,
};

type FanSpeed = number;

type FanCurve = {
  10: FanSpeed;
  20: FanSpeed;
  30: FanSpeed;
  40: FanSpeed;
  50: FanSpeed;
  60: FanSpeed;
  70: FanSpeed;
  80: FanSpeed;
  90: FanSpeed;
  100: FanSpeed;
};

interface FanProfile extends FanCurve {
  fullFanSpeedEnabled: boolean;
}

type FanProfiles = {
  [gameId: string]: FanProfile;
};

type FanState = {
  fanProfiles: FanProfiles;
  fanPerGameProfilesEnabled: boolean;
  customFanCurvesEnabled: boolean;
  supportsCustomFanCurves: boolean;
};

const initialState: FanState = {
  fanProfiles: {
    default: { ...DEFAULT_FAN_VALUES },
  },
  fanPerGameProfilesEnabled: false,
  customFanCurvesEnabled: false,
  supportsCustomFanCurves: false,
};

export const fanSlice = createSlice({
  name: "fan",
  initialState,
  reducers: {
    setCustomFanCurvesEnabled: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;
      state.customFanCurvesEnabled = enabled;
      if (enabled) {
        bootstrapFanProfile(state, extractCurrentGameId());
      }
    },
    setFanPerGameProfilesEnabled: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;
      state.fanPerGameProfilesEnabled = enabled;
      if (enabled) {
        bootstrapFanProfile(state, extractCurrentGameId());
      }
    },
    setEnableFullFanSpeedMode: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;
      const perGameProfilesEnabled = state.fanPerGameProfilesEnabled;
      const targetId = perGameProfilesEnabled
        ? extractCurrentGameId()
        : "default";
      bootstrapFanProfile(state, targetId);
      state.fanProfiles[targetId].fullFanSpeedEnabled = enabled;
    },
    updateFanCurve: (
      state,
      action: PayloadAction<{
        temp: string;
        fanSpeed: number;
      }>,
    ) => {
      const { temp, fanSpeed } = action.payload;
      setStateValue({
        sliceState: state,
        key: temp,
        value: fanSpeed,
      });
    },
    updateFanProfiles: (state, action: PayloadAction<FanProfiles>) => {
      merge(state.fanProfiles, action.payload);
    },
  },
  extraReducers: (builder) => {
    builder.addCase(setInitialState, (state, action) => {
      const fanProfiles = (action.payload?.fan || {}) as FanProfiles;

      const customFanCurvesEnabled = Boolean(
        action.payload?.customFanCurvesEnabled,
      );
      const fanPerGameProfilesEnabled = Boolean(
        action.payload?.fanPerGameProfilesEnabled,
      );

      state.supportsCustomFanCurves = Boolean(
        action.payload?.supportsCustomFanCurves,
      );

      state.customFanCurvesEnabled = customFanCurvesEnabled;
      merge(state.fanProfiles, fanProfiles);
      bootstrapFanProfile(state, "default");
      state.fanPerGameProfilesEnabled = fanPerGameProfilesEnabled;
    });
    builder.addCase(setCurrentGameId, (state, action) => {
      const newGameId = action.payload as string;
      bootstrapFanProfile(state, newGameId);
    });
  },
});

export const selectSupportsCustomFanCurves = (state: RootState) => {
  return Boolean(state.fan.supportsCustomFanCurves);
};

export const selectCustomFanCurvesEnabled = (state: RootState) => {
  return Boolean(state.fan.customFanCurvesEnabled);
};

export const selectFanPerGameProfilesEnabled = (state: RootState) => {
  return Boolean(state.fan.fanPerGameProfilesEnabled);
};

export const selectActiveFanProfile = (state: RootState) => {
  const perGameProfilesEnabled = selectFanPerGameProfilesEnabled(state);

  if (perGameProfilesEnabled) {
    const {
      ui: { currentGameId = "default" },
    } = state;
    return (
      state.fan.fanProfiles[currentGameId] ||
      state.fan.fanProfiles.default ||
      DEFAULT_FAN_VALUES
    );
  } else {
    return state.fan.fanProfiles.default || DEFAULT_FAN_VALUES;
  }
};

export const selectActiveFanCurve = (state: RootState) => {
  const profile = selectActiveFanProfile(state);

  const p = cloneDeep(profile) as any;
  delete p.fullFanSpeedEnabled;
  const x = p as FanCurve;

  return x;
};

export const selectEnableFullFanSpeedMode = (state: RootState) => {
  const profile = selectActiveFanProfile(state);
  return Boolean(profile?.fullFanSpeedEnabled);
};

const mutatingActionTypes = [
  fanSlice.actions.setFanPerGameProfilesEnabled.type,
  fanSlice.actions.updateFanCurve.type,
  fanSlice.actions.updateFanProfiles.type,
  fanSlice.actions.setEnableFullFanSpeedMode.type,
];

export const saveFanSettingsMiddleware =
  (store: any) => (next: any) => (action: any) => {
    const { type } = action;
    const result = next(action);

    const state = store.getState();

    const {
      fan: { fanPerGameProfilesEnabled, customFanCurvesEnabled },
      ui: { currentGameId: currentId },
    } = state;

    let currentGameId;
    if (fanPerGameProfilesEnabled && currentId) {
      currentGameId = currentId;
    } else {
      currentGameId = "default";
    }

    if (type === setCurrentGameId.type && customFanCurvesEnabled) {
      setFanCurve(state, currentGameId);
    }

    if (type === fanSlice.actions.setCustomFanCurvesEnabled.type) {
      if (action.payload === false) {
        disableFanProfiles(true);
      } else {
        setFanCurve(state, currentGameId);
      }
    }

    if (mutatingActionTypes.includes(type)) {
      setFanCurve(state, currentGameId);
    }

    return result;
  };

function setFanCurve(state: any, currentGameId: string) {
  const {
    fan: { fanProfiles, fanPerGameProfilesEnabled, customFanCurvesEnabled },
  } = state;

  const fanInfo = {
    fanProfiles,
    fanPerGameProfilesEnabled,
    customFanCurvesEnabled,
  };

  saveFanSettings(fanInfo, currentGameId);
}

function setStateValue({
  sliceState,
  key,
  value,
}: {
  sliceState: FanState;
  key: string;
  value: any;
}) {
  const targetId = sliceState.fanPerGameProfilesEnabled
    ? extractCurrentGameId()
    : "default";
  bootstrapFanProfile(sliceState, targetId);
  set(sliceState, `fanProfiles.${targetId}.${key}`, value);
}

function bootstrapFanProfile(state: FanState, newGameId: string) {
  if (!state.fanProfiles) {
    state.fanProfiles = {};
  }
  if (
    (!state.fanProfiles[newGameId] && state.fanPerGameProfilesEnabled) ||
    newGameId === "default"
  ) {
    if (!state.fanProfiles[newGameId]) {
      const defaultProfile = state.fanProfiles?.default;
      const newFanProfile = defaultProfile
        ? { ...DEFAULT_FAN_VALUES, ...defaultProfile }
        : { ...DEFAULT_FAN_VALUES };

      state.fanProfiles[newGameId] = newFanProfile;
    }
  }
}
