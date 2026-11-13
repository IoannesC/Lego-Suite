import t from "../../i18n/i18n";
import { FC } from "react";
import { usePerGameRgbProfilesEnabled } from "../../hooks/rgb";
import { ToggleField } from "@decky/ui";

export const RgbPerGameProfilesToggle: FC = () => {
  const [perGameProfilesEnabled, setPerGameProfilesEnabled] =
    usePerGameRgbProfilesEnabled();

  return (
    <ToggleField
      label={t("RGB_ENABLE_PER_GAME", "Enable Per Game Profiles")}
      checked={perGameProfilesEnabled}
      onChange={setPerGameProfilesEnabled}
    />
  );
};
