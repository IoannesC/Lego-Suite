import { useEffect, useState } from "react";
import { DialogButton, Focusable, PanelSectionRow } from "@decky/ui";
import { getTdpMode, setTdpMode } from "../../backend/utils";
import ErrorBoundary from "../ErrorBoundary";

export type TdpMode = "quiet" | "balanced" | "performance" | "custom";

export const TDP_MODE_COLORS: Record<TdpMode, string> = {
  quiet: "#0019ff",
  balanced: "#f3f4f6",
  performance: "#ff0004",
  custom: "#ff00d9",
};

const TDP_MODES: Array<{
  key: TdpMode;
  color: string;
  es: string;
  en: string;
}> = [
  { key: "quiet", color: TDP_MODE_COLORS.quiet, es: "Silencioso", en: "Quiet" },
  { key: "balanced", color: TDP_MODE_COLORS.balanced, es: "Balanceado", en: "Balanced" },
  { key: "performance", color: TDP_MODE_COLORS.performance, es: "Rendimiento", en: "Performance" },
  { key: "custom", color: TDP_MODE_COLORS.custom, es: "Personalizado", en: "Custom" },
];

export const TdpModeButtons = ({
  currentLang = "es",
  onModeChange,
}: {
  currentLang?: string;
  onModeChange?: (mode: TdpMode) => void;
}) => {
  const [activeMode, setActiveMode] = useState<TdpMode>("custom");

  useEffect(() => {
    let mounted = true;
    getTdpMode()
      .then((mode) => {
        if (!mounted || !mode) return;
        const normalized = String(mode).toLowerCase() as TdpMode;
        if (["quiet", "balanced", "performance", "custom"].includes(normalized)) {
          setActiveMode(normalized);
          onModeChange?.(normalized);
        }
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  const handleSelect = (mode: TdpMode) => {
    setActiveMode(mode);
    onModeChange?.(mode);
    setTdpMode(mode);
  };

  return (
    <ErrorBoundary title="TDP Mode">
      <PanelSectionRow>
        <Focusable
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: "6px",
            width: "100%",
          }}
        >
          {TDP_MODES.map((m) => {
            const isActive = activeMode === m.key;
            return (
              <DialogButton
                key={m.key}
                onClick={() => handleSelect(m.key)}
                style={{
                  minWidth: 0,
                  padding: "6px 4px",
                  fontSize: "11px",
                  fontWeight: isActive ? 800 : 600,
                  borderRadius: "6px",
                  backgroundColor: isActive
                    ? m.color
                    : "rgba(255, 255, 255, 0.08)",
                  color: isActive ? "#000000" : "#9ca3af",
                  border: isActive
                    ? "none"
                    : "1px solid rgba(255, 255, 255, 0.08)",
                }}
              >
                {currentLang === "es" ? m.es : m.en}
              </DialogButton>
            );
          })}
        </Focusable>
      </PanelSectionRow>
    </ErrorBoundary>
  );
};
