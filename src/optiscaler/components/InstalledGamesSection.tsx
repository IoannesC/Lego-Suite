import { useState, useEffect, useMemo } from "react";
import { PanelSection, PanelSectionRow, ButtonItem, DropdownItem, ConfirmModal, showModal } from "@decky/ui";
import { listInstalledGames, logError, runManualPatch, runManualUnpatch } from "../api";
import { safeAsyncOperation } from "../utils";
import { STYLES } from "../utils/constants";
import { GameInfo } from "../types/index";
import t from "../../i18n/i18n";

let lastSelectedGame: GameInfo | null = null;

interface InstalledGamesSectionProps {
  dllName?: string;
  fsr4Variant?: string;
}

export function InstalledGamesSection({ dllName = "dxgi.dll", fsr4Variant = "" }: InstalledGamesSectionProps) {
  const [games, setGames] = useState<GameInfo[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameInfo | null>(() => lastSelectedGame);
  const [result, setResult] = useState<string>('');

  useEffect(() => {
    const fetchGames = async () => {
      const response = await safeAsyncOperation(
        async () => await listInstalledGames(),
        'fetchGames'
      );
      
      if (response?.status === "success") {
        const sortedGames = [...response.games]
          .map(game => ({
            ...game,
            appid: parseInt(game.appid, 10),
          }))
          .sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
        setGames(sortedGames);
      } else if (response) {
        logError('fetchGames: ' + JSON.stringify(response));
        console.error('fetchGames: ' + JSON.stringify(response));
      }
    };
    
    fetchGames();
  }, []);

  const handlePatchClick = async () => {
    if (!selectedGame) return;

    // Show confirmation modal
    showModal(
      <ConfirmModal 
        strTitle={`${t("OPTISCALER_ENABLE_FG_FOR", "Enable Frame Generation for")} ${selectedGame.name}?`}
        strDescription={t(
          "OPTISCALER_ENABLE_FG_MODAL_DESC",
          "Important: This plugin does not automatically unpatch games when uninstalled. If you uninstall this plugin or experience game issues, use the 'Disable Frame Generation' option or verify game file integrity through Steam."
        )}
        strOKButtonText={t("OPTISCALER_ENABLE_FG", "Enable Frame Generation")}
        strCancelButtonText={t("OPTISCALER_CANCEL", "Cancel")}
        onOK={async () => {
          try {
            if (selectedGame.source === "unifideck") {
              if (selectedGame.install_dir) {
                await runManualPatch(selectedGame.install_dir, dllName, fsr4Variant);
              }
              const cleanOptions = (selectedGame.launch_options || "")
                .replace(/~\/fgmod\/fgmod(?:-uninstaller\.sh)?\s+%COMMAND%\s*/gi, "")
                .replace(/\s*WINEDLLOVERRIDES="[^"]*"/g, "")
                .trim();
              const dllStem = dllName.replace(/\.dll$/i, "");
              const overrideFlag = dllName.toLowerCase().endsWith(".dll")
                ? `WINEDLLOVERRIDES="${dllStem}=n,b"`
                : "";
              const newOptions = overrideFlag ? `${cleanOptions} ${overrideFlag}`.trim() : cleanOptions;
              await SteamClient.Apps.SetAppLaunchOptions(Number(selectedGame.appid), newOptions);
              setResult(t("OPTISCALER_FG_ENABLED_MSG", "Frame generation enabled for {name}. Launch the game, enable DLSS in graphics settings, then press Insert to access OptiScaler options.").replace("{name}", `${selectedGame.name} (${dllName})`));
            } else {
              await SteamClient.Apps.SetAppLaunchOptions(Number(selectedGame.appid), '~/fgmod/fgmod %COMMAND%');
              setResult(t("OPTISCALER_FG_ENABLED_MSG", "Frame generation enabled for {name}. Launch the game, enable DLSS in graphics settings, then press Insert to access OptiScaler options.").replace("{name}", selectedGame.name));
            }
          } catch (error) {
            logError('handlePatchClick: ' + String(error));
            setResult(error instanceof Error ? `Error: ${error.message}` : t("OPTISCALER_ERROR_ENABLING", "Error enabling frame generation"));
          }
        }}
      />
    );
  };

  const handleUnpatchClick = async () => {
    if (!selectedGame) return;

    try {
      if (selectedGame.source === "unifideck") {
        if (selectedGame.install_dir) {
          await runManualUnpatch(selectedGame.install_dir);
        }
        const cleanOptions = (selectedGame.launch_options || "")
          .replace(/~\/fgmod\/fgmod(?:-uninstaller\.sh)?\s+%COMMAND%\s*/gi, "")
          .replace(/\s*WINEDLLOVERRIDES="[^"]*"/g, "")
          .trim();
        await SteamClient.Apps.SetAppLaunchOptions(Number(selectedGame.appid), cleanOptions);
        setResult(t("OPTISCALER_FG_DISABLED_UNIFIDECK_MSG", "Frame generation disabled for {name} (unpatched game folder & preserved Unifideck store token).").replace("{name}", selectedGame.name));
      } else {
        await SteamClient.Apps.SetAppLaunchOptions(Number(selectedGame.appid), '~/fgmod/fgmod-uninstaller.sh %COMMAND%');
        setResult(t("OPTISCALER_FG_DISABLED_STEAM_MSG", "Frame generation will be disabled on next launch of {name}.").replace("{name}", selectedGame.name));
      }
    } catch (error) {
      logError('handleUnpatchClick: ' + String(error));
      setResult(error instanceof Error ? `Error: ${error.message}` : t("OPTISCALER_ERROR_DISABLING", "Error disabling frame generation"));
    }
  };

  const steamGames = useMemo(
    () => games.filter(g => g.source !== "unifideck" && g.source !== "non_steam"),
    [games]
  );
  const unifideckGames = useMemo(
    () => games.filter(g => g.source === "unifideck"),
    [games]
  );
  const nonSteamGames = useMemo(
    () => games.filter(g => g.source === "non_steam"),
    [games]
  );

  const steamOptions = useMemo(
    () => steamGames.map(game => ({ data: String(game.appid), label: game.name })),
    [steamGames]
  );
  const unifideckOptions = useMemo(
    () => unifideckGames.map(game => ({ data: String(game.appid), label: game.name })),
    [unifideckGames]
  );
  const nonSteamOptions = useMemo(
    () => nonSteamGames.map(game => ({ data: String(game.appid), label: game.name })),
    [nonSteamGames]
  );

  const selectedSteamId =
    selectedGame && selectedGame.source !== "unifideck" && selectedGame.source !== "non_steam"
      ? String(selectedGame.appid)
      : undefined;
  const selectedUnifideckId =
    selectedGame?.source === "unifideck" ? String(selectedGame.appid) : undefined;
  const selectedNonSteamId =
    selectedGame?.source === "non_steam" ? String(selectedGame.appid) : undefined;

  return (
    <PanelSection title={t("OPTISCALER_SELECT_GAME_TITLE", "Select a Game to Patch:")}>
      <PanelSectionRow>
        <DropdownItem
          label={t("OPTISCALER_STEAM_GAMES", "Steam Games")}
          layout="below"
          rgOptions={steamOptions}
          selectedOption={selectedSteamId}
          onChange={(option) => {
            const game = steamGames.find(g => String(g.appid) === String(option.data)) || null;
            lastSelectedGame = game;
            setSelectedGame(game);
            setResult('');
          }}
          strDefaultLabel={t("OPTISCALER_CHOOSE_STEAM_GAME", "Choose a Steam game")}
          menuLabel={t("OPTISCALER_STEAM_GAMES", "Steam Games")}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <DropdownItem
          label={t("OPTISCALER_UNIFIDECK_GAMES", "Unifideck Games")}
          layout="below"
          rgOptions={unifideckOptions}
          selectedOption={selectedUnifideckId}
          onChange={(option) => {
            const game = unifideckGames.find(g => String(g.appid) === String(option.data)) || null;
            lastSelectedGame = game;
            setSelectedGame(game);
            setResult('');
          }}
          strDefaultLabel={t("OPTISCALER_CHOOSE_UNIFIDECK_GAME", "Choose a Unifideck game")}
          menuLabel={t("OPTISCALER_UNIFIDECK_GAMES", "Unifideck Games")}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <DropdownItem
          label={t("OPTISCALER_NON_STEAM_GAMES", "Non-Steam Games")}
          layout="below"
          rgOptions={nonSteamOptions}
          selectedOption={selectedNonSteamId}
          onChange={(option) => {
            const game = nonSteamGames.find(g => String(g.appid) === String(option.data)) || null;
            lastSelectedGame = game;
            setSelectedGame(game);
            setResult('');
          }}
          strDefaultLabel={t("OPTISCALER_CHOOSE_NON_STEAM_GAME", "Choose a Non-Steam game")}
          menuLabel={t("OPTISCALER_NON_STEAM_GAMES", "Non-Steam Games")}
        />
      </PanelSectionRow>

      {result ? (
        <PanelSectionRow>
          <div style={{
            ...STYLES.preWrap,
            ...(result.includes('Error') ? STYLES.statusNotInstalled : STYLES.statusInstalled)
          }}>
            {result}
          </div>
        </PanelSectionRow>
      ) : null}
      
      {selectedGame ? (
        <>
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={handlePatchClick}
            >
              {t("OPTISCALER_ENABLE_FG", "Enable Frame Generation")}
            </ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={handleUnpatchClick}
            >
              {t("OPTISCALER_DISABLE_FG", "Disable Frame Generation")}
            </ButtonItem>
          </PanelSectionRow>
        </>
      ) : null}
    </PanelSection>
  );
}
