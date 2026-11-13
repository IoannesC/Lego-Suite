import { FC, memo, useState, useEffect } from "react";
import { DialogButton, Focusable } from "@decky/ui";
import TdpRange from "./components/molecules/TdpRange";
import { TdpSlider } from "./components/molecules/TdpSlider";
import { PollTdp } from "./components/molecules/PollTdp";
import { store } from "./redux-modules/store";
import { Provider, useSelector } from "react-redux";
import { TdpProfiles } from "./components/molecules/TdpProfiles";
import {
  useFetchInitialStateEffect,
  useIsInitiallyLoading,
} from "./hooks/useInitialState";
import Gpu from "./components/molecules/Gpu";
import AdvancedOptions from "./components/molecules/AdvancedOptions";
import OtaUpdates from "./components/molecules/OtaUpdates";
import ErrorBoundary from "./components/ErrorBoundary";
import PowerControl from "./components/molecules/PowerControl";
import {
  DeckySection,
  DeckyRow,
  DeckyToggle,
  DeckySlider,
  NotchLabel,
} from "./components/atoms/DeckyFrontendLib";
import { useIsDesktop } from "./hooks/desktopHooks";
import { AdvancedOptionsEnum } from "./backend/utils";
import { useAdvancedOption } from "./hooks/useAdvanced";
import { maxTdpAcProfilesEnabledSelector, getSystemLangSelector } from "./redux-modules/settingsSlice";
import { call } from "@decky/api";

// Controls & Hardware components
import RemapButtons from "./components/controller/RemapButtons";
import ControllerLightingPanel from "./components/rgb/ControllerLightingPanel";
import FanPanel from "./components/fan/FanPanel";
import AlsPanel from "./components/als/ALSPanel";
import InputPlumberSubmenu from "./components/controller/InputPlumberSubmenu";
import { useChargeLimitEnabled, useScreenDisplayControls } from "./hooks/ui";
import { useSupportsCustomFanCurves } from "./hooks/fan";
import { LEGO_SUITE_LOGO_DATA_URI } from "./logoData";
import t, { getCurrentLanguage, setForcedLanguage } from "./i18n/i18n";

type ActiveTab = "tdp" | "controls" | "screen";
const ACTIVE_TAB_STORAGE_KEY = "legoSuite.activeTab";

