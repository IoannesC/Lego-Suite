import { PanelSectionRow, ButtonItem } from "@decky/ui";
import { FaBook } from "react-icons/fa";
import t from "../../i18n/i18n";

interface OptiScalerWikiProps {
  pathExists: boolean | null;
}

export function OptiScalerWiki({ pathExists }: OptiScalerWikiProps) {
  if (pathExists !== true) return null;

  const handleWikiClick = () => {
    window.open("https://github.com/optiscaler/OptiScaler/wiki", "_blank");
  };

  return (
    <PanelSectionRow>
      <ButtonItem
        layout="below"
        onClick={handleWikiClick}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <FaBook />
          <div>{t("OPTISCALER_WIKI", "OptiScaler Wiki")}</div>
        </div>
      </ButtonItem>
    </PanelSectionRow>
  );
}
