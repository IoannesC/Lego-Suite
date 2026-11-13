import { configureStore } from "@reduxjs/toolkit";
import settingsReducer from "./settingsSlice";
import { settingsMiddleware } from "./settingsMiddleware";
import { commonMiddleware } from "./commonMiddleware";
import { uiSlice, uiSliceMiddleware } from "./uiSlice";
import { rgbSlice, saveRgbSettingsMiddleware } from "./rgbSlice";
import {
  controllerSlice,
  saveControllerSettingsMiddleware,
} from "./controllerSlice";
import { fanSlice, saveFanSettingsMiddleware } from "./fanSlice";

export const store = configureStore({
  reducer: {
    ui: uiSlice.reducer,
    settings: settingsReducer,
    rgb: rgbSlice.reducer,
    fan: fanSlice.reducer,
    controller: controllerSlice.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat([
      settingsMiddleware,
      commonMiddleware,
      uiSliceMiddleware,
      saveRgbSettingsMiddleware,
      saveControllerSettingsMiddleware,
      saveFanSettingsMiddleware,
    ]),
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
