import t from "../../i18n/i18n";
import {
  ToggleField,
  SliderField,
  ButtonItem,
  gamepadSliderClasses,
} from "@decky/ui";
import { FC, CSSProperties, useState, useEffect } from "react";
import { useRgb, useRgbMode } from "../../hooks/rgb";
import RgbModeSlider from "./RgbModeSlider";
import { RgbModes, ControllerType } from "../../backend/constants";
import { IoMdArrowDropdown, IoMdArrowDropup } from "react-icons/io";
import { STICK_IMAGE_DATA_URI } from "../../logoData";
import { getSettings } from "../../backend/utils";
import { call } from "@decky/api";
import { getCurrentLanguage } from "../../i18n/i18n";

const labelMap = {
  RIGHT: "Right",
  LEFT: "Left",
};

const HIDE_COLOR_PICKER_MODES = [RgbModes.DYNAMIC, RgbModes.SPIRAL];

const CONIC_RAINBOW =
  "conic-gradient(from 0deg, hsl(0, 100%, 55%), hsl(60, 100%, 55%), hsl(120, 100%, 55%), hsl(180, 100%, 55%), hsl(240, 100%, 55%), hsl(300, 100%, 55%), hsl(360, 100%, 55%))";

export const RgbSettings: FC<{ controller: ControllerType }> = ({
  controller,
}) => {
  const rgb = useRgb(controller);
  const separateRgbManagementEnabled = false;
  const { enabled, brightness, speed, hue } = rgb.rgbInfo;
  const [showOptions, setShowOptions] = useState(true);
  const [mode] = useRgbMode(controller);

  const [syncColoredToggles, setSyncColoredTogglesState] = useState(() => {
    try {
      return window.localStorage.getItem("LEGO_SYNC_COLORED_TOGGLES") === "true";
    } catch (e) {
      return false;
    }
  });

  useEffect(() => {
    getSettings()
      .then((s: any) => {
        if (s && s.syncColoredToggles !== undefined) {
          setSyncColoredTogglesState(Boolean(s.syncColoredToggles));
          try {
            window.localStorage.setItem(
              "LEGO_SYNC_COLORED_TOGGLES",
              s.syncColoredToggles ? "true" : "false"
            );
          } catch (e) {}
        }
      })
      .catch(() => {});
  }, []);

  const handleSyncColoredTogglesChange = (checked: boolean) => {
    setSyncColoredTogglesState(checked);
    try {
      window.localStorage.setItem(
        "LEGO_SYNC_COLORED_TOGGLES",
        checked ? "true" : "false"
      );
    } catch (e) {}
    call("set_sync_colored_toggles", checked).catch((err: any) =>
      console.error("set_sync_colored_toggles error:", err)
    );
  };

  const label = separateRgbManagementEnabled
    ? `${labelMap[controller]} Controller LED`
    : "Controller LED";

  const normBrightness = Math.max(0.18, Math.min(1, (brightness ?? 50) / 100));
  const durationSec = (
    Math.max(0.6, 4.4 - ((speed ?? 50) / 100) * 3.6) * 3.5
  ).toFixed(2);
  const activeColor = `hsl(${hue ?? 0}, 100%, 55%)`;
  const glowBlur = Math.round(3 + normBrightness * 6);
  const glowSpread = Math.round(1 + normBrightness * 2);

  const getInnerHaloStyle = (): CSSProperties => {
    const base: CSSProperties = {
      position: "absolute",
      width: "36px",
      height: "36px",
      borderRadius: "50%",
      zIndex: 2,
      pointerEvents: "none",
      transition: "opacity 0.15s ease",
    };

    if (mode === RgbModes.SPIRAL) {
      return {
        ...base,
        background: CONIC_RAINBOW,
        boxShadow: `0 0 ${glowBlur}px ${glowSpread}px rgba(255, 255, 255, ${(normBrightness * 0.45).toFixed(2)})`,
        opacity: normBrightness,
        animation: `legoRgbSpiral ${durationSec}s linear infinite`,
      };
    }

    if (mode === RgbModes.DYNAMIC) {
      return {
        ...base,
        background: "hsl(0, 100%, 55%)",
        boxShadow: `0 0 ${glowBlur}px ${glowSpread}px hsl(0, 100%, 55%)`,
        opacity: normBrightness,
        animation: `legoRgbDynamic ${durationSec}s linear infinite`,
      };
    }

    if (mode === RgbModes.PULSE) {
      return {
        ...base,
        background: activeColor,
        boxShadow: `0 0 ${glowBlur}px ${glowSpread}px ${activeColor}`,
        animation: `legoRgbPulse ${durationSec}s ease-in-out infinite`,
      };
    }

    // SOLID
    return {
      ...base,
      background: activeColor,
      boxShadow: `0 0 ${glowBlur}px ${glowSpread}px ${activeColor}`,
      opacity: normBrightness,
    };
  };

  const renderStickPreview = (key: string) => (
    <div
      key={key}
      style={{
        position: "relative",
        width: "49px",
        height: "49px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <img
        src={STICK_IMAGE_DATA_URI}
        alt={key}
        style={{
          position: "absolute",
          width: "49px",
          height: "49px",
          borderRadius: "50%",
          objectFit: "contain",
          zIndex: 1,
          pointerEvents: "none",
        }}
      />

      {mode === RgbModes.SPIRAL && (
        <div
          style={{
            position: "absolute",
            width: "39px",
            height: "39px",
            borderRadius: "50%",
            background: CONIC_RAINBOW,
            filter: `blur(${Math.round(2 + normBrightness * 3)}px)`,
            opacity: normBrightness * 0.85,
            zIndex: 2,
            pointerEvents: "none",
            animation: `legoRgbSpiral ${durationSec}s linear infinite`,
          }}
        />
      )}

      <div style={getInnerHaloStyle()} />

      <div
        style={{
          position: "absolute",
          width: "29px",
          height: "29px",
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(22,22,22,0.94) 0%, rgba(28,28,28,0.9) 76%, rgba(30,30,30,0) 100%)",
          zIndex: 3,
          pointerEvents: "none",
        }}
      />
    </div>
  );

  return (
    <>
      <ToggleField
        label={label}
        checked={enabled}
        onChange={rgb.setEnabled}
        bottomSeparator={enabled ? "none" : "thick"}
      />
      {enabled && (
        <>
          <ButtonItem
            layout={"below"}
            bottomSeparator={showOptions ? "none" : "thick"}
            style={{
              width: "100%",
              height: "20px",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
            onClick={() => setShowOptions(!showOptions)}
          >
            {showOptions ? <IoMdArrowDropup /> : <IoMdArrowDropdown />}
          </ButtonItem>
        </>
      )}
      {showOptions && enabled && (
        <>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "space-between",
              width: "100%",
              boxSizing: "border-box",
              padding: "8px 18px 4px 18px",
            }}
          >
            {renderStickPreview("left-stick")}
            {renderStickPreview("right-stick")}
          </div>

          <RgbModeSlider controller={controller} />
          <SliderField
            label={`Brightness`}
            valueSuffix="%"
            value={brightness}
            showValue={true}
            min={1}
            max={100}
            validValues="range"
            bottomSeparator={"none"}
            onChange={(value) => rgb.updateBrightness(value)}
          ></SliderField>
          {mode !== RgbModes.SOLID && (
            <SliderField
              label={t("RGB_SPEED", "Speed")}
              valueSuffix="%"
              value={speed}
              showValue={true}
              min={1}
              max={100}
              validValues="range"
              onChange={(value) => rgb.setSpeed(value)}
            ></SliderField>
          )}
          {!HIDE_COLOR_PICKER_MODES.includes(mode) && (
            <>
              <div className="ColorPicker_HSlider">
                <SliderField
                  showValue
                  label={t("RGB_HUE", "Hue")}
                  value={hue}
                  min={0}
                  max={359}
                  validValues="range"
                  bottomSeparator="none"
                  onChange={(value) => rgb.setHue(value)}
                />
              </div>
              {(mode === RgbModes.SOLID || mode === RgbModes.PULSE) && (
                <ToggleField
                  label={
                    getCurrentLanguage() === "es"
                      ? "Vincular con CSS Loader (Colored Toggles)"
                      : "Sync with CSS Loader (Colored Toggles)"
                  }
                  description={
                    getCurrentLanguage() === "es"
                      ? "Actualiza el color de Colored Toggles al tono del stick"
                      : "Updates Colored Toggles color to match stick hue"
                  }
                  checked={syncColoredToggles}
                  onChange={handleSyncColoredTogglesChange}
                  bottomSeparator="thick"
                />
              )}
            </>
          )}
          <style>
            {`
            @keyframes legoRgbPulse {
              0%, 100% {
                opacity: ${Math.max(0.12, normBrightness * 0.18).toFixed(2)};
                transform: scale(0.92);
              }
              50% {
                opacity: ${normBrightness.toFixed(2)};
                transform: scale(1.04);
              }
            }
            @keyframes legoRgbDynamic {
              0% {
                filter: hue-rotate(0deg);
              }
              100% {
                filter: hue-rotate(360deg);
              }
            }
            @keyframes legoRgbSpiral {
              0% {
                transform: rotate(0deg);
              }
              100% {
                transform: rotate(360deg);
              }
            }
            .ColorPicker_HSlider .${gamepadSliderClasses.SliderTrack} {
              background: linear-gradient(
                to right,
                hsl(0, 100%, 50%),
                hsl(60, 100%, 50%),
                hsl(120, 100%, 50%),
                hsl(180, 100%, 50%),
                hsl(240, 100%, 50%),
                hsl(300, 100%, 50%),
                hsl(360, 100%, 50%)
              ) !important;
              --left-track-color: #0000 !important;
              --colored-toggles-main-color: #0000 !important;
            }
          `}
          </style>
        </>
      )}
    </>
  );
};
