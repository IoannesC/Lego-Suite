import { PanelSectionRow } from "@decky/ui";
import { OPTISCALER_HEADER_BANNER } from "../headerBannerData";

interface OptiScalerHeaderProps {
  pathExists: boolean | null;
}

export function OptiScalerHeader({ pathExists }: OptiScalerHeaderProps) {
  if (pathExists !== true) return null;

  return (
    <PanelSectionRow>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        marginBottom: '16px' 
      }}>
        <img 
          src={OPTISCALER_HEADER_BANNER} 
          alt="OptiScaler" 
          style={{ 
            maxWidth: '100%', 
            height: 'auto',
            borderRadius: '8px'
          }} 
        />
      </div>
    </PanelSectionRow>
  );
}
