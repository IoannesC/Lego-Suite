import { useTdpProfilesEnabled } from "../../hooks/useEnableTdpProfiles";
import { useSelector } from "react-redux";
import { getCurrentTdpInfoSelector } from "../../redux-modules/settingsSlice";
import ErrorBoundary from "../ErrorBoundary";
import { DeckyRow, DeckyToggle } from "../atoms/DeckyFrontendLib";

import t from '../../i18n/i18n';

export function TdpProfiles({ isDesktop }: { isDesktop: boolean }) {
  const [tdpProfilesEnabled, setTdpProfilesEnabled] = useTdpProfilesEnabled();

  const { displayName } = useSelector(getCurrentTdpInfoSelector);
  const isEgpu = useSelector((state: any) => state.settings?.isEgpu);
  const egpuName = useSelector((state: any) => state.settings?.egpuName);

  const description = getDescription(
    isDesktop,
    displayName,
    tdpProfilesEnabled
  );

  const label = isDesktop
    ? t('TDP_PROFILE_ENABLE_DESKTOP','Enable Desktop Profile')
    : t('TDP_PROFILE_ENABLE_PER_GAME', 'Enable per-game profiles');

  return (
    <>
      {isEgpu && (
        <div
          style={{
            margin: "0 0 10px 0",
            padding: "8px 12px",
            backgroundColor: "rgba(16, 185, 129, 0.12)",
            border: "1px solid rgba(16, 185, 129, 0.35)",
            borderRadius: "6px",
            display: "flex",
            flexDirection: "column",
            gap: "2px",
          }}
        >
          <div
            style={{
              color: "#10b981",
              fontWeight: 700,
              fontSize: "12px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            ✓ {t("EGPU_CONNECTED", "eGPU Connected")}
          </div>
          {egpuName ? (
            <div
              style={{
                color: "#d1fae5",
                fontSize: "11px",
                fontWeight: 500,
                paddingLeft: "16px",
                wordBreak: "break-word",
              }}
            >
              {egpuName}
            </div>
          ) : null}
        </div>
      )}
      <DeckyRow>
        <ErrorBoundary title="Tdp Profiles">
          <DeckyToggle
            label={label}
            checked={tdpProfilesEnabled}
            onChange={(enabled: boolean) => {
              setTdpProfilesEnabled(enabled);
            }}
            description={description}
            highlightOnFocus
          />
        </ErrorBoundary>
      </DeckyRow>
    </>
  );
}

function getDescription(
  isDesktop: boolean,
  displayName: string,
  tdpProfilesEnabled: boolean
) {
  if (tdpProfilesEnabled) {
    const formattedDisplayName = isDesktop
      ? displayName
      : displayName.substring(0, 20);

    const usingLabel = t("TDP_PROFILE_USING", "Using");
    const defaultLabel = t("TDP_PROFILE_DEFAULT", "Default");

    return Boolean(displayName) && displayName.toLowerCase() !== "default"
      ? `${usingLabel} - ${formattedDisplayName}...`
      : `${usingLabel} - ${defaultLabel}`;
  }
  return "";
}
