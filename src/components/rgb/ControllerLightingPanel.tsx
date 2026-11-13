import t from "../../i18n/i18n";
import { PanelSection, ToggleField } from "@decky/ui";
import { FC } from "react";
import {
  useEnableRgbControl,
  usePowerLed,
  useRgbProfileDisplayName,
} from "../../hooks/rgb";
import { RgbPerGameProfilesToggle } from "./RgbPerGameProfilesToggle";
import { RgbSettings } from "./RgbSettings";
import { EnableRgbControlToggle } from "./EnableRgbControlToggle";

const ControllerLightingPanel: FC = () => {
  const displayName = useRgbProfileDisplayName();
  const { rgbControlEnabled } = useEnableRgbControl();
  const { powerLedEnabled, setPowerLed } = usePowerLed();

  let title =
    displayName === "Default" ? t("RGB_PANEL_TITLE", "Controller Lighting") : `${t("RGB_PANEL_TITLE", "Controller Lighting")} - ${displayName.substring(0, 10)}...`;

  return (
    <PanelSection title={title}>
      <ToggleField
        label={t("RGB_ENABLE_POWER_LED", "Enable Power LED")}
        checked={powerLedEnabled}
        onChange={setPowerLed}
      />
      <EnableRgbControlToggle />
      {rgbControlEnabled && (
        <>
          <RgbPerGameProfilesToggle />
          <RgbSettings controller="RIGHT" />
        </>
      )}
    </PanelSection>
  );
};

export default ControllerLightingPanel;
