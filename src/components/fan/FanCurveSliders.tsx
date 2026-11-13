import t from "../../i18n/i18n";
import { useDispatch, useSelector } from "react-redux";
import { fanSlice, selectActiveFanCurve } from "../../redux-modules/fanSlice";
import {
  PanelSection,
  PanelSectionRow,
  SliderField,
  ToggleField,
} from "@decky/ui";
import { FC, useState } from "react";

const DISABLE_KEY = "legion-go-remapper-disable-fan-curve-limit";

const useDisableLimit = () => {
  const [disableLimits, setDisableLimits] = useState(
    window.localStorage.getItem(DISABLE_KEY) === "true" || false,
  );

  const setLimit = (enable: boolean) => {
    setDisableLimits(enable);
    window.localStorage.setItem(DISABLE_KEY, `${enable}`);
  };

  return { disableLimits, setLimit };
};

const FanCurveSliders: FC = () => {
  const activeFanCurve = useSelector(selectActiveFanCurve);

  const { disableLimits, setLimit } = useDisableLimit();

  const dispatch = useDispatch();

  const sliders = Object.entries(activeFanCurve).map(
    ([temp, fanSpeed], idx) => {
      const updateFanCurveValue = (temp: string, fanSpeed: number) => {
        if (!disableLimits && idx >= 6 && fanSpeed < 70) {
          fanSpeed = 70;
        }
        return dispatch(fanSlice.actions.updateFanCurve({ temp, fanSpeed }));
      };
      return (
        <PanelSectionRow key={idx}>
          <SliderField
            label={`${temp} \u2103`}
            value={fanSpeed}
            showValue
            valueSuffix="%"
            step={5}
            min={5}
            max={115}
            validValues="range"
            bottomSeparator="none"
            onChange={(newSpeed) => {
              return updateFanCurveValue(temp, newSpeed);
            }}
          />
        </PanelSectionRow>
      );
    },
  );

  return (
    <PanelSection title={t("FAN_TEMP_SPEED", "Temp (\u2103) | Fan Speed (%)")}>
      <PanelSectionRow>
        <ToggleField
          label={t("FAN_DISABLE_LIMITS", "Disable Fan Curve Limits")}
          checked={disableLimits}
          onChange={setLimit}
        />
      </PanelSectionRow>
      {sliders}
    </PanelSection>
  );
};

export default FanCurveSliders;
