import t from "../../i18n/i18n";
import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  ToggleField,
} from "@decky/ui";
import {
  useCustomFanCurvesEnabled,
  useEnableFullFanSpeedMode,
  useFanPerGameProfilesEnabled,
  useSupportsCustomFanCurves,
} from "../../hooks/fan";
import { capitalize } from "lodash";
import { useSelector } from "react-redux";
import { useState, useEffect } from "react";
import { selectCurrentGameDisplayName } from "../../redux-modules/uiSlice";
import FanCurveSliders from "./FanCurveSliders";
import { IoMdArrowDropdown, IoMdArrowDropup } from "react-icons/io";
import { call } from "@decky/api";

const useTitle = (fanPerGameProfilesEnabled: boolean) => {
  const currentDisplayName = useSelector(selectCurrentGameDisplayName);

  if (!fanPerGameProfilesEnabled) {
    return t("FAN_PANEL_TITLE", "Fan Control");
  }

  const title = `${t("FAN_PANEL_TITLE", "Fan Control")} - ${capitalize(currentDisplayName)}`;

  return title;
};

const useTemperatures = () => {
  const [temps, setTemps] = useState<{ cpu: number | null; gpu: number | null; rpm: number | null }>({
    cpu: null,
    gpu: null,
    rpm: null,
  });

  useEffect(() => {
    let mounted = true;
    const fetchTemps = () => {
      try {
        call("get_temperatures").then((res: any) => {
          if (mounted && res && typeof res === "object") {
            setTemps({
              cpu: res.cpu !== null && res.cpu !== undefined ? Number(res.cpu) : null,
              gpu: res.gpu !== null && res.gpu !== undefined ? Number(res.gpu) : null,
              rpm: res.rpm !== null && res.rpm !== undefined ? Number(res.rpm) : null,
            });
          }
        }).catch(() => {});
      } catch (e) {}
    };
    fetchTemps();
    const interval = setInterval(fetchTemps, 2000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return temps;
};

const FanPanel = () => {
  const supportsFanCurves = useSupportsCustomFanCurves();
  const { cpu: cpuTemp, gpu: gpuTemp, rpm: fanRpm } = useTemperatures();
  const [showSliders, setShowSliders] = useState(true);

  const { enableFullFanSpeedMode, setEnableFullFanSpeedMode } =
    useEnableFullFanSpeedMode();

  const { customFanCurvesEnabled, setCustomFanCurvesEnabled } =
    useCustomFanCurvesEnabled();
  const { fanPerGameProfilesEnabled, setFanPerGameProfilesEnabled } =
    useFanPerGameProfilesEnabled();
  const title = useTitle(fanPerGameProfilesEnabled);

  if (!supportsFanCurves) {
    return null;
  }

  const spinDuration = fanRpm ? Math.max(0.35, Math.min(2.5, 2.5 - ((fanRpm - 1500) / 5500) * 2.0)) : 1.2;
  const fanColor = fanRpm ? (fanRpm < 4000 ? "#38bdf8" : (fanRpm < 5500 ? "#facc15" : "#ef4444")) : "#38bdf8";

  return (
    <>
      <style>{`@keyframes legosuitetwirl { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      {}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          width: "100%",
          padding: "8px 10px",
          marginBottom: "8px",
          backgroundColor: "rgba(255, 255, 255, 0.06)",
          borderRadius: "6px",
        }}
      >
        {}
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <span style={{ fontWeight: 600, fontSize: "11px", color: "#9ca3af" }}>
            Temp CPU:
          </span>
          <span
            style={{
              fontWeight: 800,
              fontSize: "11px",
              color:
                cpuTemp !== null
                  ? cpuTemp < 60
                    ? "#38bdf8"
                    : cpuTemp < 75
                    ? "#facc15"
                    : "#ef4444"
                  : "#9ca3af",
              backgroundColor:
                cpuTemp !== null
                  ? cpuTemp < 60
                    ? "rgba(56, 189, 248, 0.15)"
                    : cpuTemp < 75
                    ? "rgba(250, 204, 21, 0.15)"
                    : "rgba(239, 68, 68, 0.2)"
                  : "transparent",
              padding: "2px 5px",
              borderRadius: "4px",
            }}
          >
            {cpuTemp !== null ? `${cpuTemp.toFixed(1)} °C` : "-- °C"}
          </span>
        </div>

        {}
        <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
          <svg
            viewBox="-11 -11 22 22"
            width="18"
            height="18"
            style={{
              animation: `legosuitetwirl ${spinDuration}s linear infinite`,
              transformOrigin: "center center",
              color: fanColor,
              display: "block",
            }}
          >
            <path d="M 0 0 Q 6.3 -3.15 9 0 Q 4.5 4.05 0 0 Z" fill="currentColor" />
            <path d="M 0 0 Q 3.15 6.3 0 9 Q -4.05 4.5 0 0 Z" fill="currentColor" />
            <path d="M 0 0 Q -6.3 3.15 -9 0 Q -4.5 -4.05 0 0 Z" fill="currentColor" />
            <path d="M 0 0 Q -3.15 -6.3 0 -9 Q 4.05 -4.5 0 0 Z" fill="currentColor" />
            <circle cx="0" cy="0" r="2.8" fill="#1e293b" />
          </svg>
          <span
            style={{
              fontWeight: 800,
              fontSize: "11px",
              color: fanRpm
                ? fanRpm < 4000
                  ? "#38bdf8"
                  : fanRpm < 5500
                  ? "#facc15"
                  : "#ef4444"
                : "#9ca3af",
              backgroundColor: fanRpm
                ? fanRpm < 4000
                  ? "rgba(56, 189, 248, 0.15)"
                  : fanRpm < 5500
                  ? "rgba(250, 204, 21, 0.15)"
                  : "rgba(239, 68, 68, 0.2)"
                : "transparent",
              padding: "2px 5px",
              borderRadius: "4px",
            }}
          >
            {fanRpm !== null ? `${fanRpm} RPM` : "-- RPM"}
          </span>
        </div>

        {}
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <span style={{ fontWeight: 600, fontSize: "11px", color: "#9ca3af" }}>
            Temp GPU:
          </span>
          <span
            style={{
              fontWeight: 800,
              fontSize: "11px",
              color:
                gpuTemp !== null
                  ? gpuTemp < 60
                    ? "#38bdf8"
                    : gpuTemp < 75
                    ? "#facc15"
                    : "#ef4444"
                  : "#9ca3af",
              backgroundColor:
                gpuTemp !== null
                  ? gpuTemp < 60
                    ? "rgba(56, 189, 248, 0.15)"
                    : gpuTemp < 75
                    ? "rgba(250, 204, 21, 0.15)"
                    : "rgba(239, 68, 68, 0.2)"
                  : "transparent",
              padding: "2px 5px",
              borderRadius: "4px",
            }}
          >
            {gpuTemp !== null ? `${gpuTemp.toFixed(1)} °C` : "-- °C"}
          </span>
        </div>
      </div>

      <PanelSection title={title}>
        <PanelSectionRow>
          <ToggleField
            label={t("FAN_ENABLE_CUSTOM_CURVES", "Enable Custom Fan Curves")}
            checked={customFanCurvesEnabled}
            onChange={setCustomFanCurvesEnabled}
          />
        </PanelSectionRow>
        {customFanCurvesEnabled && (
          <>
            <PanelSectionRow>
              <ToggleField
                label={t("FAN_ENABLE_PER_GAME", "Enable Per Game Fan Curves")}
                checked={fanPerGameProfilesEnabled}
                onChange={setFanPerGameProfilesEnabled}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <ButtonItem
                layout="below"
                bottomSeparator={showSliders ? "none" : "thick"}
                style={{
                  width: "100%",
                  height: "20px",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                }}
                onClick={() => setShowSliders(!showSliders)}
              >
                {showSliders ? <IoMdArrowDropup /> : <IoMdArrowDropdown />}
              </ButtonItem>
            </PanelSectionRow>
            {showSliders && (
              <PanelSectionRow>
                <ToggleField
                  label={t("FAN_ENABLE_FULL_SPEED", "Enable Full Fan Speed Mode")}
                  checked={enableFullFanSpeedMode}
                  onChange={setEnableFullFanSpeedMode}
                />
              </PanelSectionRow>
            )}
          </>
        )}
      </PanelSection>
      {customFanCurvesEnabled && !enableFullFanSpeedMode && showSliders && (
        <FanCurveSliders />
      )}
    </>
  );
};

export default FanPanel;
