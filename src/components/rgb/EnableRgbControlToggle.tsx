import t from "../../i18n/i18n";
import { FC } from "react";
import { useEnableRgbControl } from "../../hooks/rgb";
import { ToggleField } from "@decky/ui";

export const EnableRgbControlToggle: FC = () => {
  const { rgbControlEnabled, setRgbControlEnabled } = useEnableRgbControl();

  return (
    <ToggleField
      label={t("RGB_ENABLE_CONTROL", "Enable RGB Control")}
      checked={rgbControlEnabled}
      onChange={setRgbControlEnabled}
    />
  );
};
