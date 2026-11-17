import { useState, useEffect } from "react";
import { DropdownItem, Field, PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { runInstallFGMod, runUninstallFGMod, setDefaultFsr4Variant } from "../api";
import { OperationResult } from "./ResultDisplay";
import { createAutoCleanupTimer } from "../utils";
import { TIMEOUTS, getProxyDllOptions, getFsr4VariantOptions } from "../utils/constants";
import t from "../../i18n/i18n";
import { InstallationStatus } from "./InstallationStatus";
import { OptiScalerHeader } from "./OptiScalerHeader";
import { ClipboardCommands } from "./ClipboardCommands";
import { InstructionCard } from "./InstructionCard";
import { OptiScalerWiki } from "./OptiScalerWiki";
import { UninstallButton } from "./UninstallButton";
import { ManualPatchControls } from "./CustomPathOverride";
import { SteamGamePatcher } from "./SteamGamePatcher";

interface FgmodInfo {
  exists: boolean;
  version?: string | null;
  selected_fsr4_variant?: string | null;
  selected_fsr4_variant_label?: string | null;
  install_manifest_present?: boolean;
}

interface OptiScalerControlsProps {
  pathExists: boolean | null;
  setPathExists: (exists: boolean | null) => void;
  fgmodInfo?: FgmodInfo | null;
  dllName: string;
  setDllName: (dll: string) => void;
  fsr4Variant: string;
  setFsr4Variant: (variant: string) => void;
}

export function OptiScalerControls({
  pathExists,
  setPathExists,
  fgmodInfo,
  dllName,
  setDllName,
  fsr4Variant,
  setFsr4Variant,
}: OptiScalerControlsProps) {
  const [installing, setInstalling] = useState(false);
  const [uninstalling, setUninstalling] = useState(false);
  const [installResult, setInstallResult] = useState<OperationResult | null>(null);
  const [uninstallResult, setUninstallResult] = useState<OperationResult | null>(null);
  const [advancedModeEnabled, setAdvancedModeEnabled] = useState(false);
  const [manualClipboardModeEnabled, setManualClipboardModeEnabled] = useState(false);
  const [fsr4VariantTouched, setFsr4VariantTouched] = useState(false);
  const [switchingVariant, setSwitchingVariant] = useState(false);
  useEffect(() => {
    if (installResult) {
      return createAutoCleanupTimer(() => setInstallResult(null), TIMEOUTS.resultDisplay);
    }
    return () => {}; // Ensure a cleanup function is always returned
  }, [installResult]);

  useEffect(() => {
    if (uninstallResult) {
      return createAutoCleanupTimer(() => setUninstallResult(null), TIMEOUTS.resultDisplay);
    }
    return () => {}; // Ensure a cleanup function is always returned
  }, [uninstallResult]);

  useEffect(() => {
    const installedVariant = fgmodInfo?.selected_fsr4_variant;
    if (!fsr4VariantTouched && installedVariant && getFsr4VariantOptions().some((option) => option.value === installedVariant)) {
      setFsr4Variant(installedVariant);
    }
  }, [fgmodInfo?.selected_fsr4_variant, fsr4VariantTouched]);

  const handleInstallClick = async () => {
    try {
      setInstalling(true);
      const result = await runInstallFGMod(fsr4Variant);
      setInstallResult(result);
      if (result.status === "success") {
        setPathExists(true);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setInstalling(false);
    }
  };

  const handleUninstallClick = async () => {
    try {
      setUninstalling(true);
      const result = await runUninstallFGMod();
      setUninstallResult(result);
      if (result.status === "success") {
        setPathExists(false);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setUninstalling(false);
    }
  };

  const handleFsr4VariantChange = async (nextVariant: string) => {
    const previousVariant = fsr4Variant;
    setFsr4Variant(nextVariant);
    setFsr4VariantTouched(true);

    if (pathExists !== true) return;

    try {
      setSwitchingVariant(true);
      const result = await setDefaultFsr4Variant(nextVariant);
      if (result.status !== "success") {
        throw new Error(result.message || result.output || "Failed to switch default FSR4 runtime.");
      }
      setFsr4Variant(result.selected_default_variant || nextVariant);
      setFsr4VariantTouched(false);
    } catch (error) {
      console.error(error);
      setFsr4Variant(previousVariant);
    } finally {
      setSwitchingVariant(false);
    }
  };

  const fsr4Options = getFsr4VariantOptions();
  const proxyDllOptions = getProxyDllOptions();
  const installedVariantLabel = fgmodInfo?.selected_fsr4_variant_label || fsr4Options.find((option) => option.value === fsr4Variant)?.label;

  return (
    <PanelSection>
      <InstallationStatus 
        pathExists={pathExists}
        installing={installing}
        onInstallClick={handleInstallClick}
      />
      
      <OptiScalerHeader pathExists={pathExists} />

      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label={t("OPTISCALER_DEFAULT_FSR4_RUNTIME", "Default FSR4 runtime")}
          description={fsr4Options.find((option) => option.value === fsr4Variant)?.hint}
          menuLabel={t("OPTISCALER_DEFAULT_FSR4_RUNTIME", "Default FSR4 runtime")}
          selectedOption={fsr4Variant}
          rgOptions={fsr4Options.map((option) => ({ data: option.value, label: option.label }))}
          disabled={installing || uninstalling || switchingVariant}
          onChange={(option) => {
            void handleFsr4VariantChange(String(option.data));
          }}
        />
      </PanelSectionRow>

      {pathExists === true && fgmodInfo?.version && installedVariantLabel && (
        <PanelSectionRow>
          <Field label={t("OPTISCALER_INSTALLED_BUNDLE", "Installed bundle")} description={`OptiScaler ${fgmodInfo.version}`}>
            {installedVariantLabel}
          </Field>
        </PanelSectionRow>
      )}

      {pathExists === true && (
        <PanelSectionRow>
          <DropdownItem
            layout="below"
            label={t("OPTISCALER_PROXY_DLL_NAME", "Proxy DLL name")}
            description={proxyDllOptions.find((o) => o.value === dllName)?.hint}
            menuLabel={t("OPTISCALER_PROXY_DLL_NAME", "Proxy DLL name")}
            selectedOption={dllName}
            rgOptions={proxyDllOptions.map((o) => ({ data: o.value, label: o.label }))}
            onChange={(option) => setDllName(String(option.data))}
          />
        </PanelSectionRow>
      )}

      {pathExists === true && (
        <SteamGamePatcher dllName={dllName} fsr4Variant={fsr4Variant} />
      )}

      <ClipboardCommands pathExists={pathExists} dllName={dllName} />

      {pathExists === true && (
        <PanelSectionRow>
          <ToggleField
            label={t("OPTISCALER_MANUAL_MODE", "Manual Mode")}
            description={t("OPTISCALER_MANUAL_MODE_DESC", "Show wrapper command clipboard buttons for patching and unpatching through ~/fgmod scripts.")}
            checked={manualClipboardModeEnabled}
            onChange={setManualClipboardModeEnabled}
          />
        </PanelSectionRow>
      )}

      {pathExists === true && manualClipboardModeEnabled ? (
        <ClipboardCommands
          pathExists={pathExists}
          dllName={dllName}
          manualModeEnabled
          showLaunchOptions={false}
        />
      ) : null}

      <ManualPatchControls
        isAvailable={pathExists === true}
        onManualModeChange={setAdvancedModeEnabled}
        dllName={dllName}
        fsr4Variant={fsr4Variant}
      />

      {!advancedModeEnabled && (
        <InstructionCard pathExists={pathExists} />
      )}
      <OptiScalerWiki pathExists={pathExists} />
      
      <UninstallButton 
        pathExists={pathExists}
        uninstalling={uninstalling}
        onUninstallClick={handleUninstallClick}
      />
    </PanelSection>
  );
}
