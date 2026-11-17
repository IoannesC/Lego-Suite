import { PanelSectionRow } from "@decky/ui";
import { FC } from "react";
import { STYLES } from "../utils/constants";
import { ApiResponse } from "../types/index";
import t from "../../i18n/i18n";

export type OperationResult = ApiResponse;

interface ResultDisplayProps {
  result: OperationResult | null;
}

export const ResultDisplay: FC<ResultDisplayProps> = ({ result }) => {
  if (!result) return null;

  const isSuccess = result.status === "success";
  
  return (
    <PanelSectionRow>
      <div style={isSuccess ? STYLES.statusInstalled : STYLES.statusNotInstalled}>
        {isSuccess ? (
          <>
            {result.output?.includes("uninstall") || result.output?.includes("remov") 
              ? t("OPTISCALER_UNINSTALL_SUCCESS", "OptiScaler mod removed successfully.") 
              : t("OPTISCALER_INSTALL_SUCCESS", "OptiScaler mod setup successfully!")}
          </>
        ) : (
          <>
            <strong>Error:</strong> {result.message || t("OPTISCALER_OP_FAILED", "Operation failed.")}
          </>
        )}
        {result.output && !isSuccess && (
          <details style={{ marginTop: '8px' }}>
            <summary style={{ cursor: 'pointer', fontSize: '12px' }}>{t("OPTISCALER_VIEW_DETAILS", "View Details")}</summary>
            <pre style={{ ...STYLES.preWrap, fontSize: '11px', marginTop: '4px' }}>
              {result.output}
            </pre>
          </details>
        )}
      </div>
    </PanelSectionRow>
  );
};