const App: FC = memo(({}) => {
  useFetchInitialStateEffect();

  const loading = useIsInitiallyLoading();
  const [activeTab, setActiveTab] = useState<ActiveTab>(() => {
    const saved = window.localStorage.getItem(ACTIVE_TAB_STORAGE_KEY);
    if (saved === "controls" || saved === "screen") return saved;
    return "tdp";
  });
  const [showSettings, setShowSettings] = useState(false);
  const [currentLang, setCurrentLang] = useState(() => getCurrentLanguage());
  const [controlsSubmenu, setControlsSubmenu] = useState<"main" | "inputplumber">("main");

  const handleSelectTab = (tab: ActiveTab) => {
    setActiveTab(tab);
    window.localStorage.setItem(ACTIVE_TAB_STORAGE_KEY, tab);
  };

  const backendLang = useSelector(getSystemLangSelector);

  useEffect(() => {
    if (backendLang && (backendLang === "es" || backendLang === "en")) {
      setForcedLanguage(backendLang);
      setCurrentLang(backendLang);
    }
  }, [backendLang]);

  const handleToggleLanguage = (lang: string) => {
    setForcedLanguage(lang);
    setCurrentLang(lang);
    // Persist to backend settings.json so Desktop app and Plugin share language seamlessly
    try {
      call("set_setting", "language", lang);
      call("save_settings", { language: lang, desktopTheme: { language: lang } });
    } catch {}
  };

  const isDesktop = useIsDesktop();
  const tdpControlEnabled = useAdvancedOption(
    AdvancedOptionsEnum.ENABLE_TDP_CONTROL,
  );
  const maxTdpAcProfileEnabled = useSelector(maxTdpAcProfilesEnabledSelector);
  const gpuControlEnabled = useAdvancedOption(
    AdvancedOptionsEnum.ENABLE_GPU_CONTROL,
  );

  const {
    chargeLimitEnabled,
    setChargeLimit,
  } = useChargeLimitEnabled();
  const {
    screenBrightness,
    setScreenBrightness,
    screenContrast,
    setScreenContrast,
  } = useScreenDisplayControls();
  const supportsAcpiCall = useSupportsCustomFanCurves();

  return (
    <>
      {/* Top Header with Transparent Logo, Version 0.198 and Gear Wheel Button */}
      <div
        style={{
          position: "relative",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "4px 16px 8px 16px",
        }}
      >
        <button
          onClick={() => setShowSettings(!showSettings)}
          style={{
            position: "absolute",
            top: "8px",
            right: "16px",
            background: showSettings ? "rgba(255, 255, 255, 0.2)" : "rgba(255, 255, 255, 0.08)",
            border: "1px solid rgba(255, 255, 255, 0.2)",
            borderRadius: "6px",
            color: "#ffffff",
            fontSize: "15px",
            width: "30px",
            height: "30px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            zIndex: 10,
          }}
          title={currentLang === "es" ? "Ajustes de Idioma" : "Language Settings"}
        >
          ⚙
        </button>

        <img
          src={LEGO_SUITE_LOGO_DATA_URI}
          alt="LeGO Suite"
          style={{
            width: "100%",
            maxWidth: "200px",
            objectFit: "contain",
            display: "block",
            background: "transparent",
          }}
        />
        <div
          style={{
            fontSize: "11px",
            color: "#9ca3af",
            marginTop: "2px",
            letterSpacing: "0.06em",
            fontWeight: 600,
          }}
        >
          Version 0.198
        </div>
      </div>

      {/* Settings Modal / Overlay for Language selection */}
      {showSettings && (
        <div
          style={{
            margin: "0 16px 12px 16px",
            padding: "12px",
            backgroundColor: "rgba(255, 255, 255, 0.06)",
            border: "1px solid rgba(255, 255, 255, 0.15)",
            borderRadius: "8px",
          }}
        >
          <div
            style={{
              fontSize: "13px",
              fontWeight: 700,
              color: "#ffffff",
              marginBottom: "8px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>{t("SETTINGS_LANGUAGE_TITLE", "Language / Idioma")}</span>
            <span
              onClick={() => setShowSettings(false)}
              style={{ cursor: "pointer", fontSize: "16px", opacity: 0.7 }}
            >
              ✕
            </span>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <DialogButton
              onClick={() => handleToggleLanguage("es")}
              style={{
                flex: 1,
                padding: "6px",
                backgroundColor: currentLang === "es" ? "#3b82f6" : "rgba(255, 255, 255, 0.1)",
                color: "#ffffff",
                fontWeight: currentLang === "es" ? 700 : 500,
                borderRadius: "4px",
              }}
            >
              ES
            </DialogButton>
            <DialogButton
              onClick={() => handleToggleLanguage("en")}
              style={{
                flex: 1,
                padding: "6px",
                backgroundColor: currentLang === "en" ? "#3b82f6" : "rgba(255, 255, 255, 0.1)",
                color: "#ffffff",
                fontWeight: currentLang === "en" ? 700 : 500,
                borderRadius: "4px",
              }}
            >
              EN
            </DialogButton>
          </div>
        </div>
      )}

      {/* Tab Selector Bar: TDP | Controls | Screen */}
      <div style={{ padding: "0 16px 8px 16px" }}>
        <Focusable
          style={{
            display: "flex",
            flexDirection: "row",
            gap: "6px",
            width: "100%",
          }}
        >
          <DialogButton
            onClick={() => handleSelectTab("tdp")}
            style={{
              flex: 1,
              minWidth: 0,
              padding: "8px 6px",
              fontWeight: activeTab === "tdp" ? 700 : 500,
              backgroundColor:
                activeTab === "tdp"
                  ? "rgba(255, 255, 255, 0.22)"
                  : "rgba(255, 255, 255, 0.06)",
              color: activeTab === "tdp" ? "#ffffff" : "#9ca3af",
              borderBottom:
                activeTab === "tdp"
                  ? "2px solid #ffffff"
                  : "2px solid transparent",
              borderRadius: "6px",
            }}
          >
            {t("TAB_TDP", "TDP")}
          </DialogButton>
          <DialogButton
            onClick={() => handleSelectTab("controls")}
            style={{
              flex: 1,
              minWidth: 0,
              padding: "8px 6px",
              fontWeight: activeTab === "controls" ? 700 : 500,
              backgroundColor:
                activeTab === "controls"
                  ? "rgba(255, 255, 255, 0.22)"
                  : "rgba(255, 255, 255, 0.06)",
              color: activeTab === "controls" ? "#ffffff" : "#9ca3af",
              borderBottom:
                activeTab === "controls"
                  ? "2px solid #ffffff"
                  : "2px solid transparent",
              borderRadius: "6px",
            }}
          >
            {t("TAB_CONTROLS", "Controls")}
          </DialogButton>

        </Focusable>
      </div>

      {!loading && activeTab === "tdp" && (
        <>
          <DeckySection>
            <TdpProfiles isDesktop={isDesktop} />
            {tdpControlEnabled && (
              <TdpSlider disabled={maxTdpAcProfileEnabled} />
            )}
            {gpuControlEnabled && <Gpu />}
          </DeckySection>
          <PowerControl />
          {tdpControlEnabled && (
            <>
              <TdpRange />
              <PollTdp />
            </>
          )}
          <ErrorBoundary title="Fan Panel">
            <FanPanel />
          </ErrorBoundary>
          {supportsAcpiCall && (
            <DeckySection title={t("BATTERY_POWER_TITLE", "Battery & Power")}>
              <DeckyRow>
                <DeckyToggle
                  label={
                    currentLang === "es"
                      ? "Activar Límite de Carga (80%)"
                      : "Enable Charge Limit (80%)"
                  }
                  checked={chargeLimitEnabled}
                  onChange={setChargeLimit}
                />
              </DeckyRow>
            </DeckySection>
          )}
          <AdvancedOptions />
          {!isDesktop && (
            <ErrorBoundary title="System Info">
              <OtaUpdates />
            </ErrorBoundary>
          )}
        </>
      )}

      {!loading && activeTab === "controls" && (
        <>
          {controlsSubmenu === "inputplumber" ? (
            <InputPlumberSubmenu
              currentLang={currentLang}
              onBack={() => setControlsSubmenu("main")}
            />
          ) : (
            <>
              {/* Input Plumber Submenu Navigation Entry */}
              <div
                onClick={() => setControlsSubmenu("inputplumber")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  marginBottom: "8px",
                  background: "linear-gradient(135deg, rgba(37, 99, 235, 0.2) 0%, rgba(14, 165, 233, 0.15) 100%)",
                  border: "1px solid rgba(56, 189, 248, 0.3)",
                  borderRadius: "8px",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <div
                    style={{
                      width: "28px",
                      height: "28px",
                      borderRadius: "6px",
                      background: "rgba(56, 189, 248, 0.2)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#38bdf8",
                      fontSize: "14px",
                    }}
                  >
                    🎮
                  </div>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff" }}>
                      Input Plumber
                    </div>
                    <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                      {currentLang === "es"
                        ? "Modo de mando, emulación y perfiles"
                        : "Controller mode, emulation & profiles"}
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: "16px", color: "#38bdf8", fontWeight: 700 }}>
                  ›
                </div>
              </div>

              <ErrorBoundary title="Remap Buttons">
                <RemapButtons />
              </ErrorBoundary>
              <ErrorBoundary title="Controller Lighting Panel">
                <ControllerLightingPanel />
              </ErrorBoundary>
            </>
          )}
        </>
      )}


    </>
  );
});

const AppContainer: FC = ({}) => {
  return (
    <Provider store={store}>
      <ErrorBoundary title="App">
        <App />
      </ErrorBoundary>
    </Provider>
  );
};

export default AppContainer;
