import { useState } from "react";
import {
  resetSettings,
  checkRyzenadjCoall,
  clearGameProfiles,
  clearAcProfiles,
  clearEgpuProfiles,
} from "../../backend/utils";
import { useSelector } from "react-redux";
import {
  getSystemLangSelector,
} from "../../redux-modules/settingsSlice";
import { selectScalingDriver } from "../../redux-modules/uiSlice";
import {
  DeckyButton,
  DeckyField,
  DeckyRow,
  DeckySection,
} from "../atoms/DeckyFrontendLib";
import useDeviceName from "../../hooks/useDeviceName";
import useIsIntel from "../../hooks/useIsIntel";
import t from "../../i18n/i18n";
import ArrowToggleButton from "../atoms/ArrowToggleButton";

const OtaUpdates = () => {
  const [resetSettingsInProgress, setResetSettingsInProgress] = useState(false);
  const [clearGameInProgress, setClearGameInProgress] = useState(false);
  const [clearAcInProgress, setClearAcInProgress] = useState(false);
  const [clearEgpuInProgress, setClearEgpuInProgress] = useState(false);
  const [gameClearedMsg, setGameClearedMsg] = useState(false);
  const [acClearedMsg, setAcClearedMsg] = useState(false);
  const [egpuClearedMsg, setEgpuClearedMsg] = useState(false);
  const [checkAmdUndervolt, setCheckAmdUndervolt] = useState(false);

  const systemLang = useSelector(getSystemLangSelector);
  const scalingDriver = useSelector(selectScalingDriver);
  const deviceName = useDeviceName();
  const isIntel = useIsIntel();

  return (
    <DeckySection title={t("SYSTEM_INFO_TITLE", "System Info")}>
      <ArrowToggleButton cacheKey="SystemInfoSectionCacheKey">
        <DeckyRow>
          <DeckyField
            label={t("SYSTEM_INFO_INSTALLED_VERSION", "Version")}
            bottomSeparator="none"
          >
            0.198
          </DeckyField>
        </DeckyRow>
        <DeckyRow>
          <DeckyField
            label={t("SYSTEM_INFO_SYSTEM_LANGUAGE", "System Language")}
            bottomSeparator="none"
          >
            {systemLang || "en"}
          </DeckyField>
        </DeckyRow>
        {Boolean(scalingDriver) && (
          <DeckyRow>
            <DeckyField
              label={t("SYSTEM_INFO_SCALING_DRIVER", "Scaling Driver")}
              bottomSeparator="none"
            >
              {scalingDriver}
            </DeckyField>
          </DeckyRow>
        )}
        {Boolean(deviceName) && (
          <DeckyRow>
            <DeckyField
              label={t("SYSTEM_INFO_DEVICE_NAME", "Device Name")}
              bottomSeparator="none"
            >
              {deviceName}
            </DeckyField>
          </DeckyRow>
        )}
        <DeckyRow>
          <DeckyField
            label={t("SYSTEM_INFO_RESET_SETTINGS", "Reset Plugin Settings")}
            bottomSeparator="none"
          >
            {t(
              "SYSTEM_INFO_RESET_WARNING",
              "WARNING! This permanently deletes your current settings. This will also restart the Steam client, no Steam data will be affected.",
            )}
          </DeckyField>
        </DeckyRow>
        <DeckyRow>
          <DeckyButton
            onClick={async () => {
              setResetSettingsInProgress(true);
              await resetSettings();
              setResetSettingsInProgress(false);
            }}
            style={{
              width: "100%",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
            layout={"below"}
          >
            {resetSettingsInProgress
              ? t("SYSTEM_INFO_RESETTING", "Resetting...")
              : t("SYSTEM_INFO_DELETE_SETTINGS", "Delete settings")}
          </DeckyButton>
        </DeckyRow>
        <DeckyRow>
          <DeckyButton
            onClick={async () => {
              setClearGameInProgress(true);
              try {
                await clearGameProfiles();
              } catch (e) {
                console.error("clearGameProfiles error", e);
              }
              setClearGameInProgress(false);
              setGameClearedMsg(true);
              setTimeout(() => setGameClearedMsg(false), 2500);
            }}
            style={{
              width: "100%",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
            layout={"below"}
          >
            {clearGameInProgress
              ? (systemLang === "es" ? "Borrando perfiles..." : "Clearing profiles...")
              : gameClearedMsg
              ? (systemLang === "es" ? "✓ Perfiles de juego borrados" : "✓ Game profiles deleted")
              : (systemLang === "es" ? "Borrar perfiles de juego" : "Delete game profiles")}
          </DeckyButton>
        </DeckyRow>
        <DeckyRow>
          <DeckyButton
            onClick={async () => {
              setClearAcInProgress(true);
              try {
                await clearAcProfiles();
              } catch (e) {
                console.error("clearAcProfiles error", e);
              }
              setClearAcInProgress(false);
              setAcClearedMsg(true);
              setTimeout(() => setAcClearedMsg(false), 2500);
            }}
            style={{
              width: "100%",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
            layout={"below"}
          >
            {clearAcInProgress
              ? (systemLang === "es" ? "Borrando perfiles..." : "Clearing profiles...")
              : acClearedMsg
              ? (systemLang === "es" ? "✓ Perfiles AC borrados" : "✓ AC profiles deleted")
              : (systemLang === "es" ? "Borrar perfiles AC" : "Delete AC profiles")}
          </DeckyButton>
        </DeckyRow>
        <DeckyRow>
          <DeckyButton
            onClick={async () => {
              setClearEgpuInProgress(true);
              try {
                await clearEgpuProfiles();
              } catch (e) {
                console.error("clearEgpuProfiles error", e);
              }
              setClearEgpuInProgress(false);
              setEgpuClearedMsg(true);
              setTimeout(() => setEgpuClearedMsg(false), 2500);
            }}
            style={{
              width: "100%",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
            layout={"below"}
          >
            {clearEgpuInProgress
              ? (systemLang === "es" ? "Borrando perfiles..." : "Clearing profiles...")
              : egpuClearedMsg
              ? (systemLang === "es" ? "✓ Perfiles eGPU borrados" : "✓ eGPU profiles deleted")
              : (systemLang === "es" ? "Borrar perfiles eGPU" : "Delete eGPU profiles")}
          </DeckyButton>
        </DeckyRow>
        {!isIntel && (
          <>
            <DeckyRow>
              <DeckyField
                label={t(
                  "SYSTEM_INFO_DETECT_AMD_UNDERVOLT",
                  "Detect AMD undervolt",
                )}
                bottomSeparator="none"
              >
                {t(
                  "SYSTEM_INFO_DETECT_AMD_UNDERVOLT_DESC",
                  "Check if your device supports ryzenadj-based CPU undervolting. If it does, you should see a toggle appear in the advanced options. This will reboot Steam.",
                )}
              </DeckyField>
            </DeckyRow>
            <DeckyRow>
              <DeckyButton
                onClick={async () => {
                  setCheckAmdUndervolt(true);
                  await checkRyzenadjCoall();
                  setCheckAmdUndervolt(false);
                }}
                style={{
                  width: "100%",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                }}
                layout={"below"}
              >
                {checkAmdUndervolt
                  ? t("SYSTEM_INFO_UPDATING", "Checking...")
                  : t("SYSTEM_INFO_CHECK_AMD_UNDERVOLT", "Check AMD undervolt")}
              </DeckyButton>
            </DeckyRow>
          </>
        )}
      </ArrowToggleButton>
    </DeckySection>
  );
};

export default OtaUpdates;
