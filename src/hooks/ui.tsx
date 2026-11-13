import { useDispatch, useSelector } from "react-redux";
import {
  selectChargeLimitEnabled,
  selectChargeLimitValue,
  selectScreenBrightness,
  selectScreenContrast,
  uiSlice,
} from "../redux-modules/uiSlice";

export const useChargeLimitEnabled = () => {
  const chargeLimitEnabled = useSelector(selectChargeLimitEnabled);
  const chargeLimitValue = useSelector(selectChargeLimitValue);
  const dispatch = useDispatch();

  const setChargeLimit = (enabled: boolean) => {
    return dispatch(uiSlice.actions.setChargeLimit(enabled));
  };

  const setChargeLimitValue = (value: number) => {
    return dispatch(uiSlice.actions.setChargeLimitValue(value));
  };

  return {
    chargeLimitEnabled,
    setChargeLimit,
    chargeLimitValue,
    setChargeLimitValue,
  };
};

export const useScreenDisplayControls = () => {
  const screenBrightness = useSelector(selectScreenBrightness);
  const screenContrast = useSelector(selectScreenContrast);
  const dispatch = useDispatch();

  const setScreenBrightness = (value: number) => {
    return dispatch(uiSlice.actions.setScreenBrightness(value));
  };

  const setScreenContrast = (value: number) => {
    return dispatch(uiSlice.actions.setScreenContrast(value));
  };

  return {
    screenBrightness,
    setScreenBrightness,
    screenContrast,
    setScreenContrast,
  };
};
