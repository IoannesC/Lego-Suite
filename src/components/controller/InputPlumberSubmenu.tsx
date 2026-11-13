import React, { useState, useEffect } from "react";
import {
  DeckyRow,
  DeckyToggle,
} from "../atoms/DeckyFrontendLib";
import { DropdownItem } from "@decky/ui";
import { call } from "@decky/api";
import { FaGamepad, FaChevronLeft, FaCheckCircle, FaExclamationTriangle } from "react-icons/fa";

interface ModeOption {
  data: string;
  label_es: string;
  label_en: string;
}

interface PresetProfile {
  id: string;
  name: string;
  name_es?: string;
  name_en?: string;
  description: string;
  description_es?: string;
  description_en?: string;
  isPreset: boolean;
}

interface IpInfo {
  serviceActive: boolean;
  dbusReady: boolean;
  currentMode: string;
  modes: ModeOption[];
  presetProfiles: PresetProfile[];
  activeProfiles: string[];
}

export const InputPlumberSubmenu: React.FC<{
  currentLang: string;
  onBack: () => void;
}> = ({ currentLang, onBack }) => {
  const [ipInfo, setIpInfo] = useState<IpInfo | null>(null);
  const [selectedMode, setSelectedMode] = useState("default");
  const [activeProfiles, setActiveProfiles] = useState<string[]>([]);
  const [statusMsg, setStatusMsg] = useState("");
  const [resetting, setResetting] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);

  const handleResetControllers = async () => {
    setResetting(true);
    try {
      await call("reset_controllers");
      setResetSuccess(true);
      setTimeout(() => {
        setResetSuccess(false);
        refreshInfo();
      }, 3000);
    } catch (err: any) {
      console.error("Failed to reset controllers", err);
    } finally {
      setResetting(false);
    }
  };

  const refreshInfo = async () => {
    try {
      const res = await call<any, IpInfo>("get_inputplumber_info");
      if (res) {
        setIpInfo(res);
        setSelectedMode(res.currentMode || "default");
        if (Array.isArray(res.activeProfiles)) {
          setActiveProfiles(res.activeProfiles);
        }
      }
    } catch (e) {
      console.error("Failed to load InputPlumber info", e);
    }
  };

  useEffect(() => {
    refreshInfo();
  }, []);

  const handleModeChange = async (mode: string) => {
    setSelectedMode(mode);
    setStatusMsg(currentLang === "es" ? "Cambiando modo..." : "Changing mode...");
    try {
      const ok = await call<any, boolean>("set_inputplumber_mode", mode);
      if (ok) {
        setStatusMsg(currentLang === "es" ? "Modo aplicado correctamente" : "Mode applied successfully");
      } else {
        setStatusMsg(currentLang === "es" ? "Comprueba que inputplumber esté iniciado" : "Verify that inputplumber is running");
      }
    } catch (err: any) {
      setStatusMsg(`Error: ${err?.message || err}`);
    }
    setTimeout(() => {
      refreshInfo();
      setStatusMsg("");
    }, 2000);
  };

  const handleToggleProfile = async (profId: string, checked: boolean) => {
    const next = checked
      ? [...activeProfiles.filter((id) => id !== profId), profId]
      : activeProfiles.filter((id) => id !== profId);
    setActiveProfiles(next);
    try {
      await call("set_inputplumber_profiles", next);
    } catch (err: any) {
      console.error("Failed to set InputPlumber profiles", err);
    }
  };

  const isEs = currentLang === "es";

  const dropdownOptions = (ipInfo?.modes || []).map((m) => ({
    data: m.data,
    label: isEs ? m.label_es : m.label_en,
  }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {}
      <div
        onClick={onBack}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          cursor: "pointer",
          padding: "8px 12px",
          background: "rgba(255, 255, 255, 0.05)",
          borderRadius: "8px",
          color: "#60a5fa",
          fontWeight: 600,
          fontSize: "13px",
        }}
      >
        <FaChevronLeft />
        <span>{isEs ? "Volver a Controles" : "Back to Controls"}</span>
      </div>

      <div
        style={{
          background: "rgba(30, 41, 59, 0.5)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          borderRadius: "10px",
          padding: "12px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "14px" }}>
            <FaGamepad style={{ color: "#38bdf8" }} />
            <span>Input Plumber</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
            {ipInfo?.serviceActive || ipInfo?.dbusReady ? (
              <span style={{ color: "#10b981", display: "flex", alignItems: "center", gap: "4px" }}>
                <FaCheckCircle /> {isEs ? "Activo" : "Active"}
              </span>
            ) : (
              <span style={{ color: "#f59e0b", display: "flex", alignItems: "center", gap: "4px" }}>
                <FaExclamationTriangle /> {isEs ? "Inactivo / Standby" : "Inactive / Standby"}
              </span>
            )}
          </div>
        </div>

        {statusMsg && (
          <div
            style={{
              padding: "6px 10px",
              borderRadius: "6px",
              background: "rgba(59, 130, 246, 0.2)",
              color: "#93c5fd",
              fontSize: "12px",
              textAlign: "center",
            }}
          >
            {statusMsg}
          </div>
        )}

        {}
        <DeckyRow>
          <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "12px", color: "#9ca3af", fontWeight: 600 }}>
              {isEs ? "Objetivo de emulación" : "Target Emulation"}
            </label>
            <DropdownItem
              label=""
              selectedOption={selectedMode}
              rgOptions={dropdownOptions}
              onChange={(opt: any) => handleModeChange(opt.data)}
              bottomSeparator="none"
            />
          </div>
        </DeckyRow>

        {}
        <div style={{ borderTop: "1px solid rgba(255, 255, 255, 0.08)", paddingTop: "10px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#e2e8f0", marginBottom: "8px" }}>
            {isEs ? "Perfiles de Mapeo Rápido" : "Quick Mapping Profiles"}
          </div>

          {(ipInfo?.presetProfiles || []).map((prof) => {
            const isChecked = activeProfiles.includes(prof.id);
            const profName = isEs
              ? (prof.name_es || (prof.id === "swap_menu_buttons" ? "Intercambiar Botones de Menú" : prof.id === "swap_volume" ? "Intercambiar Botones de Volumen" : prof.name))
              : (prof.name_en || prof.name);
            const profDesc = isEs
              ? (prof.description_es || (prof.id === "swap_menu_buttons" ? "Intercambia Select/Guía y Start/Ajustes rápidos" : prof.id === "swap_volume" ? "Invierte los botones de subir y bajar volumen" : prof.description))
              : (prof.description_en || prof.description);
            return (
              <DeckyRow key={prof.id}>
                <DeckyToggle
                  label={profName}
                  description={profDesc}
                  checked={isChecked}
                  onChange={(checked: boolean) => handleToggleProfile(prof.id, checked)}
                />
              </DeckyRow>
            );
          })}
        </div>

        {}
        <div style={{ borderTop: "1px solid rgba(255, 255, 255, 0.08)", paddingTop: "12px" }}>
          <button
            onClick={handleResetControllers}
            disabled={resetting}
            style={{
              width: "100%",
              padding: "10px 12px",
              background: resetSuccess
                ? "rgba(16, 185, 129, 0.2)"
                : "rgba(239, 68, 68, 0.15)",
              border: resetSuccess
                ? "1px solid rgba(16, 185, 129, 0.4)"
                : "1px solid rgba(239, 68, 68, 0.35)",
              borderRadius: "8px",
              color: resetSuccess ? "#34d399" : "#f87171",
              fontWeight: 700,
              fontSize: "12px",
              cursor: resetting ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
            }}
          >
            {resetting ? (
              <span>{isEs ? "Reseteando mandos..." : "Resetting controllers..."}</span>
            ) : resetSuccess ? (
              <span>{isEs ? "✓ Mandos reseteados correctamente" : "✓ Controllers reset successfully"}</span>
            ) : (
              <span>{isEs ? "🔄 Resetear Mandos" : "🔄 Reset Controllers"}</span>
            )}
          </button>
          <div style={{ fontSize: "10px", color: "#64748b", marginTop: "6px", textAlign: "center", lineHeight: "1.3" }}>
            {isEs
              ? "Reinicio USB + valores de fábrica (HHD). Atajo físico: Izq: Legion L + LB + LS | Der: Legion R + RB + RS"
              : "USB reset + factory defaults (HHD). Hardware combo: Left: Legion L + LB + LS | Right: Legion R + RB + RS"}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InputPlumberSubmenu;
