import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import { get, set, merge } from "lodash";
import type { RootState } from "./store";
import { setCurrentGameId, setInitialState } from "./extraActions";
import { extractCurrentGameId, saveControllerSettings } from "../backend/utils";
import {
  Gyro,
  GyroRemapActions,
  RemapActions,
  RemappableButtons,
  RumbleIntensity,
} from "../backend/constants";
import { Router } from "@decky/ui";

const DEFAULT_CONTROLLER_VALUES: ControllerProfile = {
  Y1: RemapActions.DISABLED,
  Y2: RemapActions.DISABLED,
  Y3: RemapActions.DISABLED,
  M2: RemapActions.DISABLED,
  M3: RemapActions.DISABLED,
  TOUCHPAD: true,
  LEFT_GYRO: GyroRemapActions.DISABLED,
  RIGHT_GYRO: GyroRemapActions.DISABLED,
  RUMBLE: RumbleIntensity.MEDIUM,
};

type ControllerProfile = {
  Y1: RemapActions;
  Y2: RemapActions;
  Y3: RemapActions;
  M2: RemapActions;
  M3: RemapActions;
  TOUCHPAD: boolean;
  LEFT_GYRO: GyroRemapActions;
  RIGHT_GYRO: GyroRemapActions;
  RUMBLE: RumbleIntensity;
};

type ControllerProfiles = {
  [gameId: string]: ControllerProfile;
};

type ControllerState = {
  controllerProfiles: ControllerProfiles;
  perGameProfilesEnabled: boolean;
  controllerRemappingEnabled: boolean;
};

const initialState: ControllerState = {
  controllerProfiles: {},
  perGameProfilesEnabled: false,
  controllerRemappingEnabled: true,
};

export const controllerSlice = createSlice({
  name: "controller",
  initialState,
  reducers: {
    setPerGameProfilesEnabled: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;
      state.perGameProfilesEnabled = enabled;
      if (enabled) {
        bootstrapControllerProfile(state, extractCurrentGameId());
      }
    },
    setControllerRemappingEnabled: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;
      state.controllerRemappingEnabled = enabled;
    },
    remapButton: (
      state,
      action: PayloadAction<{
        button: RemappableButtons;
        remapAction: RemapActions;
      }>,
    ) => {
      const { button, remapAction } = action.payload;
      setStateValue({
        sliceState: state,
        key: button,
        value: remapAction,
      });
    },
    updateControllerProfiles: (
      state,
      action: PayloadAction<ControllerProfiles>,
    ) => {
      merge(state.controllerProfiles, action.payload);
    },
    setTouchpad: (state, action: PayloadAction<boolean>) => {
      const touchpadEnabled = action.payload;
      setStateValue({
        sliceState: state,
        key: "TOUCHPAD",
        value: touchpadEnabled,
      });
    },
    setRumbleIntensity: (state, action: PayloadAction<RumbleIntensity>) => {
      const rumble = action.payload;
      setStateValue({
        sliceState: state,
        key: "RUMBLE",
        value: rumble,
      });
    },
    setGyro: (
      state,
      action: PayloadAction<{ gyro: Gyro; remapAction: GyroRemapActions }>,
    ) => {
      const { gyro, remapAction } = action.payload;
      setStateValue({
        sliceState: state,
        key: gyro,
        value: remapAction,
      });
    },
  },
  extraReducers: (builder) => {
    builder.addCase(setInitialState, (state, action) => {
      const controllerProfiles = (action.payload?.controller ||
        {}) as ControllerProfiles;

      const perGameProfilesEnabled = Boolean(
        action.payload?.controllerPerGameProfilesEnabled,
      );
      const controllerRemappingEnabled =
        action.payload?.controllerRemappingEnabled !== undefined
          ? Boolean(action.payload.controllerRemappingEnabled)
          : false;

      state.controllerRemappingEnabled = controllerRemappingEnabled;
      state.controllerProfiles = controllerProfiles;
      state.perGameProfilesEnabled = perGameProfilesEnabled;
      bootstrapControllerProfile(state, "default");
    });
    builder.addCase(setCurrentGameId, (state, action) => {
      const newGameId = action.payload as string;
      bootstrapControllerProfile(state, newGameId);
    });
  },
});

// -------------
// selectors
// -------------

export const selectControllerPerGameProfilesEnabled = (state: RootState) => {
  return state.controller.perGameProfilesEnabled;
};

export const selectControllerRemappingEnabled = (state: RootState) => {
  return state.controller.controllerRemappingEnabled;
};

