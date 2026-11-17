import { FC } from "react";
import { PanelSection, PanelSectionRow, ButtonItem } from "@decky/ui";
import { useState, useEffect } from "react";
import { OptiScalerControls } from "./components";
import { InstalledGamesSection } from "./components/InstalledGamesSection";
import { checkFGModPath } from "./api";
import { safeAsyncOperation } from "./utils";
import { TIMEOUTS, DEFAULT_PROXY_DLL, DEFAULT_FSR4_VARIANT } from "./utils/constants";
import t from "../i18n/i18n";

type FgmodInfo = {
  exists: boolean;
  version?: string | null;
  selected_fsr4_variant?: string | null;
  selected_fsr4_variant_label?: string | null;
  install_manifest_present?: boolean;
};

export const OptiscalerInjectorTab: FC = () => {
  const [pathExists, setPathExists] = useState<boolean | null>(null);
  const [fgmodInfo, setFgmodInfo] = useState<FgmodInfo | null>(null);
  const [dllName, setDllName] = useState<string>(DEFAULT_PROXY_DLL);
  const [fsr4Variant, setFsr4Variant] = useState<string>(DEFAULT_FSR4_VARIANT);
  const [showOptions, setShowOptions] = useState(false);

  useEffect(() => {
    const checkPath = async () => {
      const result = await safeAsyncOperation(
        async () => await checkFGModPath(),
        'OptiscalerInjectorTab -> checkPath'
      );
      if (result) {
        setFgmodInfo((prev) => {
          if (prev && JSON.stringify(prev) === JSON.stringify(result)) return prev;
          return result;
        });
        setPathExists((prev) => (prev === result.exists ? prev : result.exists));
      }
    };
    
    checkPath(); // Initial check
    const intervalId = setInterval(checkPath, TIMEOUTS.pathCheck); // Check every 3 seconds
    return () => clearInterval(intervalId); // Cleanup interval on component unmount
  }, []);

  return (
    <>
      {pathExists === true ? (
        <>
          <InstalledGamesSection dllName={dllName} fsr4Variant={fsr4Variant} />
          <PanelSection>
            <PanelSectionRow>
              <ButtonItem
                layout="below"
                onClick={() => setShowOptions((prev) => !prev)}
              >
                {showOptions ? t("OPTISCALER_OPTIONS_OPEN", "Options ▾") : t("OPTISCALER_OPTIONS_CLOSED", "Options ▸")}
              </ButtonItem>
            </PanelSectionRow>
          </PanelSection>
          {showOptions ? (
            <OptiScalerControls
              pathExists={pathExists}
              setPathExists={setPathExists}
              fgmodInfo={fgmodInfo}
              dllName={dllName}
              setDllName={setDllName}
              fsr4Variant={fsr4Variant}
              setFsr4Variant={setFsr4Variant}
            />
          ) : null}
        </>
      ) : (
        <OptiScalerControls
          pathExists={pathExists}
          setPathExists={setPathExists}
          fgmodInfo={fgmodInfo}
          dllName={dllName}
          setDllName={setDllName}
          fsr4Variant={fsr4Variant}
          setFsr4Variant={setFsr4Variant}
        />
      )}
    </>
  );
};

export default OptiscalerInjectorTab;
