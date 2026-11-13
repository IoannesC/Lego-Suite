import t from "../../i18n/i18n";
import { FC } from "react";
import { Gyro, RemappableButtons, RumbleIntensity } from "../../backend/constants";
import RemapActionDropdown from "./RemapActionDropdown";
import {
  DropdownItem,
  Field,
  PanelSection,
  PanelSectionRow,
  ToggleField,
} from "@decky/ui";
import {
  useControllerPerGameEnabled,
  useControllerProfileDisplayName,
  useControllerRemappingEnabled,
  useTouchpadEnabled,
  useRumbleIntensity,
} from "../../hooks/controller";
import { IconRow } from "../IconRow";
import GyroRemapSlider from "./GyroRemapSlider";

const RUMBLE_I18N_KEYS: Record<string, string> = {
  OFF: "RUMBLE_INTENSITY_OFF",
  LOW: "RUMBLE_INTENSITY_LOW",
  MEDIUM: "RUMBLE_INTENSITY_MEDIUM",
  HIGH: "RUMBLE_INTENSITY_HIGH",
};

const RemapButtons: FC = () => {
  const btns = Object.values(RemappableButtons);
  const gyros = Object.values(Gyro);
  const displayName = useControllerProfileDisplayName();
  const { controllerPerGameEnabled, setControllerPerGameEnabled } =
    useControllerPerGameEnabled();
  const { controllerRemappingEnabled, setControllerRemappingEnabled } =
    useControllerRemappingEnabled();

  const { touchpadEnabled, setTouchpad } = useTouchpadEnabled();
  const { rumbleIntensity, setRumbleIntensity } = useRumbleIntensity();

  const rumbleOptions = Object.values(RumbleIntensity).map((intensity) => {
    const key = RUMBLE_I18N_KEYS[intensity];
    const fallback = intensity.charAt(0).toUpperCase() + intensity.slice(1).toLowerCase();
    const label = key ? t(key, fallback) : fallback;
    return {
      data: intensity,
      label,
    };
  });

  const title = controllerPerGameEnabled ? `${t("REMAP_BUTTONS_TITLE", "Remap Buttons")} -
${displayName.substring(0, 20)}${displayName.length > 20 ? "..." : ""}` : t("REMAP_BUTTONS_TITLE", "Remap Buttons");

  return (
    <>
      <PanelSection title={title}>
        <PanelSectionRow>
          <DropdownItem
            label={t("RUMBLE_INTENSITY", "Vibration Intensity")}
            rgOptions={rumbleOptions.map((o) => ({
              data: o.data,
              label: o.label,
            }))}
            selectedOption={
              rumbleOptions.find((o) => o.data === (rumbleIntensity || RumbleIntensity.MEDIUM))?.data || RumbleIntensity.MEDIUM
            }
            onChange={(option: any) => setRumbleIntensity(option.data as RumbleIntensity)}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <ToggleField
            label={t("REMAP_ENABLE", "Enable controller remaps")}
            checked={controllerRemappingEnabled}
            onChange={setControllerRemappingEnabled}
          />
        </PanelSectionRow>
        {controllerRemappingEnabled && (
          <>
            <PanelSectionRow>
              <Field disabled>
                {t("REMAP_WARNING", "⚠️ WARNING ⚠️ - Don't use these remapping features with Controller Emulators. If you are using Handheld Daemon (hhd), use the Dualsense Edge controller + remap back buttons with Steam Input")}
              </Field>
            </PanelSectionRow>
            <PanelSectionRow>
              <ToggleField
                label={t("REMAP_ENABLE_PER_GAME", "Enable Per Game Remaps")}
                checked={controllerPerGameEnabled}
                onChange={setControllerPerGameEnabled}
              />
            </PanelSectionRow>
            <ToggleField
              label={t("REMAP_TOUCHPAD", "Touchpad")}
              checked={touchpadEnabled}
              onChange={(value) => setTouchpad(value)}
            ></ToggleField>
            {btns.map((btn, idx) => {
              return (
                <IconRow btn={btn} key={idx}>
                  <RemapActionDropdown btn={btn} />
                </IconRow>
              );
            })}
            {gyros.map((gyro, idx) => {
              return <GyroRemapSlider gyro={gyro} key={idx} />;
            })}
          </>
        )}
      </PanelSection>
    </>
  );
};

export default RemapButtons;