export const selectTouchpadEnabled = (state: RootState) => {
  if (state.controller.perGameProfilesEnabled) {
    return get(
      state,
      `controller.controllerProfiles.${extractCurrentGameId()}.TOUCHPAD`,
      true,
    );
  } else {
    return get(state, `controller.controllerProfiles.default.TOUCHPAD`, true);
  }
};

export const selectRumbleIntensity = (state: RootState) => {
  if (state.controller.perGameProfilesEnabled) {
    return get(
      state,
      `controller.controllerProfiles.${extractCurrentGameId()}.RUMBLE`,
      RumbleIntensity.MEDIUM,
    );
  } else {
    return get(
      state,
      `controller.controllerProfiles.default.RUMBLE`,
      RumbleIntensity.MEDIUM,
    );
  }
};

export const selectButtonRemapAction =
  (button: RemappableButtons) => (state: RootState) => {
    if (state.controller.perGameProfilesEnabled) {
      return get(
        state,
        `controller.controllerProfiles.${extractCurrentGameId()}.${button}`,
        RemapActions.DISABLED,
      );
    } else {
      return get(
        state,
        `controller.controllerProfiles.default.${button}`,
        RemapActions.DISABLED,
      );
    }
  };

export const selectGyroRemapAction = (gyro: Gyro) => (state: RootState) => {
  if (state.controller.perGameProfilesEnabled) {
    return get(
      state,
      `controller.controllerProfiles.${extractCurrentGameId()}.${gyro}`,
      GyroRemapActions.DISABLED,
    );
  } else {
    return get(
      state,
      `controller.controllerProfiles.default.${gyro}`,
      GyroRemapActions.DISABLED,
    );
  }
};

export const selectControllerProfileDisplayName = (state: RootState) => {
  if (state.controller.perGameProfilesEnabled) {
    return Router.MainRunningApp?.display_name || "Default";
  } else {
    return "Default";
  }
};

// -------------
// middleware
// -------------

const mutatingActionTypes = [
  controllerSlice.actions.setPerGameProfilesEnabled.type,
  controllerSlice.actions.remapButton.type,
  controllerSlice.actions.updateControllerProfiles.type,
  controllerSlice.actions.setTouchpad.type,
  controllerSlice.actions.setRumbleIntensity.type,
  controllerSlice.actions.setGyro.type,
  controllerSlice.actions.setControllerRemappingEnabled.type,
  setCurrentGameId.type,
];

export const saveControllerSettingsMiddleware =
  (store: any) => (next: any) => (action: any) => {
    const { type } = action;
    const result = next(action);

    if (mutatingActionTypes.includes(type)) {
      const {
        controller: {
          controllerProfiles,
          perGameProfilesEnabled,
          controllerRemappingEnabled,
        },
        ui: { currentGameId: currentId },
      } = store.getState();
      let currentGameId;
      if (perGameProfilesEnabled && currentId) {
        currentGameId = currentId;
      } else {
        currentGameId = "default";
      }

      const controller = {
        controllerProfiles,
        perGameProfilesEnabled,
        controllerRemappingEnabled,
      };

      saveControllerSettings(controller, currentGameId);
    }

    return result;
  };

function setStateValue({
  sliceState,
  key,
  value,
}: {
  sliceState: ControllerState;
  key: string;
  value: any;
}) {
  if (sliceState.perGameProfilesEnabled) {
    const currentGameId = extractCurrentGameId();
    bootstrapControllerProfile(sliceState, currentGameId);
    set(sliceState, `controllerProfiles.${currentGameId}.${key}`, value);
  } else {
    bootstrapControllerProfile(sliceState, "default");
    set(sliceState, `controllerProfiles.default.${key}`, value);
  }
}

function bootstrapControllerProfile(state: ControllerState, newGameId: string) {
  if (!state.controllerProfiles) {
    state.controllerProfiles = {};
  }
  if (
    (!state.controllerProfiles[newGameId] && state.perGameProfilesEnabled) ||
    newGameId === "default"
  ) {
    if (!state.controllerProfiles[newGameId]) {
      const defaultProfile = state.controllerProfiles?.default;
      const newControllerProfile = defaultProfile
        ? { ...DEFAULT_CONTROLLER_VALUES, ...defaultProfile }
        : { ...DEFAULT_CONTROLLER_VALUES };

      state.controllerProfiles[newGameId] = newControllerProfile;
    }
  }
}
