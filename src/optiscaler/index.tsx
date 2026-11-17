import { definePlugin } from "@decky/api";
import { PanelSection, PanelSectionRow, ButtonItem } from "@decky/ui";
import { MdOutlineAutoAwesomeMotion } from "react-icons/md";
import { useState, useEffect } from "react";
import { OptiScalerControls } from "./components";
import { InstalledGamesSection } from "./components/InstalledGamesSection";
import { checkFGModPath } from "./api";
import { safeAsyncOperation } from "./utils";
import { TIMEOUTS, DEFAULT_PROXY_DLL, DEFAULT_FSR4_VARIANT } from "./utils/constants";

type FgmodInfo = {
  exists: boolean;
  version?: string | null;
  selected_fsr4_variant?: string | null;
  selected_fsr4_variant_label?: string | null;
  install_manifest_present?: boolean;
};

function MainContent() {
  const [pathExists, setPathExists] = useState<boolean | null>(null);
  const [fgmodInfo, setFgmodInfo] = useState<FgmodInfo | null>(null);
  const [dllName, setDllName] = useState<string>(DEFAULT_PROXY_DLL);
  const [fsr4Variant, setFsr4Variant] = useState<string>(DEFAULT_FSR4_VARIANT);
  const [showOptions, setShowOptions] = useState(false);

  useEffect(() => {
    const checkPath = async () => {
      const result = await safeAsyncOperation(
        async () => await checkFGModPath(),
        'MainContent -> checkPath'
      );
      if (result) {
        setFgmodInfo(result);
        setPathExists(result.exists);
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
                {showOptions ? "Options ▾" : "Options ▸"}
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
}

export default definePlugin(() => ({
  name: "LeGO Suite",
  titleView: <div>LeGO Suite</div>,
  alwaysRender: true,
  content: <MainContent />,
  icon: <MdOutlineAutoAwesomeMotion />,
  onDismount() {
    console.log("LeGO Suite Plugin unmounted");
  },
}));
